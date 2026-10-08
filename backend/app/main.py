from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from app.core.config import settings
from app.routers import web, api, auth
from app.core.database import engine, Base, SessionLocal
from app.core.models import User
from app.core.auth import get_password_hash
from app.core.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Création des tables de la BDD
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, docs_url=None, redoc_url=None, openapi_url=None) # Désactive Swagger et OpenAPI en prod
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi import Request

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if request.method in ["POST", "PUT", "DELETE"]:
        origin = request.headers.get("Origin")
        host = request.headers.get("Host")
        if origin and host:
            # Simple check to ensure origin matches host
            if not origin.endswith(host):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"detail": "CSRF bloqué: Origin invalide"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
    return response

@app.on_event("startup")
def init_db():
    db = SessionLocal()
    try:
        # Création des utilisateurs si la base est vide
        users_to_create = ["baptiste", "papa", "maman"]
        # On lit le mot de passe depuis le fichier caché .env. Pas de fallback en dur par sécurité.
        default_pwd = os.getenv("GARAGE_DEFAULT_PWD")
        if not default_pwd:
            raise ValueError("ERREUR CRITIQUE: La variable d'environnement GARAGE_DEFAULT_PWD n'est pas définie dans le fichier .env")
        
        for username in users_to_create:
            if not db.query(User).filter(User.username == username).first():
                is_admin = (username == "baptiste")
                new_user = User(username=username, hashed_password=get_password_hash(default_pwd), is_admin=is_admin)
                db.add(new_user)
        db.commit()
    finally:
        db.close()

# Dossier statique pour les images et assets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ASSETS_DIR = os.path.join(BASE_DIR, "..", "..", "assets")

os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Enregistrement des routes
app.include_router(web.router)
app.include_router(api.router)
app.include_router(auth.router)
