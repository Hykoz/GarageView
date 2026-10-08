# Utilisation de l'image officielle Python allégée
FROM python:3.13-slim

# Sécurité : ne pas exécuter en tant que root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Empêcher Python de générer des fichiers .pyc et forcer la sortie standard
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Création et attribution des droits du dossier de travail
WORKDIR /app
RUN chown -R appuser:appuser /app

# Installation des dépendances système si nécessaire (ex: sqlite)
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements et installation (en tant que root temporairement pour pip)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY backend/ ./backend/
COPY assets/ ./assets/

# Attribution des droits sur les fichiers copiés
RUN chown -R appuser:appuser /app

# Passage sous l'utilisateur non-root
USER appuser

# Le port d'écoute
EXPOSE 8000

ENV PYTHONPATH=/app/backend

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
