from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.models import User
from app.core.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

from app.core.rate_limit import limiter

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Identifiants incorrects")
    
    access_token = create_access_token(data={"sub": user.username, "is_admin": user.is_admin})
    
    response = JSONResponse(content={"status": "success", "message": "Connecté"})
    import os
    secure_cookie = os.getenv("SECURE_COOKIE", "False").lower() in ("true", "1", "yes")
    # HttpOnly secure cookie
    response.set_cookie(
        key="garage_session", 
        value=access_token, 
        httponly=True, 
        max_age=2 * 3600, 
        samesite="lax",
        secure=secure_cookie
    )
    return response

@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("garage_session")
    if token:
        from app.core.auth import SECRET_KEY, ALGORITHM, revoked_jtis
        import jwt
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            if jti:
                revoked_jtis.add(jti)
        except jwt.PyJWTError:
            pass
    response = JSONResponse(content={"status": "success", "message": "Déconnecté"})
    response.delete_cookie("garage_session")
    return response
