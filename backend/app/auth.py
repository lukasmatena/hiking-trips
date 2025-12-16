from jose import jwt, JOSEError
from pydantic import BaseModel
from os import environ
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
import datetime
from typing import Any


ROLE_NONE = "none"
ROLE_READER = "reader"
ROLE_ADMIN = "admin"

ALGORITHM = "HS256"
SECRET_KEY = environ.get("AUTH_SECRET_KEY")


oauth2 = OAuth2PasswordBearer(tokenUrl="/login")


def create_token_or_none(password: str) -> str | None:
    data: dict = {}
    if password == environ.get("AUTH_PASSWORD_READER"):
        data["role"] = ROLE_READER
    elif password == environ.get("AUTH_PASSWORD_ADMIN"):
        data["role"] = ROLE_ADMIN
    else:
        return None
    data["exp"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    return jwt.encode(data, key=SECRET_KEY, algorithm=ALGORITHM)



def role_from_token(token: str) -> str | None:
    payload: dict[str, Any] = {}
    try:
        payload = jwt.decode(token, algorithms=ALGORITHM, key=SECRET_KEY)
    except JOSEError:
        pass
    if not payload.get("role"):
        return None
    return payload.get("role", ROLE_NONE)

def reader_only(token: str = Depends(oauth2)):
    role: str|None = role_from_token(token)
    if not role:
        raise HTTPException(status_code=401)
    if role == ROLE_READER or role == ROLE_ADMIN:
        return True
    raise HTTPException(status_code=403)
    
def admin_only(token: str = Depends(oauth2)):
    role: str|None = role_from_token(token)
    if not role:
        raise HTTPException(status_code=401)
    if role == ROLE_ADMIN:
        return True
    raise HTTPException(status_code=403)

def get_me_role(token: str = Depends(oauth2)) -> str:
    role: str|None = role_from_token(token)
    if role:
        return role
    return ""


