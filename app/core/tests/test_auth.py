from cryptography.hazmat.primitives import serialization
from ..auth import generate_jwt, decode_jwt
import os

SELF_PATH = os.path.dirname(os.path.abspath(__file__))

with open(f'{SELF_PATH}/../vault/jwt_public_key.pem', 'rb') as public_key_file:
    public_key = serialization.load_der_public_key(
        public_key_file.read(),
        backend=None
    )

with open(f'{SELF_PATH}/../vault/jwt_private_key.pem', 'rb') as private_key_file:
    private_key = serialization.load_pem_private_key(
        private_key_file.read(),
        password=None,
        backend=None
    )

def test_jwt():
    input = {'test': 'test'}
    jwt = generate_jwt(input, private_key)
    output = decode_jwt(jwt, public_key)

    assert input == output