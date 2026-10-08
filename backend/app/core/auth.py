import jwt
from datetime import datetime, timedelta
import bcrypt
from fastapi import Request, HTTPException, Depends
from typing import Optional
import uuid
import os

from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 2

revoked_jtis = set()

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_from_cookie(request: Request) -> Optional[dict]:
    token = request.cookies.get("garage_session")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti in revoked_jtis:
            return None
        username: str = payload.get("sub")
        if username is None:
            return None
        return {"username": username, "is_admin": payload.get("is_admin", False)}
    except jwt.PyJWTError:
        return None

def check_auth(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorisé. Connectez-vous d'abord.")
    return user

def check_admin(request: Request):
    user = check_auth(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès refusé. Réservé aux administrateurs.")
    return user
