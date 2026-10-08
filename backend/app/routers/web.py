from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx
import datetime
import os
from app.core.config import settings
from app.core.state import system_state
from app.core.auth import check_auth, check_admin, get_current_user_from_cookie
from fastapi import Depends

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = get_current_user_from_cookie(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={
            "system_state": system_state, 
            "is_authenticated": bool(user),
            "username": user["username"] if user else None,
            "is_admin": user["is_admin"] if user else False
        }
    )

import time
last_trigger_time = 0

from app.core.rate_limit import limiter

@router.post("/action/trigger")
@limiter.limit("2/minute")
async def trigger_door(request: Request, user: dict = Depends(check_admin)):
    global last_trigger_time
    
    # Bloque strictement le spam côté serveur (2 secondes)
    if time.time() - last_trigger_time < 2.0:
        return {"status": "ignored", "message": "Anti-spam serveur"}
    last_trigger_time = time.time()

    esp32_ip = system_state.get("esp32_ip", settings.ESP32_IP)
    url = f"http://{esp32_ip}/trigger"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, timeout=5.0, headers={"X-ESP32-TOKEN": settings.ESP32_API_KEY})
            print("✅ Ordre envoyé à l'ESP32 avec succès.")
    except Exception as e:
        print(f"❌ Erreur de communication avec l'ESP32: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="L'ESP32 est hors ligne ou injoignable")

    # On change l'état d'affichage provisoirement
    system_state["porte_ouverte"] = not system_state["porte_ouverte"]
    system_state["derniere_mise_a_jour"] = datetime.datetime.now().strftime("%H:%M:%S")
    
    return {"status": "success", "message": "Commande envoyée"}

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

@router.get("/stream")
async def proxy_stream(user: dict = Depends(check_auth)):
    # On passe par le serveur Python pour contourner les blocages de Chrome/VPN
    esp32_ip = system_state.get("esp32_ip", settings.ESP32_IP)
    url = f"http://{esp32_ip}:81/stream"
    
    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", url, timeout=None, headers={"X-ESP32-TOKEN": settings.ESP32_API_KEY}) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            print(f"❌ Erreur Proxy Caméra: {e}")
            yield b""

    return StreamingResponse(
        stream_generator(), 
        media_type="multipart/x-mixed-replace;boundary=123456789000000000000987654321"
    )

@router.get("/state")
async def get_state(user: dict = Depends(check_auth)):
    return system_state

from fastapi.responses import FileResponse
from fastapi import HTTPException
import os

@router.get("/latest_capture.jpg")
async def get_latest_capture(user: dict = Depends(check_auth)):
    image_path = os.path.join(BASE_DIR, "protected", "latest_capture.jpg")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Pas de capture disponible")
    return FileResponse(image_path)

