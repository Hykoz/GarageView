<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-white-nobg.png"/>
    <img src="assets/banner-color.png" alt="GarageView" width="500"/>
  </picture>
</p>

<p align="center">
  <strong>Télésurveillance et contrôle d'accès de porte de garage, 100 % local</strong><br/>
  PWA multi-utilisateurs · Python · ESP32-CAM · Docker · Auto-hébergé
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Back--end-Python%20%7C%20FastAPI-3776AB?logo=python&logoColor=white" alt="Python FastAPI"/>
  <img src="https://img.shields.io/badge/Front--end-PWA%20%7C%20JS%20Vanilla-F7DF1E?logo=javascript&logoColor=black" alt="PWA"/>
  <img src="https://img.shields.io/badge/Firmware-Arduino%20C%2B%2B-00979D?logo=arduino&logoColor=white" alt="Arduino C++"/>
  <img src="https://img.shields.io/badge/Hardware-ESP32--CAM-E7352C?logo=espressif&logoColor=white" alt="ESP32"/>
  <img src="https://img.shields.io/badge/D%C3%A9ploiement-Docker-2496ED?logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Base%20de%20donn%C3%A9es-SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite"/>
</p>

---

## 📖 Présentation

**GarageView** est un système domotique qui permet d'**ouvrir sa porte de garage depuis son téléphone**, de **voir son état réel** (ouverte / fermée) et de **recevoir une photo** à chaque action.

Le projet repose sur une **architecture 100 % locale et auto-hébergée** : aucune donnée n'est envoyée vers un service Cloud, tout tourne sur un Mini-PC à la maison.

- **Le matériel** (ESP32-CAM) appuie physiquement sur le bouton d'une télécommande, lit un capteur magnétique et prend des photos.
- **Le serveur** (Python, conteneurisé avec Docker) gère les utilisateurs, la sécurité, l'historique et la logique.
- **L'interface** (PWA) s'installe sur l'écran d'accueil du téléphone comme une vraie application.

### 🔐 Le défi : le code tournant

La motorisation (EcoStar) utilise une sécurité radio à **code tournant** (*Rolling Code*) : chaque signal est unique et chiffré, il est donc impossible de l'imiter par logiciel.

👉 **Solution « Hardware Bypass »** : un relais à contact sec est soudé sur le bouton d'une **télécommande de secours**. L'ESP32 simule un appui physique et la télécommande gère elle-même la sécurité d'origine.

## 🏗️ Architecture

```
┌──────────────┐   HTTPS / WebSocket   ┌────────────────────────────┐    HTTP + jeton    ┌──────────────┐
│  📱 PWA       │ ◄──────────────────► │   🖥️ SERVEUR (Mini-PC)      │ ◄────────────────► │  📷 ESP32-CAM │
│  (Téléphone) │   commandes · état   │   Docker                   │   ordre · état     │              │
│              │   photos · historique│   ├─ FastAPI (Python)      │   photo            │  ├─ Relais ──┼──► Télécommande ··· 📡 ··· Moteur
└──────────────┘                      │   ├─ SQLite                │                    │  └─ Capteur  │◄── Contacteur magnétique
                                      │   └─ Cloudflare Tunnel     │                    └──────────────┘
                                      └────────────────────────────┘
```

## ⚙️ Stack technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Interface | PWA (HTML / CSS / JS Vanilla) | Application installable, bouton d'ouverture, état en direct |
| Serveur | Python · FastAPI | API REST, authentification, logique métier |
| Temps réel | WebSockets | État de la porte mis à jour instantanément sur tous les appareils |
| Base de données | SQLite · SQLModel | Utilisateurs, rôles, historique des accès |
| Firmware | Arduino C++ | Pilotage du relais, lecture du capteur, capture photo |
| Matériel | Freenove ESP32-WROVER CAM | Pont d'exécution entre le serveur et la porte |
| Déploiement | Docker · Docker Compose | Conteneurisation sur Mini-PC Linux |
| Accès distant | Cloudflare Tunnel | Accès sécurisé depuis l'extérieur, sans ouvrir de port |

## ✨ Fonctionnalités

- [ ] 🔓 Ouverture / fermeture à distance
- [ ] 🚪 Retour d'état fiable (capteur magnétique)
- [ ] 📸 Photo automatique à chaque action (levée de doute)
- [ ] 👥 Multi-utilisateurs avec rôles (admin / utilisateur)
- [ ] 📜 Historique : qui, quand, avec quelle photo
- [ ] ⚡ Mise à jour en temps réel
- [ ] 📱 Installable sur téléphone (PWA)
- [ ] 🌍 Accès sécurisé depuis l'extérieur

## 🎨 Identité visuelle

L'interface est en **mode sombre** avec une seule couleur d'accent : l'**ambre** `#FF7A00`.

| Couleur | Code | Utilisation |
|---------|------|-------------|
| ⬛ Gris carbone | `#121212` / `#18181B` | Fonds |
| ⬜ Blanc / gris | `#FFFFFF` / `#A1A1AA` | Textes |
| 🟧 Ambre | `#FF7A00` | Boutons d'action, état de connexion |
| 🔴 Rouge | — | **Uniquement** : porte ouverte |
| 🟢 Vert | — | **Uniquement** : porte fermée |

- **Pourquoi l'ambre ?** Il évoque le côté matériel du projet (cuivre, relais, voyants de voiture).
- **Pourquoi le mode sombre ?** L'app sert souvent la nuit, depuis la voiture : un fond sombre n'éblouit pas.
- **Pourquoi réserver le rouge et le vert ?** Pour comprendre l'état de la porte d'un simple coup d'œil, sans confusion avec le reste de l'interface.
- **Règle 60-30-10** : 60 % de fonds sombres, 30 % de textes neutres, 10 % d'ambre.

## 🚀 Lancement rapide

```bash
# Cloner le projet
git clone https://github.com/ton-username/GarageView.git
cd GarageView

# Lancer avec Docker (recommandé)
docker-compose up --build -d
```

> 💡 L'application sera accessible sur `http://127.0.0.1:8000`. Consultez le fichier `GUIDE_DEMARRAGE.md` pour plus de détails.

## 📁 Structure du projet

```
GarageView/
├── backend/             # Serveur Python FastAPI et frontend PWA
├── arduino/             # Code Arduino C++ de l'ESP32-CAM
├── assets/              # Ressources graphiques (logo, images)
├── docker-compose.yml   # Configuration de déploiement Docker
└── README.md
```

## 🎯 Objectifs pédagogiques

- **Architecture Client-Serveur** : séparation des responsabilités entre interface, serveur et matériel
- **Développement back-end Python** : API REST, authentification, base de données
- **Temps réel** : communication bidirectionnelle avec les WebSockets
- **Systèmes embarqués** : programmation C++ / Arduino, GPIO, capteurs, caméra
- **Sécurité** : hachage des mots de passe, gestion des sessions, cloisonnement réseau
- **DevOps** : conteneurisation Docker, auto-hébergement, déploiement sur Linux
- **Bonnes pratiques** : code propre, versionning Git, documentation

## 📄 Licence

Ce projet est développé à des fins éducatives et personnelles.
