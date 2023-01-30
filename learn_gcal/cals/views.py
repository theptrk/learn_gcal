from datetime import datetime

import environ
import google.auth.transport.requests
from allauth.socialaccount.models import SocialToken
from django.shortcuts import redirect, render
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

env = environ.Env()


def get_events(creds):
    try:
        service = build("calendar", "v3", credentials=creds)

        today = datetime.now().date()
        midnight = datetime.combine(today, datetime.min.time())
        iso_midnight = midnight.isoformat()
        now = iso_midnight + "Z"  # 'Z' indicates UTC time

        print("Getting the upcoming 10 events")
        try:
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=20,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except Exception as e:
            print("GOOGLE API ERROR")
            print(e)
            # creds.refresh(httplib2.Http())
            # https://stackoverflow.com/questions/29154374/how-can-i-refresh-a-stored-google-oauth-credential
            # https://google-auth.readthedocs.io/en/latest/reference/google.auth.transport.requests.html#google.auth.transport.requests.Request

            # Does this work?
            request = google.auth.transport.requests.Request()
            creds.refresh(request)
            # TODO fix this when token is expired
            # INFO 2023-01-15 23:56:00,153 google_auth_httplib2 77745 123145462980608 Refreshing credentials
            # due to a 401 response. Attempt 1/2.
            # print(events_result)

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
            redirect("accounts:social:begin", "google")
    except Exception as e:
        print("some other error")
        print(e)


def target_blank(value):
    if value is None:
        return None
    return value.replace("<a ", '<a target="_blank" ')


def index(request):
    context = {"user": request.user, "events": [], "state": ""}

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
            print(e)

        if token is None:
            context["state"] += ", token is None"
        else:
            try:
                # TODO if token.expires_at is expired then refresh token
                print("C")
                credentials = Credentials(
                    token=token.token,
                    refresh_token=token.token_secret,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=env("GOOGLE_CLIENT_ID", default=""),
                    client_secret=env("GOOGLE_CLIENT_SECRET", default=""),
                )
                events = get_events(credentials)
                context["events"] = events
            except Exception as e:
                print("getting events failed")
                print(e)

    return render(request, "cals/index.html", context)
