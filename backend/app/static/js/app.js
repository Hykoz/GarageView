const homeView = document.getElementById('home-view');
const camView = document.getElementById('cam-view');
const triggerBtn = document.getElementById('trigger-btn');
const openCamBtn = document.getElementById('open-cam-btn');
const closeCamBtn = document.getElementById('close-cam-btn');
const fullCamStream = document.querySelector('.full-cam-stream');

// Gestion des erreurs
let errorTimeout = null;
function showError(msg) {
    const toast = document.getElementById('error-toast');
    document.getElementById('error-message').innerText = msg;
    toast.classList.add('show');
    if (errorTimeout) clearTimeout(errorTimeout);
    errorTimeout = setTimeout(() => toast.classList.remove('show'), 4000);
}

// Navigation entre les vues
openCamBtn.addEventListener('click', () => {
    // On charge le stream dans la grande vue uniquement quand on l'ouvre
    if (!fullCamStream.src.includes('/stream')) {
        fullCamStream.src = '/stream';
    }
    homeView.classList.remove('active');
    camView.classList.add('active');
    
    // Tente de forcer le plein écran natif (optionnel, selon l'appareil)
    if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(e => {});
    }
});

closeCamBtn.addEventListener('click', () => {
    camView.classList.remove('active');
    homeView.classList.add('active');
    if (document.fullscreenElement) {
        document.exitFullscreen().catch(e => {});
    }
});

// Logique du gros bouton central
triggerBtn.addEventListener('click', function() {
    if (navigator.vibrate) navigator.vibrate(50);
    
    // Animation du bouton
    this.classList.add('clicked');
    setTimeout(() => this.classList.remove('clicked'), 600);
    
    this.disabled = true;

    fetch('/action/trigger', { method: 'POST' })
        .then(response => {
            if (!response.ok) throw new Error("Erreur système (" + response.status + ")");
            return response.json();
        })
        .catch(err => {
            console.error('Erreur:', err);
            showError("Échec de l'action : " + err.message);
        });

    // Déverrouillage après 2.5 secondes
    setTimeout(() => {
        this.disabled = false;
    }, 2500);
});

let lastState = null;

// Polling de l'état
setInterval(function() {
    fetch('/state')
        .then(response => response.json())
        .then(state => {
            document.getElementById('distance-val').innerText = state.distance_cm;
            document.getElementById('time-val').innerText = state.derniere_mise_a_jour;

            // Vérifier si l'état a changé pour déclencher l'animation
            const statusDiv = document.getElementById('door-status');
            const isChanged = (lastState !== null && lastState !== state.porte_ouverte);
            lastState = state.porte_ouverte;
            
            const updateClass = isChanged ? 'updated' : '';

            if (state.porte_ouverte) {
                statusDiv.innerHTML = `
                    <div class="status-badge open ${updateClass}">
                        <div class="status-indicator"></div>
                        Porte Ouverte
                    </div>`;
            } else {
                statusDiv.innerHTML = `
                    <div class="status-badge closed ${updateClass}">
                        <div class="status-indicator"></div>
                        Porte Fermée
                    </div>`;
            }
        })
        .catch(err => {
            console.error('Erreur MAJ Etat:', err);
            // showError("Impossible de joindre le garage"); // On peut le masquer pour éviter le spam s'il y a une micro-coupure
        });
}, 1500);

// Déconnexion
const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        fetch('/auth/logout', { method: 'POST' })
            .then(() => window.location.reload());
    });
}
