from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
import jwt
from dotenv import load_dotenv
import os
import uuid
import logging


load_dotenv()

password_context = CryptContext(schemes=["bcrypt"])

ACCESS_TOKEN_EXPIRY =  600
REFRESH_TOKEN_EXPIRY = 7*24*3600

def generate_hash(password: str) -> str:
    hash = password_context.hash(password)
    
    return hash

def verify_password(password: str, hash: str) -> bool:
    return password_context.verify(password, hash)


def create_access_token(user_data: dict, 
                        expiry: timedelta = None, 
                        refresh: bool = False):

    payload = {}
    
    payload['user'] = user_data
    payload['exp'] = datetime.now(timezone.utc) + (expiry if expiry is not None else timedelta(seconds=ACCESS_TOKEN_EXPIRY))
    
    payload['jti'] = str(uuid.uuid4())

    payload['refresh']  = refresh
    
    
    token = jwt.encode(
        payload=payload,
        key = os.getenv("JWT_SECRET"),
        algorithm="HS256"
    )
    
    return token


def create_refresh_token(user_data: dict, expiry: timedelta = None):
    
    
    payload = {
        "user": user_data,
        "exp": datetime.now() + (expiry if expiry else timedelta(seconds=REFRESH_TOKEN_EXPIRY)),
        "jti": str(uuid.uuid4()),
        "refresh": True
    }

    token = jwt.encode(
        payload=payload,
        key=os.getenv("JWT_SECRET"),
        algorithm="HS256"
    )

    return token

def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token,
            key = os.getenv("JWT_SECRET"),
            algorithms=["HS256"]
        )
        return token_data
    
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        logging.exception(e)
        return None
        
    