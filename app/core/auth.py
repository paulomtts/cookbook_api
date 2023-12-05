from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse

import requests

import os


auth_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
google_redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')


@auth_router.get("/auth/login")
async def login():
    # return {"url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={google_client_id}&redirect_uri={google_redirect_uri}&scope=openid%20profile%20email&access_type=offline"}
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={google_client_id}&redirect_uri={google_redirect_uri}&scope=openid%20profile%20email&access_type=offline")


@auth_router.route("/auth/callback")
async def validate(code: str):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": google_redirect_uri,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=data)
    print(response.json())
    access_token = response.json()["access_token"]
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    print(user_info.json())
    return user_info.json()

# @auth_router.get("/token")
# async def get_token(token: str = Depends(oauth2_scheme)):
#     return jwt.decode(token, google_client_secret, algorithms=["HS256"])