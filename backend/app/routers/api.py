from fastapi import APIRouter, UploadFile, File, Request, Header, HTTPException
import datetime
import os
from app.core.state import system_state
from app.core.config import settings

router = APIRouter(prefix="/api/esp32", tags=["ESP32"])

def verify_esp32_token(x_esp32_token: str = Header(...)):
    if x_esp32_token != settings.ESP32_API_KEY:
        raise HTTPException(status_code=401, detail="Jeton ESP32 invalide")
    return x_esp32_token

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

PROTECTED_DIR = os.path.join(BASE_DIR, "protected")
os.makedirs(PROTECTED_DIR, exist_ok=True)

from pydantic import BaseModel
from typing import Optional

class ESP32Status(BaseModel):
    is_open: Optional[bool] = None
    distance: Optional[int] = None

from fastapi import Depends

@router.post("/update")
async def esp32_update(status: ESP32Status, request: Request, token: str = Depends(verify_esp32_token)):
    if request.client and request.client.host:
        system_state["esp32_ip"] = request.client.host

    if status.is_open is not None:
        system_state["porte_ouverte"] = status.is_open
        
    if status.distance is not None:
        system_state["distance_cm"] = status.distance
        # Logique pour déduire Ouvert/Fermé (Exemple: si > 50cm, la porte est ouverte)
        if status.distance > 50:
            system_state["porte_ouverte"] = True
        else:
            system_state["porte_ouverte"] = False
            
    system_state["derniere_mise_a_jour"] = datetime.datetime.now().strftime("%H:%M:%S")
    return {"message": "État mis à jour avec succès"}

@router.post("/camera")
async def receive_camera_image(file: UploadFile = File(...), token: str = Depends(verify_esp32_token)):
    image_path = os.path.join(PROTECTED_DIR, "latest_capture.jpg")
    with open(image_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"status": "success", "message": "Photo enregistrée"}
