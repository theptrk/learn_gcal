import environ
from allauth.socialaccount.models import SocialApp, SocialToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

env = environ.Env()


def get_google_credentials(token: SocialToken):
    try:
        google_client = SocialApp.objects.get(provider="google")
        creds = Credentials(
            token=token.token,
            refresh_token=token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=google_client.client_id,
            client_secret=google_client.secret,
        )

        # I read somewhere in google docs? it was best practice to renew the token
        # on every request before the expiry time. Users can revoke access at any time
        # before expiry or other reasons can cause the token to be invalid.
        creds.refresh(Request())
        # update saved SocialToken
        token.token = creds.token
        token.token_secret = creds.refresh_token
        token.expires_at = creds.expiry
        token.save()
        return creds
    except Exception as e:
        print("get_google_credentials")
        print(e)
        return None
