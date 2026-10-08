import os
import secrets
from dataclasses import dataclass

def get_or_create_secret():
    # Génère une clé secrète unique pour la machine locale
    # Ce fichier ne sera jamais poussé sur GitHub
    secret_file = os.path.join(os.path.dirname(__file__), ".jwt_secret")
    if os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            return f.read().strip()
    else:
        new_secret = secrets.token_hex(32)
        with open(secret_file, "w") as f:
            f.write(new_secret)
        return new_secret

def get_esp32_api_key():
    key = os.getenv("ESP32_API_KEY")
    if not key:
        raise ValueError("ERREUR CRITIQUE: La variable d'environnement ESP32_API_KEY n'est pas définie dans le fichier .env")
    return key

@dataclass
class Settings:
    PROJECT_NAME: str = "GarageView API"
    ESP32_IP: str = os.getenv("ESP32_IP", "192.168.1.47")
    SECRET_KEY: str = os.getenv("SECRET_KEY", get_or_create_secret())
    ESP32_API_KEY: str = get_esp32_api_key()

settings = Settings()
