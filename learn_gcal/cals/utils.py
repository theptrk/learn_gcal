import environ
from allauth.socialaccount.models import SocialToken, SocialApp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from learn_gcal.cals import NEED_REDIRECT_GOOGLE_AUTH

env = environ.Env()


def get_google_credentials(token: SocialToken):
    # please modify the name to your google app name
    # http://127.0.0.1:8000/admin/socialaccount/socialapp/
    try:
        gApp = SocialApp.objects.get(name="google calender")
    except:
        print(""">>>please check your config on admin socialAPP,
         default url is -> /admin/socialaccount/socialapp/""")

    creds = Credentials(
        token=token.token,
        refresh_token=token.token_secret,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=gApp.client_id,
        client_secret=gApp.secret
    )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            r = creds.refresh(Request())
            print(">>>>>OLD TOKEN IS --->", token.token)
            print(">>>>>NEW TOKEN IS --->", creds.token)
            # update SocialToken
            token.token = creds.token
            token.token_secret = creds.refresh_token
            token.expires_at = creds.expiry
            token.save()
            print(">>>>>REFRESH TOKEN IS SUCCESS")
        else:
            return NEED_REDIRECT_GOOGLE_AUTH
    print(">>>>>CURRENT CREDS IS --->", creds)
    return creds
