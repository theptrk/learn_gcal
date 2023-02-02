import environ
from allauth.socialaccount.models import SocialToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from learn_gcal.cals import NEED_REDIRECT_GOOGLE_AUTH

env = environ.Env()


def get_google_credentials(token: SocialToken):

    creds = Credentials(
        token=token.token,
        refresh_token=token.token_secret,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env("GOOGLE_CLIENT_ID", default=""),
        client_secret=env("GOOGLE_CLIENT_SECRET", default=""),
    )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # update SocialToken
            token.token = creds["access_token"]
            token.token_secret = creds.refresh_token
            token.expires_at = creds.expiry
            token.save()
        else:
            return NEED_REDIRECT_GOOGLE_AUTH

    return creds
