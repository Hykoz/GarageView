from typing import Dict, Any

# Gestion de l'état en mémoire (Sera remplacé par SQLite plus tard)
system_state: Dict[str, Any] = {
    "porte_ouverte": False,
    "distance_cm": 0,
    "derniere_mise_a_jour": "Jamais",
    "esp32_ip": "192.168.1.47"
}
