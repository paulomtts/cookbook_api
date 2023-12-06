from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse, JSONResponse

from app.core.models import Users, Sessions
from app.core.schemas import SuccessMessages, DBOutput

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from datetime import datetime, timedelta

import requests
import secrets
import base64
import json
import jwt
import os

from setup import db


auth_router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
GOOGLE_INFO_URL = os.environ.get('GOOGLE_INFO_URL')

# Session tokens are JWTs built and encoded with a specific public key
# that is never shared with the client. The client cannot decode the 
# session JWT. The client can only send the JWT to the server for
# verification. This is to prevent the client from tampering with the
# session JWT.

# The server can decode the session JWT and verify the payload. If the
# payload is valid, the server can then issue a new session JWT to the
# client. The client can then store the new session JWT and use it for
# future requests.


# RSA & hashing
def generate_rsa_key_pair():
    """
    Generate a new key pair in PEM format and store them locally. This method 
    is meant for development only. When in production, store your private key 
    in a secure location.
    """

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()


    private_key_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                format=serialization.PrivateFormat.PKCS8,
                                                encryption_algorithm=serialization.NoEncryption())
    public_key_der = public_key.public_bytes(encoding=serialization.Encoding.DER,
                                        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    

    with open('./vault/jwt_public_key.pem', 'wb') as public_key_file:
        public_key_file.write(public_key_der)

    with open('./vault/jwt_private_key.pem', 'wb') as private_key_file:
        private_key_file.write(private_key_pem)

def hash_plaintext(plaintext) -> str:
    """
    Hash plaintext using SHA256. Output is in hash.

    Note: SHA256 is a one-way hash function. It is not possible to decrypt the
    output to obtain the original plaintext. The only way to verify the
    plaintext is to hash it again and compare the hashes.
    """
    digest = hashes.Hash(hashes.SHA256())
    digest.update(plaintext.encode('utf-8'))
    hash = digest.finalize()

    return hash

def encrypt_rsa_plaintext(plaintext, public_key) -> str:
    """
    Hashes and encrypts a plaintext using the public key. Output is in ciphertext.
    """
    hashed_plaintext = hash_plaintext(plaintext)

    ciphertext = public_key.encrypt(
        hashed_plaintext, 
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    ciphertext = base64.b64encode(ciphertext).decode('utf-8')

    return ciphertext

def decrypt_rsa_ciphertext(ciphertext, private_key) -> str:
    """
    Decrypt ciphertext using the private key. Output is in plaintext.
    """
    ciphertext = base64.b64decode(ciphertext)

    decryption = private_key.decrypt(
        ciphertext, 
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    decryption = base64.b64encode(decryption).decode('utf-8')

    return decryption


# JWT
def generate_jwt(payload, private_key):
    """
    Generates a JWT token using the payload and the secret signature.
    """
    return jwt.encode(payload, private_key, algorithm='RS256')

def decode_jwt(token, public_key):
    """
    Decodes a JWT token using the secret signature.
    """
    return jwt.decode(token, public_key, algorithms=['RS256'])


# Session token
def generate_session_token(length=64):
    """
    Generates a random key for general use.
    """
    return secrets.token_hex(length//2)


# Routes
@auth_router.get("/auth/login")
async def login():
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline")


@auth_router.get("/auth/callback")
async def validate(request: Request, code: str = Query(...)):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:

        access_token = response.json().get("access_token")
        if access_token:
            user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})

            # 1) collect information
            hashed_user_agent = hash_plaintext(json.dumps(request.headers.get("User-Agent")))
            user_agent = base64.b64encode(hashed_user_agent).decode('utf-8')
            client_ip = request.client.host
            user_info: dict = user_info.json()
            session_token = generate_session_token()

            # 2) build user & session data
            user_data = {
                'google_id': user_info.get("id")
                , 'google_email': user_info.get("email")
                , 'google_picture_url': user_info.get("picture")
                , 'google_access_token': access_token
                , 'name': user_info.get("name")
                , 'locale': user_info.get("locale")
            }

            session_data = {
                'google_id': user_info.get("id")
                , 'token': session_token
                , 'user_agent': user_agent
                , 'client_ip': client_ip
                , 'status': 'active'
            }

            # 3) build payload & generate JWT
            payload = {
                "token": session_token
                , "user_email": user_info.get("email")
                , "local_user_id": user_info.get("id")
                , "expiration": (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            }

            with open(f'{os.getcwd()}/app/core/vault/jwt_private_key.pem', 'rb') as private_key_file:
                private_key = serialization.load_pem_private_key(
                    private_key_file.read(),
                    password=None
                )

                jwt_token = generate_jwt(payload, private_key)

            @db.catching(SuccessMessages(client="User was successfully created.", logger="User authenticated. Session initiated."))
            def auth__initiate_session(user_data, session_data):
                user = db.upsert(Users, [user_data], single=True)
                if user:
                    db.upsert(Sessions, [session_data])

                return []
            
            db_output: DBOutput = auth__initiate_session(user_data, session_data)
            
            if db_output.status == 200:
                response = JSONResponse(content={'message': db_output.message}, status_code=db_output.status)
                response.set_cookie(key="session_cookie", value=jwt_token, httponly=True, samesite=None) # during development
                return response

            raise HTTPException(status_code=db_output.status, detail=db_output.message)
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    raise HTTPException(status_code=401, detail="Bad request.")


async def verify_session(access_token: str = Depends(oauth2_scheme)):
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    if user_info.status_code == 200:
        return user_info.json()
    else:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
