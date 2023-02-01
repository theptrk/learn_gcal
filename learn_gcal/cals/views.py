import zoneinfo
from datetime import datetime

import google.auth.transport.requests
import pytz
from allauth.socialaccount.models import SocialToken
from django.shortcuts import redirect, render
from django.utils import timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from learn_gcal.cals import NEED_REDIRECT_GOOGLE_AUTH
from learn_gcal.cals.utils import get_google_credentials


def get_events(creds):
    try:
        service = build("calendar", "v3", credentials=creds)

        # today = datetime.now().date()
        # midnight = datetime.combine(today, datetime.min.time())
        # iso_midnight = midnight.isoformat()
        # now = iso_midnight + "Z"  # 'Z' indicates UTC time

        # TODO use user timezone
        tz = pytz.timezone("America/Los_Angeles")
        today = datetime.now(tz)
        midnight_here = today.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_utc = midnight_here.astimezone(pytz.utc)
        # cant use isoformat() because it adds a +00:00
        # ex: '2023-01-30T08:00:00+00:00Z'
        # google expects: '2023-01-30T00:00:00Z'
        timeMin = midnight_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        print("Getting the upcoming 10 events")
        try:
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=timeMin,
                    maxResults=30,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

        except Exception as e:
            print("GOOGLE API ERROR")
            print(e)
            if e.status_code == 403:
                if e.reason == "Request had insufficient authentication scopes.":
                    print("user needs to grant calendar scopes")

        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        events_parsed = []
        for event in events:
            start_datetime_or_date = None
            end_datetime_or_date = None
            all_day_event = True if "date" in event["start"] else False
            if all_day_event:
                start_datetime_or_date = event["start"].get("date", None)
                date_object = datetime.strptime(start_datetime_or_date, "%Y-%m-%d")
                start_datetime_or_date_readable = date_object.strftime("%B %d, %Y")

                end_datetime_or_date = event["end"].get("date", None)
                date_object = datetime.strptime(end_datetime_or_date, "%Y-%m-%d")
                end_datetime_or_date_readable = date_object.strftime("%B %d, %Y")
            else:
                start_datetime_or_date = event["start"].get("dateTime", None)
                start_datetime_or_date_readable = datetime.strptime(
                    start_datetime_or_date, "%Y-%m-%dT%H:%M:%S%z"
                )
                end_datetime_or_date = event["end"].get("dateTime", None)
                end_datetime_or_date_readable = datetime.strptime(
                    end_datetime_or_date, "%Y-%m-%dT%H:%M:%S%z"
                )

            event["all_day_event"] = all_day_event
            event["start_datetime_or_date"] = start_datetime_or_date
            event["start_datetime_or_date_readable"] = start_datetime_or_date_readable
            event["end_datetime_or_date"] = end_datetime_or_date
            event["end_datetime_or_date_readable"] = end_datetime_or_date_readable

            # change links to open in new tab
            old_description = event.get("description", "")
            new_description = target_blank(old_description)
            event["description"] = new_description

            description = event.get("description", "")
            if (
                "This event was created from an email you received in Gmail"
                in description
            ):
                event["gmail_autocreated_event"] = True

            events_parsed.append(event)
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

        return events_parsed

    except HttpError as error:
        print("An error occurred: %s" % error)
        if error.reason == "Request had insufficient authentication scopes.":
            print("User needs to allow api scopes in the google authenications page")
            # TODO redirect to google relogin page
            return NEED_REDIRECT_GOOGLE_AUTH
    except Exception as e:
        print("some other error")
        print(e)


def target_blank(value):
    if value is None:
        return None
    return value.replace("<a ", '<a target="_blank" ')


def index(request):
    # TODO generalize timezones
    timezone.activate(zoneinfo.ZoneInfo("America/Los_Angeles"))

    context = {"user": request.user, "events": [], "state": ""}
    ReLogin = 0

    if not request.user.is_authenticated:
        print("user is not authenticated")

    if request.user.is_authenticated:
        # request is the HttpRequest object
        token = None
        try:
            print("A")
            token = SocialToken.objects.get(
                account__user=request.user, account__provider="google"
            )

        except Exception as e:
            print("B")
            # todo redirect to login again?
            # bug: if no social token you need to relogin with google
            print("no social token: SUPER BIG BUG")
            context["state"] += ", no social token"
            ReLogin = NEED_REDIRECT_GOOGLE_AUTH

        if token is None:
            context["state"] += ", token is None"
        else:
            try:
                credentials = get_google_credentials(token)
                if credentials is NEED_REDIRECT_GOOGLE_AUTH:
                    raise Exception(NEED_REDIRECT_GOOGLE_AUTH)

                events = get_events(credentials)
                if events is NEED_REDIRECT_GOOGLE_AUTH:
                    raise Exception(NEED_REDIRECT_GOOGLE_AUTH)

                context["events"] = events

            except Exception as e:
                if e is NEED_REDIRECT_GOOGLE_AUTH:
                    ReLogin = NEED_REDIRECT_GOOGLE_AUTH
                print("getting events failed")
                print(e)

    # RELODIN REDIRECT
    # YOU NEED CHANGE THE URL TO YOUR REAL URL YOURSELF
    if ReLogin is NEED_REDIRECT_GOOGLE_AUTH:
        return redirect("accounts:social:begin", "google")

    return render(request, "cals/index.html", context)
