from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

import requests
import secrets
import base64
import jwt
import os

auth_router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')


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
    

    with open('./secrets/public_key.pem', 'wb') as public_key_file:
        public_key_file.write(public_key_der)

    with open('./secrets/private_key.pem', 'wb') as private_key_file:
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
def generate_session_token(length=128):
    """
    Generates a random key for general use.
    """
    return secrets.token_hex(length//2)


# Routes
@auth_router.get("/auth/login")
async def login():
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline")


@auth_router.get("/auth/callback")
async def validate(code: str = Query(...)):
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

            # 1) store in database

            # 2) generate jwt token

            # 3) return jwt token

            return user_info.json()
    
    return {"error": "Failed to obtain access token"}


@auth_router.get("/auth/verify")
async def verify_session(access_token: str = Depends(oauth2_scheme)):
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    if user_info.status_code == 200:
        return user_info.json()
    else:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

