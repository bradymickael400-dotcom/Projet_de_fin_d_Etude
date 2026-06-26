// ═══════════════════════════════════════════════════════
//  ARGOS — script.js  (version DB-live complète)
// ═══════════════════════════════════════════════════════

// ── STATE ──────────────────────────────────────────────
let currentRole = 'superadmin';
let currentPage = '';
let currentUserId = null;
// Langue par défaut (utilisée dans les pages Paramètres)
let currentLang = localStorage.getItem('argos_lang') || 'fr';
// Nom affiché de l'utilisateur (utilisé par la page Paramètres)
let currentUserName = localStorage.getItem('currentUserName') || '';
// Notifications activées (par défaut true)
let notifsEnabled = (localStorage.getItem('argos_notifs') === 'false') ? false : true;
let maps   = {};
let charts = {};
let liveInterval = null;
let mapLayerIdx  = 0;
let trailsOn     = false;
let heatmapOn    = false;
let trailLayers  = [];
let heatLayer    = null;
let selectedSaleCoords = {lat: 0, lng: 0};

let userInteractionActive = false;
let interactionTimeout = null;

const I18N = {
  fr: {
    nav_dashboard: 'Dashboard',
    nav_map: 'Carte',
    nav_containers: 'Conteneurs',
    nav_sell: 'Attribution',
    nav_companies: 'Entreprises',
    'nav_clients-sa': 'Abonnés',
    'nav_clients-own': 'Mes Clients',
    nav_drivers: 'Chauffeurs',
    nav_stats: 'Statistiques',
    nav_events: 'Événements',
    nav_blockchain: 'Données Scellées',
    nav_blog: 'Publications',
    nav_settings: 'Paramètres',
    settings_saved: 'Paramètres sauvegardés',
    toast_refresh_rate: 'Actualisation réglée sur {v} secondes',
    btn_close: 'Fermer',
    map_legend: 'LÉGENDE',
  },
  en: {
    nav_dashboard: 'Dashboard',
    nav_map: 'Map',
    nav_containers: 'Containers',
    nav_sell: 'Assign',
    nav_companies: 'Companies',
    'nav_clients-sa': 'Subscribers',
    'nav_clients-own': 'My Clients',
    nav_drivers: 'Drivers',
    nav_stats: 'Stats',
    nav_events: 'Events',
    nav_blockchain: 'Blockchain',
    nav_blog: 'Publications',
    nav_settings: 'Settings',
    settings_saved: 'Settings saved',
    toast_refresh_rate: 'Refresh set to {v} seconds',
    btn_close: 'Close',
    map_legend: 'LEGEND',
  }
};

// Indicateur pour éviter les rafraîchissements concurrents
let isRefreshing = false;

// DB-backed live data
let DB_CONTAINERS = [];  // mis à jour depuis /api/containers/all
let DB_EVENTS     = [];
let DB_COMPANIES  = [];
let DB_CLIENTS    = [];
let DB_DRIVERS    = [];
let refreshTimer  = null;
let refreshSec = parseInt(localStorage.getItem('argos_refresh_rate')) || 10;
//  variable pour changer de langue 
// Fonction qui traduit un mot clé
function t(key) {
    return I18N[currentLang][key] || key;
}

function escapeHTML(value) {
    return String(value || '').replace(/[&<>\"']/g, function (c) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
}

function validateContainerNumber(value) {
    const ISO_VALUES = {
        A:10,B:12,C:13,D:14,E:15,F:16,G:17,H:18,I:19,J:20,K:21,
        L:23,M:24,N:25,O:26,P:27,Q:28,R:29,S:30,T:31,U:32,V:34,
        W:35,X:36,Y:37,Z:38
    };
    const cid = String(value || '').toUpperCase().replace(/[\s-]/g, '');
    if (cid.length !== 11) return { valid: false, msg: `${cid.length}/11 caractères` };
    if (!/^[A-Z]{4}\d{6}\d$/.test(cid)) return { valid: false, msg: 'Format : OOOUDDDDDDX' };
    let total = 0;
    for (let i = 0; i < 10; i++) {
        const c = cid[i];
        const val = /[A-Z]/.test(c) ? ISO_VALUES[c] : parseInt(c, 10);
        total += val * Math.pow(2, i);
    }
    const rem = total % 11;
    const expected = rem === 10 ? 0 : rem;
    const check = parseInt(cid[10], 10);
    return check === expected
        ? { valid: true, msg: 'Numéro ISO 6346 valide' }
        : { valid: false, msg: `Chiffre contrôle invalide (attendu: ${expected})` };
}

function updateIsoFeedback(input, feedbackId) {
  const feedback = document.getElementById(feedbackId);
  if(!feedback) return;
  if(!input.value.trim()) {
    input.style.borderColor = '';
    feedback.textContent = '';
    return;
  }
  const result = validateContainerNumber(input.value);
  input.style.borderColor = result.valid ? 'var(--green)' : 'var(--amber)';
  feedback.style.color = result.valid ? 'var(--green)' : 'var(--amber)';
  feedback.textContent = result.msg;
}

// ── SECURE API WRAPPER (ZERO-TRUST PROXY) ─────────────────
async function secureApiFetch(endpoint, options = {}) {
    const role = localStorage.getItem('currentRole') || '';
    const userId = localStorage.getItem('currentUserId') || '';
    options.headers = {
        ...(options.headers || {}),
        'X-Role': role,
        'X-User-Id': userId,
    };
    return await fetch(endpoint, options);
}

// Audio
const soundInfo  = new Audio('/static/audio/notif.mp3');
const soundAlert = new Audio('/static/audio/notif.mp3');
soundInfo.volume = 0.5; soundAlert.volume = 0.8;

// Fond de cartes disponibles
const MAP_LAYERS = [
  { name:'Satellite Sombre', url:'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png' },
  { name:'OpenStreetMap',    url:'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png' },
  { name:'Terrain Stadia',   url:'https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}{r}.png' },
  { name:'Satellite Esri',   url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}' },
];

// ── NAV ────────────────────────────────────────────────
const NAV = {
  superadmin:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie',          label:'Dashboard'},
    {id:'map',       icon:'fa-solid fa-map-location-dot',   label:'Monitoring'},
    {id:'containers',icon:'fa-solid fa-box',                label:'Conteneurs'},
    {id:'sell',      icon:'fa-solid fa-arrow-up-from-bracket',label:'Attribution'},
    {id:'companies', icon:'fa-solid fa-building',           label:'Entreprises'},
    {id:'clients-sa',icon:'fa-solid fa-users',              label:'Abonnés'},
    {id:'stats',     icon:'fa-solid fa-chart-line',         label:'Statistiques'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation',label:'Événements'},
    {id:'blockchain',icon:'fa-solid fa-link',               label:'Données Scellées'},
    {id:'blog',      icon:'fa-solid fa-newspaper',          label:'Publications'},
    {id:'settings',  icon:'fa-solid fa-gear',               label:'Paramètres'},
  ],
  company:[
    {id:'dashboard',icon:'fa-solid fa-chart-pie',label:'Dashboard'},
    {id:'map',icon:'fa-solid fa-map',label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',label:'Conteneurs Liés'},
    {id:'clients-own',icon:'fa-solid fa-users',label:'Mes Clients'},
    {id:'stats',icon:'fa-solid fa-chart-line',label:'Statistiques'},
    {id:'events',icon:'fa-solid fa-triangle-exclamation',label:'Alertes'},
    {id:'settings',icon:'fa-solid fa-gear',label:'Paramètres'},
  ],
  owner:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie',   label:'Mon Dashboard'},
    {id:'map',       icon:'fa-solid fa-map',          label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',          label:'Mes Conteneurs'},
    {id:'drivers',   icon:'fa-solid fa-truck',        label:'Chauffeurs'},
    {id:'clients-own',icon:'fa-solid fa-users',       label:'Clients'},
    {id:'stats',     icon:'fa-solid fa-chart-line',   label:'Analytiques'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation',label:'Alertes'},
    {id:'blockchain',icon:'fa-solid fa-link',         label:'Données Scellées'},
    {id:'settings',  icon:'fa-solid fa-gear',         label:'Paramètres'},
  ],
  driver:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie',           label:'Ma Mission'},
    {id:'map',       icon:'fa-solid fa-map',                  label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',                  label:'Mon Conteneur'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation', label:'Alertes'},
    {id:'settings',  icon:'fa-solid fa-gear',                 label:'Paramètres'},
  ],
  client:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie', label:'Mon Colis'},
    {id:'map',       icon:'fa-solid fa-map',        label:'Suivi'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation', label:'Événements'},
    {id:'settings',  icon:'fa-solid fa-gear',       label:'Paramètres'},
  ],
  port_authority:[
    {id:'dashboard', icon:'fa-solid fa-anchor', label:'Vue Portuaire'},
    {id:'containers',icon:'fa-solid fa-box', label:'Conteneurs Port'},
    {id:'events', icon:'fa-solid fa-triangle-exclamation', label:'Alertes'},
    {id:'blockchain',icon:'fa-solid fa-link', label:'Données Scellées'},
    {id:'settings', icon:'fa-solid fa-gear', label:'Paramètres'},
  ],
};

const aiState = {
  conversation: [],
  reportData: null,
  attachedImages: [] // Réintégré pour la gestion des pièces jointes IA
};

// ── SECURE API WRAPPER ─────────────────────────────────
// ══════════════════════════════════════════════════════
//  LOGIN
// ══════════════════════════════════════════════════════
async function doLogin(){
  const u  = document.getElementById('login-username').value.trim();
  const p  = document.getElementById('login-password').value.trim();
  const er = document.getElementById('login-error-message');
  er.innerText = '';
  if(!u || !p){ er.innerText = 'Veuillez remplir tous les champs.'; return; }
  try {
    const res  = await fetch('/api/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username:u, password:p})
    });
    const data = await res.json();
    console.log('Login response', res.status, data);
    if(res.ok && data.status === 'success'){
      localStorage.setItem('currentRole', data.role);
      localStorage.setItem('currentUserId', data.user_id || '');
      localStorage.setItem('isLoggedIn', 'true');
      currentRole   = data.role;
      currentUserId = data.user_id || null;
      document.getElementById('login-screen').style.display = 'none';
      document.getElementById('app').style.display = 'flex';
      initApp();
      showToast(`Bienvenue ! Connecté en tant que ${currentRole}`, 'success');
    } else {
      er.innerText = data.error || "Échec de l'authentification.";
    }
  } catch(e){ er.innerText = 'Erreur de connexion au serveur.'; }
}

// ══════════════════════════════════════════════════════
//  INIT APP
// ══════════════════════════════════════════════════════
// 1. Initialiser la variable avec la valeur sauvegardée (ou 10 secondes par défaut)


// 2. La fonction qui fait tourner la boucle
function startAutoRefresh() {
    // Nettoyer l'ancien timer s'il existe
    if (refreshTimer) clearInterval(refreshTimer);

    // Ne pas lancer l'auto-refresh si défini sur "0" (optionnel pour désactiver)
    if (refreshSec <= 0) return;

    refreshTimer = setInterval(async () => {
        // Logique silencieuse (sans toast) pour ne pas spammer l'écran
        if (currentPage === 'map' || currentPage === 'dashboard' || currentPage === 'containers') {
            await loadContainerData();
            if (maps['map-main']) refreshMapMarkers();
        }
        if (currentPage === 'events') {
            refreshEventTable();
        }
        buildNotificationsFromDB();
    }, refreshSec * 1000);
}

// 3. La fonction appelée quand on change le select dans les paramètres
function changeRefreshRate(v) {
    refreshSec = parseInt(v) || 10;
    // Sauvegarder le choix de l'utilisateur dans le navigateur
    localStorage.setItem('argos_refresh_rate', refreshSec);
    
    // Redémarrer le chronomètre avec le nouveau délai
    startAutoRefresh();
    showToast(`Actualisation réglée sur ${v} secondes`, 'info');
}
// ══════════════════════════════════════════════════════
//  INIT APP (Corrigé et Sécurisé)
// ══════════════════════════════════════════════════════
function initApp(){
  const roleLabels = {superadmin:'SUPER ADMIN', owner:'PROPRIÉTAIRE BB',
                      driver:'CHAUFFEUR', client:'CLIENT', company:'ENTREPRISE',
                      port_authority:'AUTORITÉ PORTUAIRE'};
  const roleInit   = {superadmin:'SA', owner:'PB', driver:'CH', client:'CL', company:'AG',
                      port_authority:'AP'};
  
  const saved = localStorage.getItem('theme');
  document.body.classList.toggle('theme-light', saved === 'light');

  const unlockAudio = () => {
    soundInfo.play().then(()=>{ soundInfo.pause(); soundInfo.currentTime=0; }).catch(()=>{});
    document.removeEventListener('click', unlockAudio);
  };
  document.addEventListener('click', unlockAudio);

  // 1. Sécurité : Vérifie que l'élément HTML existe avant de le modifier
  const roleLabelEl = document.getElementById('topbar-role-label');
  if(roleLabelEl) roleLabelEl.textContent = roleLabels[currentRole] || '';

  const avatarEl = document.getElementById('user-avatar');
  if(avatarEl) avatarEl.textContent       = roleInit[currentRole]   || '?';

  // 2. Initialisation des composants
  buildNav();
  buildNotifications();

  // 2b. Vérifier que le rôle renvoyé par le serveur existe bien dans la configuration de navigation.
  if (!NAV[currentRole] || NAV[currentRole].length === 0) {
      console.error(`Rôle inconnu pendant l'initialisation : ${currentRole}`);
      showToast(`Rôle inconnu : ${currentRole}. Déconnexion nécessaire.`, 'danger');
      doLogout();
      return;
  }
  
  // 3. Sécurité : Ne lance l'horloge que si la fonction existe vraiment
  if (typeof startClock === "function") {
      startClock();
  } else {
      console.warn("Fonction startClock() manquante - ignorée.");
  }

  startAutoRefresh();
  
  // 4. Lancement de la première page (Dashboard)
  if (NAV[currentRole] && NAV[currentRole].length > 0) {
      navigateTo(NAV[currentRole][0].id);
  }

  // 5. Sécurité : Ne lance le script GPS que si la fonction est bien définie
  if (typeof startDestinationProximityCheck === "function") {
      startDestinationProximityCheck();
  }
}

// ══════════════════════════════════════════════════════
//  NAV & ROUTING
// ══════════════════════════════════════════════════════
function buildNav(){
  const items = NAV[currentRole] || [];
  let html = '<div style="padding:20px 0">';
  items.forEach(item=>{
    const translatedLabel = (I18N[currentLang] && I18N[currentLang][`nav_${item.id}`]) ? I18N[currentLang][`nav_${item.id}`] : item.label;
    html += `<div class="nav-item" id="nav-${item.id}" onclick="navigateTo('${item.id}')">
      <span class="nav-icon"><i class="${item.icon}"></i></span>
      <span class="nav-label">${translatedLabel}</span>
    </div>`;
  });
  html += '</div>';
  document.getElementById('nav-container').innerHTML = html;
}

function navigateTo(page){
  if(currentPage === page) return;
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));
  const navEl = document.getElementById('nav-'+page);
  if(navEl) navEl.classList.add('active');
  if(page === 'ai'){ openAIAssistant(); return; }
  currentPage = page;
  renderPage(page);
}

function renderPage(page){
  const c = document.getElementById('pages-container');
  const builders = {
    dashboard:   ()=> buildDashboard(),
    map:         ()=> buildMapPage(),
    containers:  ()=> buildContainersPage(),
    sell:        ()=> buildSellPage(),
    companies:   ()=> buildCompaniesPage(),
    'clients-sa':()=> buildClientsPage(),
    'clients-own':()=> buildClientsPage(),
    drivers:     ()=> buildDriversPage(),
    stats:       ()=> buildStatsPage(),
    events:      ()=> buildEventsPage(),
    blockchain:  ()=> buildBlockchainPage(),
    blog:        ()=> buildBlogPage(),
    settings:    ()=> buildSettingsPage(),
  };
  c.innerHTML = (builders[page] || builders.dashboard)();
  populateContainerSelect('container-select');
  setTimeout(()=> initPageScripts(page), 60);
}

async function initPageScripts(page){
  if(page === 'dashboard'){
    initCharts(page);
    initMap('map-main', currentRole);
    if(currentRole === 'superadmin') await loadSADashboardData();
    else if(currentRole === 'owner') await loadOwnerDashboardData();
    else if(currentRole === 'driver' || currentRole === 'client') await loadContainerData();
  }
  if(page === 'map'){
    await loadContainerData();
    initMap('map-main', currentRole);
  }
  if(page === 'sell')   initMap('map-sale', 'sell');
  if(page === 'stats'){
    initCharts(page);
    await populateStatsBoiteSelect();
    loadDynamicStats('7d');
  }
  if(page === 'events'){
    await loadContainerData();
    refreshEventTable();
    startLiveMonitoring();
  }
  if(page === 'containers') await loadContainerData();
  if(page === 'companies'){
    await loadCompaniesData();
    if (typeof renderCompaniesTable === 'function') renderCompaniesTable();
  }
  if(page === 'clients-sa' || page === 'clients-own'){
    await loadClientsData();
    await loadAvailableContainers();
    if (typeof renderClientsTable === 'function') renderClientsTable();
  }
  if(page === 'drivers'){
    await loadContainerData();
    await loadDriversData();
    if (typeof renderDriversTable === 'function') renderDriversTable();
  }
  if(page === 'blockchain') await loadBlockchainData();
  if(page === 'settings'){
    const tog = document.getElementById('theme-toggle');
    if(tog) tog.checked = document.body.classList.contains('theme-light');
  }
}

// ══════════════════════════════════════════════════════
//  AUTO REFRESH
// ══════════════════════════════════════════════════════

function refreshCurrentView() {
    // Si on est sur la carte, on ne recharge pas le HTML, on bouge juste les points
    if (currentPage === 'map') {
        if (typeof refreshMapMarkers === 'function') refreshMapMarkers();
        return;
    }

    // 🛑 VÉRIFICATION CRITIQUE : L'utilisateur écrit-il dans un formulaire ?
    // Si on rafraîchit la page pendant qu'il écrit, ça va effacer tout son texte !
    const activeTag = document.activeElement ? document.activeElement.tagName : '';
    const isTyping = (activeTag === 'INPUT' || activeTag === 'TEXTAREA' || activeTag === 'SELECT');
    
    if (isTyping) {
        return; // On annule le rafraîchissement visuel pour ne pas le gêner
    }

    // Re-générer la page actuelle avec les nouvelles données
    // (Assure-toi que cette fonction correspond à celle de ton fichier pages.js)
    const container = document.getElementById('pages-container');
    if (container && typeof renderPage === 'function') {
        renderPage(currentPage);
    }
}
//  afficher les compagnies 
function buildCompaniesTable() {
    let tbody = '';
    
    if (!DB_COMPANIES || DB_COMPANIES.length === 0) {
        tbody = `<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text3);">Aucune entreprise enregistrée pour le moment.</td></tr>`;
    } else {
        DB_COMPANIES.forEach(comp => {
            tbody += `
                <tr>
                    <td style="font-family:var(--mono);">${escapeHTML(comp.niu || 'N/A')}</td>
                    <td><strong>${escapeHTML(comp.nom_agence)}</strong></td>
                    <td>${escapeHTML(comp.addresse_mail)}</td>
                    <td><span class="badge badge-info">${comp.nb_boites || 0} boîtes liées</span></td>
                    <td><span class="badge badge-ok">${comp.nb_abonnes || 0} abonnés actifs</span></td>
                    <td>${formatTime(comp.created_at)}</td>
                </tr>
            `;
        });
    }

    return `
        <div class="card" style="margin-top:20px; overflow-x:auto;">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>NIU</th>
                        <th>Nom de l'Entreprise</th>
                        <th>Email</th>
                        <th>Matériel (Boîtes)</th>
                        <th>Clients (Abonnés)</th>
                        <th>Date de création</th>
                    </tr>
                </thead>
                <tbody>
                    ${tbody}
                </tbody>
            </table>
        </div>
    `;
}

function resetInteractionTimeout() {
    if (interactionTimeout) clearTimeout(interactionTimeout);
    interactionTimeout = setTimeout(() => {
        userInteractionActive = false;
    }, 1200);
}

function markUserInteraction() {
    userInteractionActive = true;
    resetInteractionTimeout();
}

function shouldSkipAutoRefresh() {
    if (userInteractionActive) return true;
    const active = document.activeElement;
    if (active && ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName)) return true;
    if (document.querySelector('.modal-overlay')) return true;
    return false;
}

document.addEventListener('focusin', markUserInteraction);
document.addEventListener('focusout', resetInteractionTimeout);
document.addEventListener('pointerdown', markUserInteraction);
document.addEventListener('pointerup', resetInteractionTimeout);
document.addEventListener('keydown', markUserInteraction);

async function startAutoRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer);
    
    const tick = async () => {
        if (isRefreshing) {
            refreshTimer = setTimeout(tick, refreshSec * 1000);
            return;
        }
        if (shouldSkipAutoRefresh()) {
            refreshTimer = setTimeout(tick, refreshSec * 1000);
            return;
        }

        isRefreshing = true;

        try {
            // Lancer toutes les requêtes en même temps (très rapide)
            await Promise.all([
                loadContainerData(),
                loadEventsData(),
                loadCompaniesData(),
                loadClientsData()
            ]);
            
            // Mettre à jour l'affichage en toute sécurité
            if (typeof refreshCurrentView === 'function') refreshCurrentView();

        } catch (e) {
            console.warn("Erreur boucle de rafraîchissement:", e);
        } finally {
            isRefreshing = false; 
            refreshTimer = setTimeout(tick, refreshSec * 1000); // Reboucle toutes les 10s
        }
    };
    
    await tick(); // Déclenche le premier chargement
}

// ══════════════════════════════════════════════════════
//  DATA LOADERS

async function loadCompaniesData() {
    if (currentRole !== 'superadmin') return; // Seul le superadmin voit toutes les entreprises
    try {
        const res = await secureApiFetch('/api/companies');
        if (res.ok) DB_COMPANIES = await res.json();
    } catch (e) { console.error("Erreur chargement entreprises"); }
}

async function loadEventsData() {
    try {
        const res = await secureApiFetch('/api/events?limit=100');
        if (res.ok) DB_EVENTS = await res.json();
    } catch (e) { console.error("Erreur chargement événements"); }
}

async function loadClientsData() {
    try {
        const res = await secureApiFetch('/api/clients');
        if (res.ok) {
            DB_CLIENTS = await res.json();
        } else {
            DB_CLIENTS = [];
        }
    } catch (e) {
        console.error("Erreur chargement clients", e);
        DB_CLIENTS = [];
    }
    if (typeof renderClientsTable === 'function') renderClientsTable();
}

async function loadContainerData() {
    try {
        const res = await secureApiFetch('/api/containers/all');
        DB_CONTAINERS = await res.json();
        updateContainerPageUI();
    } catch(e) { console.error('loadContainerData error:', e); }
}



async function loadDriversData(){
  try {
    const res = await secureApiFetch('/api/drivers');
    if (res.ok) {
      DB_DRIVERS = await res.json();
    } else {
      DB_DRIVERS = [];
    }
    if (typeof renderDriversTable === 'function') renderDriversTable();
  } catch(e){ console.error('loadDriversData', e); }
}

// ══════════════════════════════════════════════════════
//  BLOCKCHAIN PAGE (Sécurisé par rôle)
// ══════════════════════════════════════════════════════
async function loadBlockchainData(page=1){
  try {
    const etype = document.getElementById('bc-filter-type')?.value || '';
    const boite = document.getElementById('bc-filter-boite')?.value || '';
    let url = `/api/blockchain/events?page=${page}&per_page=30`;
    if(etype) url += `&type=${etype}`;
    if(boite) url += `&boite=${boite}`;
    
    // REMPLACEMENT : secureApiFetch au lieu de fetch
    const res  = await secureApiFetch(url);
    const data = await res.json();
    
    // Si le back-end refuse l'accès (ex: client ou chauffeur)
    if (data.error) {
        document.getElementById('bc-tbody').innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--red)">${data.error}</td></tr>`;
        return;
    }
    
    renderBlockchainTable(data);

    // stats bar : On sécurise aussi cet appel
    const statsRes = await secureApiFetch('/api/blockchain/stats');
    const stats = await statsRes.json();
    const el = document.getElementById('bc-stats');
    if(el && stats.by_type) {
        el.innerHTML = `<span class="badge badge-info">${stats.total_blocks} blocs</span> ` +
        Object.entries(stats.by_type).map(([k,v])=>`<span class="badge badge-ok">${k}: ${v}</span>`).join(' ');
    }
  } catch(e){ console.error('loadBlockchainData', e); }
}

function renderBlockchainTable(data){
  const tbody = document.getElementById('bc-tbody');
  if(!tbody) return;
  if(!data.blocks || data.blocks.length === 0){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3)">Aucun bloc scellé</td></tr>';
    return;
  }
  tbody.innerHTML = data.blocks.map(b => {
    const payload = (b.payload || b.data || {});
    const payStr  = JSON.stringify(payload).substring(0, 80) + (JSON.stringify(payload).length > 80 ? '…' : '');
    const typeColor = b.event_type === 'GENESIS' ? 'var(--text3)'
                    : b.event_type === 'ALERTE_CRITIQUE' ? 'var(--red)'
                    : b.event_type === 'VENTE_ATTRIBUTION' ? 'var(--cyan)'
                    : 'var(--amber)';
    return `<tr>
      <td style="font-family:var(--mono);font-size:11px">#${b.block_index}</td>
      <td><span style="color:${typeColor};font-weight:600;font-size:12px">${b.event_type}</span></td>
      <td><span class="badge badge-info">${b.id_boite || '—'}</span></td>
      <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">${b.horodatage ? new Date(b.horodatage).toLocaleString('fr-FR') : '—'}</td>
      <td style="font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${payStr}</td>
      <td>
        <button class="btn-icon" style="font-size:11px" onclick="showBlockDetail(${JSON.stringify(b).replace(/"/g,'&quot;')})">
          <i class="fas fa-eye"></i> Détail
        </button>
      </td>
    </tr>`;
  }).join('');

  // Pagination
  const pages = Math.ceil(data.total / data.per_page);
  const pag   = document.getElementById('bc-pagination');
  if(pag && pages > 1){
    let html = '';
    for(let i=1; i<=pages; i++){
      html += `<button class="btn-icon${i===data.page?' btn-primary':''}" onclick="loadBlockchainData(${i})">${i}</button>`;
    }
    pag.innerHTML = html;
  }
}

function showBlockDetail(block){
  const d = (block.payload || block.data || {});
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:640px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-link" style="color:var(--cyan)"></i> Bloc #${block.block_index} — ${block.event_type}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div class="grid-2" style="margin-bottom:16px">
            <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Index</div><div class="stat-value" style="font-size:20px">#${block.block_index}</div></div>
            <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Boîte</div><div class="stat-value" style="font-size:18px">${block.id_boite || '—'}</div></div>
          </div>
          <div style="background:var(--bg3);border-radius:var(--radius);padding:12px;margin-bottom:12px">
            <div style="font-size:11px;color:var(--text3);margin-bottom:4px">HASH BLOC</div>
            <div style="font-family:var(--mono);font-size:10px;word-break:break-all;color:var(--cyan)">${block.block_hash}</div>
          </div>
          <div style="background:var(--bg3);border-radius:var(--radius);padding:12px;margin-bottom:12px">
            <div style="font-size:11px;color:var(--text3);margin-bottom:4px">HASH PRÉCÉDENT</div>
            <div style="font-family:var(--mono);font-size:10px;word-break:break-all;color:var(--text3)">${block.previous_hash}</div>
          </div>
          <div style="font-size:11px;color:var(--text3);margin-bottom:4px">HORODATAGE</div>
          <div style="font-family:var(--mono);font-size:12px;margin-bottom:12px">${block.horodatage ? new Date(block.horodatage).toLocaleString('fr-FR') : '—'}</div>
          <div style="font-size:11px;color:var(--text3);margin-bottom:4px">DONNÉES SCELLÉES</div>
          <pre style="background:var(--bg3);border-radius:var(--radius);padding:12px;font-size:11px;overflow-x:auto;max-height:200px;color:var(--green)">${JSON.stringify(d, null, 2)}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-primary" style="width:auto" onclick="verifyChain()"><i class="fas fa-shield-alt"></i> Vérifier la chaîne</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

// ========= EDIT / EXTEND MODALS ==========
function openEditClientModal(id){
  const c = DB_CLIENTS.find(x=>x.id_cni===id);
  if(!c) return showToast('Client introuvable','warn');
  const imageUrl = c.profile_image || c.cni_file;
  const canViewImage = imageUrl && (String(c.created_by||'')===String(localStorage.getItem('currentUserId')) || currentRole==='superadmin');
  
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:640px">
        <div class="modal-header"><div class="modal-title">Modifier Client — ${escapeHTML(c.nom||'')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-field"><label>Nom</label><input id="edit-client-nom" value="${escapeHTML(c.nom||'')}"></div>
            <div class="form-field"><label>Prénom</label><input id="edit-client-prenom" value="${escapeHTML(c.prenom||'')}"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Email</label><input id="edit-client-email" value="${escapeHTML(c.address_mail||'')}"></div>
            <div class="form-field"><label>Téléphone</label><input id="edit-client-phone" value="${escapeHTML(c.contact||'')}"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Boîtes assignées (séparées par virgule)</label><input id="edit-client-boites" value="${escapeHTML((c.boites||[c.id_boite||'']).join? (c.boites||[c.id_boite||'']).join(', '): (c.id_boite||''))}"></div>
            <div class="form-field"><label>Type Abonnement</label><input id="edit-client-sub" value="${escapeHTML(c.type_a||'')}"></div>
          </div>
          ${canViewImage ? `
          <div class="settings-item">
            <div class="settings-item-label"><i class="fas fa-image"></i> Document Profil</div>
            <button class="btn-icon" onclick="openImageModal('${escapeHTML(imageUrl)}', 'Document CNI', 'Document Profil - ${escapeHTML(c.nom||'')} ${escapeHTML(c.prenom||'')}')"><i class="fas fa-eye"></i> Voir</button>
          </div>
          ` : (imageUrl ? `<div class="settings-item"><div class="settings-item-label">Document Profil</div><span style="color:var(--text3)">Visible uniquement par le créateur</span></div>` : '')}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="submitEditClient('${escapeHTML(id)}')"><i class="fas fa-save"></i> Sauvegarder</button>
        </div>
      </div>
    </div>`;
}

async function submitEditClient(id){
  const payload = {
    id_cni: id,
    nom: document.getElementById('edit-client-nom')?.value,
    prenom: document.getElementById('edit-client-prenom')?.value,
    email: document.getElementById('edit-client-email')?.value,
    phone: document.getElementById('edit-client-phone')?.value,
    boites: (document.getElementById('edit-client-boites')?.value||'').split(',').map(s=>s.trim()).filter(Boolean),
    type_a: document.getElementById('edit-client-sub')?.value
  };
  try{
    const res = await fetch('/api/client/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d = await res.json();
    if(res.ok){ showToast('Client mis à jour','success'); closeModal(); if(typeof loadClientsData==='function') loadClientsData(); }
    else showToast(d.error||'Erreur mise à jour','danger');
  }catch(e){ console.error(e); showToast('Erreur réseau','danger'); }
}

function openExtendSubscriptionModal(id){
  const c = DB_CLIENTS.find(x=>x.id_cni===id); if(!c) return showToast('Client introuvable','warn');
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:480px">
        <div class="modal-header"><div class="modal-title">Allonger Abonnement — ${escapeHTML(c.nom||'')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-field"><label>Durée (jours)</label><input id="extend-days" type="number" value="30"></div>
          <div class="form-field"><label>Montant (CFA)</label><input id="extend-amount" type="number" value="5000"></div>
        </div>
        <div class="modal-footer"><button class="btn-secondary" onclick="closeModal()">Annuler</button>
        <button class="btn-primary" onclick="submitExtendSubscription('${escapeHTML(id)}')">Valider</button></div>
      </div>
    </div>`;
}

async function submitExtendSubscription(id){
  const days = parseInt(document.getElementById('extend-days')?.value)||0;
  const amount = parseInt(document.getElementById('extend-amount')?.value)||0;
  try{
    const res = await fetch('/api/client/extend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id_cni:id, days, amount})});
    const d = await res.json();
    if(res.ok){ showToast('Abonnement allongé','success'); closeModal(); if(typeof loadClientsData==='function') loadClientsData(); }
    else showToast(d.error||'Erreur extension','danger');
  }catch(e){ console.error(e); showToast('Erreur réseau','danger'); }
}

function openIncreaseContainersModal(id){
  const c = DB_CLIENTS.find(x=>x.id_cni===id); if(!c) return showToast('Client introuvable','warn');
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:520px">
        <div class="modal-header"><div class="modal-title">Ajouter Conteneurs — ${escapeHTML(c.nom||'')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-field"><label>Nombre de conteneurs</label><input id="add-cont-count" type="number" value="1"></div>
          <div class="form-field"><label>Type conteneur</label><select id="add-cont-type"><option value="DRY">DRY</option><option value="REF">Réfrigéré</option><option value="HC">High Cube</option></select></div>
        </div>
        <div class="modal-footer"><button class="btn-secondary" onclick="closeModal()">Annuler</button>
        <button class="btn-primary" onclick="submitAddContainers('${escapeHTML(id)}')">Ajouter</button></div>
      </div>
    </div>`;
}

async function submitAddContainers(id){
  const count = parseInt(document.getElementById('add-cont-count')?.value)||1;
  const type = document.getElementById('add-cont-type')?.value||'DRY';
  try{
    const res = await fetch('/api/client/add_containers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id_cni:id,count,type})});
    const d = await res.json();
    if(res.ok){ showToast('Conteneurs ajoutés','success'); closeModal(); if(typeof loadClientsData==='function') loadClientsData(); }
    else showToast(d.error||'Erreur ajout conteneurs','danger');
  }catch(e){ console.error(e); showToast('Erreur réseau','danger'); }
}

function openEditDriverModal(id){
  const d = DB_DRIVERS.find(x=>x.id_cni===id); 
  if(!d) return showToast('Chauffeur introuvable','warn');
  const imageUrl = d.profile_image || d.cni_file || d.image || d.document || d.logo;
  
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:640px">
        <div class="modal-header"><div class="modal-title">Modifier Chauffeur — ${escapeHTML(d.nom_chauffeurs||d.nom||'')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-field"><label>Nom</label><input id="edit-driver-nom" value="${escapeHTML(d.nom_chauffeurs||d.nom||'')}"></div>
            <div class="form-field"><label>Login</label><input id="edit-driver-login" value="${escapeHTML(d.login||'')}"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Téléphone</label><input id="edit-driver-phone" value="${escapeHTML(d.contact||'')}"></div>
            <div class="form-field"><label>Transport</label><input id="edit-driver-transport" value="${escapeHTML(d.moyen_transport||'')}"></div>
          </div>
          ${imageUrl ? `
          <div class="settings-item">
            <div class="settings-item-label"><i class="fas fa-image"></i> Document / Photo</div>
            <button class="btn-icon" onclick="openImageModal('${escapeHTML(imageUrl)}', 'Photo Chauffeur', 'Document - ${escapeHTML(d.nom_chauffeurs||d.nom||'')}')"><i class="fas fa-eye"></i> Voir</button>
          </div>
          ` : ''}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="submitEditDriver('${escapeHTML(id)}')"><i class="fas fa-save"></i> Sauvegarder</button>
        </div>
      </div>
    </div>`;
}

async function submitEditDriver(id){
  const payload = {
    id_cni: id,
    nom: document.getElementById('edit-driver-nom')?.value,
    login: document.getElementById('edit-driver-login')?.value,
    contact: document.getElementById('edit-driver-phone')?.value,
    moyen_transport: document.getElementById('edit-driver-transport')?.value
  };
  try{
    const res = await fetch('/api/driver/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d = await res.json();
    if(res.ok){ showToast('Chauffeur mis à jour','success'); closeModal(); if(typeof loadDriversData==='function') loadDriversData(); }
    else showToast(d.error||'Erreur mise à jour','danger');
  }catch(e){ console.error(e); showToast('Erreur réseau','danger'); }
}

function openEditCompanyModal(id){
  const e = DB_COMPANIES.find(x=>x.id===id); 
  if(!e) return showToast('Entreprise introuvable','warn');
  const imageUrl = e.logo || e.image || e.cni_file || e.profile_image || e.document;
  
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:640px">
        <div class="modal-header"><div class="modal-title">Modifier Entreprise — ${escapeHTML(e.nom_agence||'')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-field"><label>Nom</label><input id="edit-company-name" value="${escapeHTML(e.nom_agence||'')}"></div>
            <div class="form-field"><label>NIU</label><input id="edit-company-niu" value="${escapeHTML(e.niu||'')}"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Email</label><input id="edit-company-email" value="${escapeHTML(e.addresse_mail||'')}"></div>
            <div class="form-field"><label>Localisation</label><input id="edit-company-loc" value="${escapeHTML(e.lieu_residence||'')}"></div>
          </div>
          ${imageUrl ? `
          <div class="settings-item">
            <div class="settings-item-label"><i class="fas fa-image"></i> Logo / Document</div>
            <button class="btn-icon" onclick="openImageModal('${escapeHTML(imageUrl)}', 'Logo Entreprise', 'Logo - ${escapeHTML(e.nom_agence||'')}')"><i class="fas fa-eye"></i> Voir</button>
          </div>
          ` : ''}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="submitEditCompany('${escapeHTML(id)}')"><i class="fas fa-save"></i> Sauvegarder</button>
        </div>
      </div>
    </div>`;
}

async function submitEditCompany(id){
  const payload = { id, nom_agence:document.getElementById('edit-company-name')?.value, niu:document.getElementById('edit-company-niu')?.value, email:document.getElementById('edit-company-email')?.value, lieu_residence:document.getElementById('edit-company-loc')?.value };
  try{
    const res = await fetch('/api/company/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d = await res.json();
    if(res.ok){ showToast('Entreprise mise à jour','success'); closeModal(); if(typeof loadCompaniesData==='function') loadCompaniesData(); }
    else showToast(d.error||'Erreur mise à jour','danger');
  }catch(e){ console.error(e); showToast('Erreur réseau','danger'); }
}

async function verifyChain(){
  try {
    const res  = await secureApiFetch('/api/blockchain/verify');
    const data = await res.json();
    
    if (data.error) { showToast(data.error, 'danger'); return; }
    
    showToast(data.valid
      ? `✅ Chaîne valide — ${data.total_blocks} blocs vérifiés`
      : `❌ ${data.errors.length} erreurs détectées !`, data.valid ? 'success' : 'danger');
  } catch(e){ showToast('Erreur vérification', 'danger'); }
}

// ══════════════════════════════════════════════════════
//  DASHBOARD BUILDERS
// ══════════════════════════════════════════════════════
function buildDashboard(){
  if(currentRole === 'superadmin') return buildSADashboard();
  if(currentRole === 'owner')      return buildOwnerDashboard();
  if(currentRole === 'driver')     return buildDriverDashboard();
  if(currentRole === 'client')     return buildClientDashboard();
  return buildSADashboard();
}
// ?? manuelle refresh 
async function manualRefresh() {
    // Affiche un toast de début
    showToast('Actualisation en cours…', 'info');

    try {
        // Actualisation ciblée selon la page active (currentPage)
        if (currentPage === 'dashboard') {
            if (currentRole === 'superadmin') await loadSADashboardData();
            else if (currentRole === 'owner') await loadOwnerDashboardData();
            // Le dashboard client/driver se met à jour via loadContainerData()
        } 
        
        if (currentPage === 'map' || currentPage === 'dashboard' || currentPage === 'containers') {
            await loadContainerData();
            if (typeof refreshMapMarkers === 'function' && maps['map-main']) {
                refreshMapMarkers();
            }
        } 
        
        if (currentPage === 'events') {
            await refreshEventTable();
        }

        if (currentPage === 'blockchain') {
            await loadBlockchainData();
        }

        // Met toujours à jour les notifications globales
        if (typeof buildNotificationsFromDB === 'function') {
            await buildNotificationsFromDB();
        }

        showToast('Données à jour', 'success');
        
    } catch (error) {
        console.error("Erreur lors de l'actualisation manuelle :", error);
        showToast('Erreur lors de la récupération des données', 'danger');
    }
}

function buildSADashboard(){
  return `
  <div class="page active" id="page-dashboard">
    <div class="page-header">
      <div class="page-title">Dashboard Global <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px">
        <span class="badge badge-ok"><span class="badge-dot"></span>Système Opérationnel</span>
        <button class="btn-icon" onclick="manualRefresh()">
            <i class="fas fa-sync-alt"></i> Actualiser
        </button>
      </div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)">
        <div class="stat-label">Comptes Entreprises</div>
        <div class="stat-value" id="dash-tot-ent">--</div>
        <div class="stat-sub">Propriétaires enregistrés</div>
      </div>
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label">Abonnés Actifs</div>
        <div class="stat-value" id="dash-tot-subs">--</div>
        <div class="stat-sub">Statut Actif en BD</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label">Alertes Actives</div>
        <div class="stat-value" id="dash-tot-alerts">--</div>
        <div class="stat-sub">Enregistrées en BD</div>
      </div>
      <div class="stat-card" style="--accent:var(--purple)" onclick="navigateTo('blockchain')" style="cursor:pointer">
        <div class="stat-label"><i class="fas fa-link"></i> Blocs Scellés</div>
        <div class="stat-value" id="dash-bc-count">--</div>
        <div class="stat-sub" style="color:var(--cyan);cursor:pointer">↗ Voir données scellées</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Carte Globale Live</span>
          <button class="btn-icon" onclick="navigateTo('map')"><i class="fas fa-expand"></i> Plein écran</button>
        </div>
        <div class="map-container" style="height:280px"><div id="map-main"></div></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Alertes Récentes (BD)</span></div>
        <div id="dash-alertes-list" style="max-height:280px;overflow-y:auto">
          <div style="padding:20px;text-align:center;color:var(--text3)"><i class="fas fa-spinner fa-spin"></i> Chargement…</div>
        </div>
      </div>
    </div>
    <div class="grid-3" style="margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Top 5 Conteneurs Critiques</span></div>
        <div id="dash-crit-containers" class="zone-scrollable"><div style="padding:20px;text-align:center;color:var(--text3)">Chargement…</div></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Total d'abonnements mensuels</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-revenue"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Répartition Alertes (BD)</span></div>
        <div class="chart-wrap" style="height:180px"><canvas id="chart-subs"></canvas></div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;padding:8px">
          ${['var(--red)','var(--amber)','var(--cyan)','var(--green)','var(--purple)'].map((c,i)=>
            `<span style="display:flex;align-items:center;gap:4px;font-size:11px">
              <span style="width:10px;height:10px;border-radius:50%;background:${c};display:inline-block"></span>
              ${['Choc','Temp.','Humidité','Vitesse','Pression'][i]}
            </span>`).join('')}
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">5 Dernières Entreprises Enregistrées</span></div>
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Entreprise</th><th>Boîtes</th><th>Clients</th><th>Statut</th><th>Contact</th><th>Action</th></tr></thead>
          <tbody id="dash-top-entreprises"><tr><td colspan="6" style="text-align:center">Chargement…</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>`;
}

function buildOwnerDashboard(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Mon Dashboard <small>Propriétaire</small></div>
      <span class="badge badge-ok" id="owner-boites-badge"><span class="badge-dot"></span>Chargement…</span>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Boîtes Actives</div><div class="stat-value" id="ow-active">--</div></div>
      <div class="stat-card" style="--accent:var(--amber)"><div class="stat-label">Alertes</div><div class="stat-value" id="ow-alerts">--</div></div>
      <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Total Événements</div><div class="stat-value" id="ow-events">--</div></div>
      <div class="stat-card" style="--accent:var(--purple)" onclick="navigateTo('blockchain')" style="cursor:pointer">
        <div class="stat-label"><i class="fas fa-link"></i> Données Scellées</div>
        <div class="stat-value" id="ow-bc">--</div>
        <div class="stat-sub" style="color:var(--cyan)">↗ Voir</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Carte Temps Réel</span></div>
        <div class="map-container" style="height:320px"><div id="map-main"></div></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Mes Boîtes Noires</span></div>
        <div id="owner-boxes-list" style="max-height:320px;overflow-y:auto">
          <div style="padding:16px;text-align:center;color:var(--text3)">Chargement…</div>
        </div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card"><div class="card-header"><span class="card-title">Température (BD)</span></div>
        <div class="chart-wrap" style="height:180px"><canvas id="chart-temp"></canvas></div></div>
      <div class="card"><div class="card-header"><span class="card-title">Chocs & Alertes (BD)</span></div>
        <div class="chart-wrap" style="height:180px"><canvas id="chart-shock"></canvas></div></div>
    </div>
  </div>`;
}

function buildDriverDashboard(){
  const c = DB_CONTAINERS[0] || {};
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Ma Mission <small>${c.id_boite || 'En attente'}</small></div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label"><i class="fas fa-thermometer-half"></i> Température</div>
        <div class="stat-value" id="drv-temp">${c.temp !== null ? c.temp+'°C' : '--'}</div></div>
      <div class="stat-card" style="--accent:var(--blue)"><div class="stat-label"><i class="fas fa-tint"></i> Humidité</div>
        <div class="stat-value" id="drv-hum">${c.humidity !== null ? c.humidity+'%' : '--'}</div></div>
      <div class="stat-card" style="--accent:var(--green)"><div class="stat-label"><i class="fas fa-tachometer-alt"></i> Vitesse</div>
        <div class="stat-value" id="drv-speed">${(c.speed||0)} km/h</div></div>
      <div class="stat-card" style="--accent:var(--amber)"><div class="stat-label"><i class="fas fa-wave-square"></i> Chocs</div>
        <div class="stat-value">${c.shock||0} G</div></div>
    </div>
    <div class="card"><div class="card-header"><span class="card-title">Position Actuelle</span></div>
      <div class="map-container" style="height:350px"><div id="map-main"></div></div>
    </div>
  </div>`;
}

function buildClientDashboard(){
  const c = DB_CONTAINERS[0] || {};
  return `
  <div class="page active">
    <div class="page-header"><div class="page-title">Mon Colis <small>Suivi en temps réel</small></div></div>
    <div class="grid-2" style="margin-bottom:20px">
      <div class="card"><div class="card-header"><span class="card-title">Suivi GPS</span></div>
        <div class="map-container" style="height:300px"><div id="map-main"></div></div>
      </div>
      <div class="card"><div class="card-header"><span class="card-title">État du Conteneur</span></div>
        <div class="sensor-grid">
          <div class="sensor-tile" style="--sensor-color:var(--cyan)">
            <div class="sensor-unit"><i class="fas fa-thermometer-half"></i></div>
            <div class="sensor-val">${c.temp !== null && c.temp !== undefined ? c.temp : '--'}</div>
            <div class="sensor-label">Temp °C</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:var(--blue)">
            <div class="sensor-unit"><i class="fas fa-tint"></i></div>
            <div class="sensor-val">${c.humidity !== null && c.humidity !== undefined ? c.humidity : '--'}</div>
            <div class="sensor-label">Humidité %</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:var(--amber)">
            <div class="sensor-unit"><i class="fas fa-wave-square"></i></div>
            <div class="sensor-val">${c.shock || 0}</div>
            <div class="sensor-label">Chocs G</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:var(--green)">
            <div class="sensor-unit"><i class="fas fa-tachometer-alt"></i></div>
            <div class="sensor-val">${c.speed || 0}</div>
            <div class="sensor-label">km/h</div>
          </div>
        </div>
        <div style="margin-top:12px">
          <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':'danger'}">
            ${c.status ? c.status.toUpperCase() : 'INCONNU'}
          </span>
        </div>
      </div>
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════
//  MAP PAGE
// ══════════════════════════════════════════════════════
function buildMapPage(){
  const ok  = DB_CONTAINERS.filter(c=>c.status==='ok').length;
  const wa  = DB_CONTAINERS.filter(c=>c.status==='warning').length;
  const da  = DB_CONTAINERS.filter(c=>c.status==='danger').length;
  const off = DB_CONTAINERS.filter(c=>c.status==='off').length;
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Carte Monitoring <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <span class="badge badge-ok"><span class="badge-dot"></span>${ok} OK</span>
        <span class="badge badge-warn">${wa} Alertes</span>
        <span class="badge badge-danger">${da} Critiques</span>
        <span class="badge badge-off">${off} Hors ligne</span>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 300px;gap:16px;height:calc(100vh - 160px)">
      <div class="card" style="padding:0;overflow:hidden;position:relative">
        <div id="map-main" style="height:100%"></div>
        <div class="map-overlay">
          <div class="map-legend">
            <div style="font-size:11px;font-weight:600;margin-bottom:6px;letter-spacing:1px">LÉGENDE</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Nominal</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--amber)"></div>Alerte</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>Critique</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--text3)"></div>Hors ligne</div>
          </div>
        </div>
        <div class="map-controls">
          <button class="map-btn" onclick="showAllContainers()" title="Vue globale"><i class="fas fa-globe"></i></button>
          <button class="map-btn" onclick="toggleMapLayer()" title="Changer fond de carte"><i class="fas fa-layer-group"></i></button>
          <button class="map-btn" onclick="toggleTrails()" title="Traces GPS" id="btn-trails"><i class="fas fa-route"></i></button>
          <button class="map-btn" onclick="toggleHeatmap()" title="Heatmap alertes" id="btn-heat"><i class="fas fa-fire"></i></button>
          <button class="map-btn" onclick="fitAllMarkers()" title="Centrer sur tous"><i class="fas fa-compress-arrows-alt"></i></button>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;overflow-y:auto">
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:8px">Conteneurs (${DB_CONTAINERS.length})</div>
          <div style="position:relative;margin-bottom:8px">
            <i class="fas fa-search" style="position:absolute;left:10px;top:8px;color:var(--text3);font-size:12px"></i>
            <input type="text" placeholder="Rechercher…" style="width:100%;padding:6px 10px 6px 28px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);color:var(--text);font-size:12px;outline:none" oninput="filterContainersList(this.value)">
          </div>
          <div id="containers-sidebar-list" class="zone-scrollable" style="max-height: 35vh;">
            ${DB_CONTAINERS.map(c=>{
              const col = c.status==='ok'?'var(--green)':c.status==='warning'?'var(--amber)':c.status==='danger'?'var(--red)':'var(--text3)';
              return `<div class="container-item status-${c.status}" style="margin-bottom:6px;cursor:pointer" onclick="focusContainerDB('${c.id_boite||c.id}')">
                <div style="width:8px;height:8px;border-radius:50%;background:${col}"></div>
                <div class="container-info">
                  <div class="container-id" style="font-size:12px">${c.id_boite || c.id}</div>
                  <div style="font-size:10px;color:var(--text3)">${c.type_conteneurs || '—'} • ${c.speed||0} km/h</div>
                  <div style="font-size:10px;color:var(--text3)">${c.lastUpdate}</div>
                </div>
              </div>`;
            }).join('')}
          </div>
        </div>
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:8px">Données Live</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div class="sensor-tile" style="--sensor-color:var(--cyan);padding:10px">
              <div class="sensor-unit" style="font-size:10px"><i class="fas fa-thermometer-half"></i></div>
              <div class="sensor-val" style="font-size:20px" id="map-temp">${DB_CONTAINERS[0]?.temp ?? '--'}</div>
              <div class="sensor-label" style="font-size:10px">Temp</div>
            </div>
            <div class="sensor-tile" style="--sensor-color:var(--amber);padding:10px">
              <div class="sensor-unit" style="font-size:10px"><i class="fas fa-wave-square"></i></div>
              <div class="sensor-val" style="font-size:20px" id="map-shock">${DB_CONTAINERS.find(c=>c.shock>0)?.shock ?? 0}</div>
              <div class="sensor-label" style="font-size:10px">Choc G</div>
            </div>
          </div>
        </div>
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:8px">Alertes Actives (BD)</div>
          <div id="map-alerts-list" class="zone-scrollable" style="max-height: 25vh;">
            ${DB_CONTAINERS.filter(c=>c.alerts&&c.alerts.length>0).slice(0,8).map(c=>
              c.alerts.slice(0,2).map(a=>`
              <div class="timeline-item" style="padding:5px 0">
                <div class="timeline-dot" style="background:${c.status==='danger'?'var(--red)':'var(--amber)'}"></div>
                <div class="timeline-content">
                  <div style="font-size:11px">${c.id_boite}: ${a.substring(0,40)}</div>
                  <div class="timeline-time">${c.lastUpdate}</div>
                </div>
              </div>`).join('')
            ).join('') || '<div style="color:var(--text3);font-size:12px">Aucune alerte active</div>'}
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════
//  CONTAINERS PAGE (DB-driven)
// ══════════════════════════════════════════════════════
function buildContainersPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Conteneurs <small id="cont-total">${DB_CONTAINERS.length} Total</small></div>
      <div style="display:flex;gap:8px">
        <div style="position:relative;width:200px">
          <i class="fas fa-search" style="position:absolute;left:12px;top:8px;color:var(--text3);font-size:12px"></i>
          <input type="text" placeholder="Rechercher…" id="container-search"
            style="padding:6px 14px 6px 28px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;color:var(--text);font-size:13px;outline:none;width:100%"
            oninput="filterContainers(this.value)">
        </div>
        <button class="btn-icon" onclick="loadContainerData().then(()=>renderPage('containers'))"><i class="fas fa-sync"></i> Actualiser</button>
      </div>
    </div>
    <div class="tabs" id="cont-tabs">
      <div class="tab active" onclick="filterContainersStatus('all',this)">Tous (${DB_CONTAINERS.length})</div>
      <div class="tab" onclick="filterContainersStatus('ok',this)"><i class="fas fa-check-circle" style="color:var(--green)"></i> OK (${DB_CONTAINERS.filter(c=>c.status==='ok').length})</div>
      <div class="tab" onclick="filterContainersStatus('warning',this)"><i class="fas fa-exclamation-triangle" style="color:var(--amber)"></i> Alerte (${DB_CONTAINERS.filter(c=>c.status==='warning').length})</div>
      <div class="tab" onclick="filterContainersStatus('danger',this)"><i class="fas fa-circle" style="color:var(--red);font-size:8px"></i> Critique (${DB_CONTAINERS.filter(c=>c.status==='danger').length})</div>
      <div class="tab" onclick="filterContainersStatus('off',this)"><i class="fas fa-power-off" style="color:var(--text3)"></i> Hors ligne (${DB_CONTAINERS.filter(c=>c.status==='off').length})</div>
    </div>
    <div id="containers-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px; max-height: calc(100vh - 200px); overflow-y: auto; padding-right: 10px;">
      ${DB_CONTAINERS.length ? DB_CONTAINERS.map(c=>buildContainerCard(c)).join('') :
        '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text3)"><i class="fas fa-box-open" style="font-size:40px;margin-bottom:12px;display:block"></i>Aucun conteneur en base de données</div>'}
    </div>
  </div>`;
}

function buildContainerCard(c){
  const statusColors = {ok:'var(--green)',warning:'var(--amber)',danger:'var(--red)',off:'var(--text3)'};
  const col = statusColors[c.status] || 'var(--text3)';
  const hasData = c.temp !== null && c.temp !== undefined;
  return `
  <div class="card container-item status-${c.status}" style="display:block;cursor:pointer" onclick="showContainerDetailDB('${c.id_boite||c.id}')">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:8px">
        <div style="width:10px;height:10px;border-radius:50%;background:${col};${c.status!=='off'?'box-shadow:0 0 8px '+col:''}"></div>
        <span style="font-family:var(--display);font-size:16px;color:var(--cyan)">${c.id_boite || c.id}</span>
      </div>
      <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}">${c.status.toUpperCase()}</span>
    </div>
    <div style="font-size:12px;color:var(--text2);margin-bottom:6px"><i class="fas fa-box"></i> ${c.type_conteneurs||'—'} • <i class="fas fa-microchip"></i> ${c.type_boite||'—'}</div>
    ${hasData ? `
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px">
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:${c.temp>32?'var(--red)':c.temp>28?'var(--amber)':'var(--green)'}">${c.temp}</div>
        <div style="font-size:10px;color:var(--text3)">°C</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:${c.humidity>75?'var(--red)':c.humidity>65?'var(--amber)':'var(--green)'}">${c.humidity??'--'}</div>
        <div style="font-size:10px;color:var(--text3)">%HR</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono)">${c.speed??0}</div>
        <div style="font-size:10px;color:var(--text3)">km/h</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:${c.shock>5?'var(--red)':c.shock>0?'var(--amber)':'var(--green)'}">${c.shock??0}</div>
        <div style="font-size:10px;color:var(--text3)">G</div>
      </div>
    </div>` : '<div style="text-align:center;padding:16px;color:var(--text3)"><i class="fas fa-power-off"></i> Aucune donnée capteur</div>'}
    ${c.alerts && c.alerts.length>0 ? `<div style="margin-top:8px;display:flex;gap:4px;flex-wrap:wrap">${c.alerts.slice(0,2).map(a=>`<span class="badge badge-warn" style="font-size:10px"><i class="fas fa-exclamation-triangle"></i> ${a.substring(0,30)}</span>`).join('')}</div>` : ''}
    <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text3);margin-top:8px">
      <span>${c.resistance||'—'}</span><span>MàJ: ${c.lastUpdate}</span>
    </div>
  </div>`;
}

function updateContainerPageUI(){
  if(currentPage === 'containers'){
    const grid = document.getElementById('containers-grid');
    if(grid) grid.innerHTML = DB_CONTAINERS.length
      ? DB_CONTAINERS.map(c=>buildContainerCard(c)).join('')
      : '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text3)">Aucun conteneur</div>';
  }
}

// +++++++++++++++++++++++++++++ vide le conteneurs

async function viderContainer(id_boite) {
    const motif = prompt("Motif du vidage :");
    if (!motif) return;
    try {
        const res = await fetch('/api/container/vider', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_boite, motif, user_id: currentUserId })
        });
        const data = await res.json();
        if (res.ok) {
            showToast("Demande de vidage envoyée. En attente de validation.", "info");
        } else {
            showToast(data.error, "danger");
        }
    } catch(e) { showToast("Erreur réseau", "danger"); }
}

async function showContainerDetailDB(id){
  const c = DB_CONTAINERS.find(x=>String(x.id_boite)===String(id) || String(x.id)===String(id));
  if(!c){ showToast('Conteneur introuvable','warn'); return; }

  // Charger seuils depuis BD
  let seuils = {};
  try {
    const sr = await fetch(`/api/config/thresholds/${c.id_boite||c.id}`);
    seuils = await sr.json();
  } catch(e){}

  // Historique events
  let evts = [];
  try {
    const er = await fetch(`/api/events?container=${c.id_boite||c.id}&limit=10`);
    evts = await er.json();
  } catch(e){}

  const hasData = c.temp !== null && c.temp !== undefined;
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:720px">
        <div class="modal-header">
          <div>
            <div class="modal-title" style="font-family:var(--display);color:var(--cyan)">${c.id_boite||c.id}</div>
            <div style="font-size:12px;color:var(--text3)">${c.type_conteneurs||'—'} • ${c.type_boite||'—'} • v${c.versions||'?'}</div>
          </div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
            <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}">${c.status.toUpperCase()}</span>
            <span style="font-size:12px;color:var(--text3)"><i class="fas fa-clock"></i> ${c.lastUpdate}</span>
            ${c.resistance?`<span class="badge badge-info">Résistance: ${c.resistance}</span>`:''}
          </div>
          ${hasData ? `
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px">
            ${[
              ['fa-thermometer-half','Température',(c.temp??'--')+'°C', c.temp>32?'var(--red)':c.temp>28?'var(--amber)':'var(--green)'],
              ['fa-tint','Humidité',(c.humidity??'--')+'%', c.humidity>75?'var(--red)':c.humidity>65?'var(--amber)':'var(--green)'],
              ['fa-compress-arrows-alt','Pression',(c.pressure??'--')+' hPa','var(--cyan)'],
              ['fa-wave-square','Chocs',(c.shock??0)+' G', c.shock>5?'var(--red)':c.shock>0?'var(--amber)':'var(--green)'],
              ['fa-tachometer-alt','Vitesse',(c.speed??0)+' km/h','var(--text)'],
              ['fa-map-marker-alt','GPS',c.lat&&c.lon?`${Number(c.lat).toFixed(4)},${Number(c.lon).toFixed(4)}`:'—','var(--text2)'],
              ['fa-shield-alt','Seuil Temp',`${seuils.temp_max||32}°C`,'var(--amber)'],
              ['fa-exclamation-triangle','Alertes actives',c.alerts.length,'var(--red)'],
            ].map(([ic,lb,va,co])=>`
            <div style="background:var(--card2);border:1px solid var(--border);border-radius:var(--radius);padding:10px;text-align:center">
              <div><i class="fas ${ic}"></i></div>
              <div style="font-size:10px;color:var(--text3);margin:4px 0">${lb}</div>
              <div style="font-size:13px;font-weight:700;color:${co}">${va}</div>
            </div>`).join('')}
          </div>` : '<div class="alert alert-warn"><i class="fas fa-power-off"></i> Aucune donnée capteur reçue</div>'}
          ${c.alerts && c.alerts.length>0 ? `
          <div style="margin-bottom:16px">
            <div style="font-size:12px;color:var(--text3);margin-bottom:6px">ALERTES ACTIVES</div>
            ${c.alerts.map(a=>`<div class="alert alert-warn" style="margin-bottom:4px;font-size:12px"><i class="fas fa-exclamation-triangle"></i> ${a}</div>`).join('')}
          </div>` : ''}
          <div>
            <div style="font-size:12px;color:var(--text3);margin-bottom:6px">DERNIERS ÉVÉNEMENTS (BD)</div>
            ${evts.length ? evts.slice(0,5).map(e=>{
              let msgs=[]; try{if(e.notif)msgs=JSON.parse(e.notif);}catch(ex){}
              return `<div class="timeline-item">
                <div class="timeline-dot" style="background:${msgs.length?'var(--red)':'var(--green)'}"></div>
                <div class="timeline-content">
                  <div style="font-size:12px">${e.log_action} — T:${e.temperature??'--'}°C H:${e.humidite??'--'}%</div>
                  <div class="timeline-time">${new Date(e.horodatage).toLocaleString('fr-FR')}</div>
                </div>
              </div>`;
            }).join('') : '<div style="color:var(--text3);font-size:12px">Aucun événement récent</div>'}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-secondary" onclick="openChangeContainerModal('${c.id_boite||c.id}')"><i class="fas fa-exchange-alt"></i> Changer</button>
          <button class="btn-primary" style="background:var(--red)" onclick="viderContainer('${c.id_boite}')">
              <i class="fas fa-trash-alt"></i> Destockage
          </button>
          <button class="btn-primary" style="width:auto" onclick="closeModal();navigateTo('map')"><i class="fas fa-map-marker-alt"></i> Voir Carte</button>
          <button class="btn-primary" style="width:auto" onclick="closeModal();navigateTo('events')"><i class="fas fa-list"></i> Événements</button>
          <button class="export-btn" onclick="openAIAssistant('${c.id_boite||c.id}')"><i class="fas fa-robot"></i> Rapport IA</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

async function changerConteneur(id_boite) {
    // 1. Vider l'ancien conteneur (détacher)
    await fetch('/api/container/vider', { method: 'POST', body: JSON.stringify({ id_boite, motif: "Changement de conteneur", auto_validate: true }) });
    // 2. Récupérer la liste des conteneurs disponibles (non liés)
    const disponibles = await fetch('/api/containers/disponibles').then(r=>r.json());
    const choices = disponibles.map(c => c.id || c.id_conteneurs || c.id_boite).filter(Boolean);
    let nouveau = prompt("Nouvel ID du conteneur (ou choisir parmi : " + choices.join(", "));
    if (!nouveau) return;
    // 3. Vérifier si existe, sinon le créer
    await fetch('/api/container/lier', { method: 'POST', body: JSON.stringify({ id_boite, id_conteneur: nouveau }) });
    showToast("Conteneur changé avec succès.", "success");
}

async function openChangeContainerModal(id_boite) {
  try {
    const res = await secureApiFetch('/api/containers/disponibles');
    const disponibles = res.ok ? await res.json() : [];

    const options = disponibles.map(d => {
      const label = d.id_conteneurs || d.id || d.id_boite || '';
      const value = d.id_conteneurs || d.id || d.id_boite || '';
      return `<option value="${escapeHTML(value)}">${escapeHTML(label)}${d.id_boite?(' — boîte #'+d.id_boite):''}</option>`;
    }).join('');

    const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:640px">
        <div class="modal-header"><div class="modal-title">Changer le Conteneur — ${escapeHTML(id_boite)}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div style="margin-bottom:8px;font-size:13px;color:var(--text3)">Rechercher ou sélectionner un conteneur disponible pour remplacer celui-ci.</div>
          <div style="display:flex;gap:8px;align-items:center">
            <input type="text" id="change-search" placeholder="Rechercher par ID…" style="flex:1;padding:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);border-radius:6px" oninput="filterChangeOptions(this.value)">
            <select id="change-select" style="width:260px;padding:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);border-radius:6px">${options || '<option value="">Aucun conteneur disponible</option>'}</select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="confirmChangeContainer('${escapeHTML(id_boite)}')"><i class="fas fa-exchange-alt"></i> Confirmer le Changement</button>
        </div>
      </div>
    </div>`;
    document.getElementById('modal-root').innerHTML = html;
  } catch(e){
    console.error(e); showToast('Erreur chargement conteneurs disponibles','danger');
  }
}

function filterChangeOptions(q){
  q = (q||'').toLowerCase();
  const sel = document.getElementById('change-select');
  if(!sel) return;
  for(let i=0;i<sel.options.length;i++){
    const o = sel.options[i];
    o.style.display = (o.text.toLowerCase().includes(q) || o.value.toLowerCase().includes(q)) ? '' : 'none';
  }
}

async function confirmChangeContainer(id_boite){
  const sel = document.getElementById('change-select');
  if(!sel) return showToast('Aucun conteneur sélectionné','warn');
  const id_conteneur = sel.value;
  if(!id_conteneur) return showToast('Sélectionnez un conteneur valide','warn');
  try {
    const res = await fetch('/api/container/lier', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id_boite, id_conteneur })
    });
    const data = await res.json();
    if(res.ok){
      showToast('Conteneur changé avec succès','success');
      closeModal();
      await loadContainerData();
    } else {
      showToast(data.error || 'Erreur changement conteneur','danger');
    }
  } catch(e){ console.error(e); showToast('Erreur réseau', 'danger'); }
}

async function continuerContainer(id_boite) {
    // Vérifier si étapes existent
    const etapes = await fetch(`/api/trajet/etapes?boite=${id_boite}`).then(r=>r.json());
    if (etapes.length === 0) {
        // Première étape : demande de destination
        const dest = prompt("Point d'arrivée (ville) :");
        if (dest) {
            // géocoder pour obtenir lat/lon
            const coords = await geocode(dest);
            await fetch('/api/trajet/etapes', { method: 'POST', body: JSON.stringify({ id_boite, lat: coords.lat, lon: coords.lng }) });
        }
    } else {
        const next = etapes.find(e => !e.atteint);
        if (next) {
            const distance = getDistanceFromLatLonInM(currentPos.lat, currentPos.lon, next.lat, next.lon);
            if (distance <= 30000) {
                // Notification déjà envoyée
                if (distance <= 100) {
                    // Arrivé
                    const auto = confirm("Arrivé au point. Continuer automatiquement dans 45 min ? (Sinon manuel)");
                    if (auto) {
                        setTimeout(() => finaliserEtape(id_boite, next.id), 45*60*1000);
                    } else {
                        finaliserEtape(id_boite, next.id);
                    }
                }
            } else {
                showToast("Encore trop loin du prochain point.", "info");
            }
        }
    }
}

async function finaliserEtape(id_boite, id_etape) {
    const ajouterColis = confirm("Ajouter d'autres colis ?");
    if (ajouterColis) {
        // Afficher modal d'abonnement (comme dans addNewClient)
        showModal('addClientFromContinuation', { id_boite });
    }
    await fetch('/api/trajet/etape/atteinte', { method: 'POST', body: JSON.stringify({ id_etape }) });
    showToast("Étape marquée comme atteinte.", "success");
}
// ══════════════════════════════════════════════════════
//  SELL PAGE
// ══════════════════════════════════════════════════════
function buildSellPage(){
  return `
  <div class="page active">
    <div class="page-header"><div class="page-title">Ventes & Attribution <small>Boîtes Noires</small></div></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><span class="card-title">Nouvelle Vente / Attribution</span></div>
          <div class="form-row">
            <div class="form-field"><label>Nombre de Boîtes</label>
              <input type="number" min="1" placeholder="1" id="sell-qty" oninput="updateContainerIdFields()"></div>
            <div id="container-ids-section"></div>
            <div class="form-field"><label>Nom de l'Entreprise</label>
              <input type="text" placeholder="Nom entreprise" id="sell-company"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Localisation</label><input type="text" placeholder="Ville, Pays" id="sell-location"></div>
            <div class="form-field"><label>Téléphone</label><input type="text" placeholder="+237 6…" id="sell-phone"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Login</label><input type="text" id="sell-login"></div>
            <div class="form-field"><label>Mot de passe</label><input type="password" id="sell-password"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Email</label><input type="email" id="sell-email"></div>
            <div class="form-field"><label>Type Abonnement</label>
              <select id="sell-sub">
                <option value="monthly">Mensuel — 15 000 CFA/BB</option>
                <option value="yearly">Annuel — 150 000 CFA/BB</option>
                <option value="custom">Personnalisé</option>
              </select>
            </div>
          </div>
          <div class="form-field"><label>NIU</label><input type="text" placeholder="NIU" id="sell-niu"></div>
          <div class="form-field">
            <label>Type de Conteneur</label>
            <select id="container-type" onchange="handleContainerTypeChange()">
              <option value="">-- Sélectionner --</option>
              <option value="DRY">DRY</option>
              <option value="HighCube">High Cube</option>
              <option value="Refrigere">Réfrigéré</option>
              <option value="OpenTop">Open Top</option>
            </select>
            <small id="open-top-note" style="display:none;color:var(--amber)">Ces conteneurs sont dépourvus de toit.</small>
          </div>
          <div id="container-volume-section" style="display:none">
            <div class="form-row">
              <div class="form-field"><label>Volume (m³)</label><input type="number" id="container-volume" oninput="calcPerimeter()"></div>
              <div class="form-field"><label>Périmètre calculé (m)</label><input type="text" id="container-perimeter" readonly></div>
            </div>
            <div class="form-field" id="pouce-field" style="display:none">
              <label>Valeur en pouces</label><input type="text" id="container-pouce" placeholder="ex: 20' ou 40'">
            </div>
          </div>
          <div class="form-field" style="margin-bottom:16px">
            <label>Photo CNI</label>
            <div class="upload-zone" onclick="document.getElementById('cni-upload').click()">
              <div class="upload-icon"><i class="fas fa-id-card"></i></div>
              <div class="upload-text">Cliquer pour charger la photo CNI</div>
            </div>
            <input type="file" id="cni-upload" accept="image/*" style="display:none" onchange="previewFile(this,'cni-preview')">
            <div id="cni-preview"></div>
          </div>
          <button class="btn-primary" onclick="submitSale()"><i class="fas fa-check"></i> Valider la Vente & Créer le Compte</button>
        </div>
      </div>
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><span class="card-title"><i class="fas fa-map-marker-alt"></i> Position du Client</span></div>
          <p style="font-size:12px;color:var(--text3);margin-bottom:10px">Cliquez sur la carte pour marquer l'emplacement</p>
          <div class="map-container" style="height:300px"><div id="map-sale"></div></div>
          <div id="map-sale-coords" style="font-size:12px;color:var(--cyan);font-family:var(--mono);margin-top:8px;padding:6px;background:var(--bg3);border-radius:var(--radius)">Cliquez sur la carte…</div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Résumé Vente</span></div>
          <div id="sale-summary"><div style="text-align:center;padding:20px;color:var(--text3)">Remplissez le formulaire</div></div>
        </div>
      </div>
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════
//  GESTION DES FORMULAIRES (Colis / Abonnés)
// ══════════════════════════════════════════════════════

/**
 * Remplit une liste déroulante (select) avec UNIQUEMENT les conteneurs du propriétaire
 * @param {string} selectElementId - L'ID de la balise <select> dans ton HTML
 */
function populateOwnerContainersSelect(selectElementId) {
    const selectEl = document.getElementById(selectElementId);
    if (!selectEl) return;

    // On s'assure qu'on ne liste que les conteneurs ayant un identifiant de conteneur
    const conteneursValides = DB_CONTAINERS.filter(c => c.id || c.id_conteneurs);

    if (conteneursValides.length === 0) {
        selectEl.innerHTML = '<option value="">Aucun conteneur disponible</option>';
        selectEl.disabled = true;
        return;
    }

    // Le selecteur affiche l'ID du conteneur, mais stocke la boîte noire
    let options = '<option value="">-- Sélectionnez un de vos conteneurs --</option>';
    
    conteneursValides.forEach(c => {
        const containerId = c.id || c.id_conteneurs;
        const boxId = c.id_boite || c.id;
        options += `<option value="${boxId}">${escapeHTML(containerId)} (Boîte #${boxId})</option>`;
    });

    selectEl.innerHTML = options;
    selectEl.disabled = false;
}

// ══════════════════════════════════════════════════════
//  COMPANIES PAGE (DB)
// ══════════════════════════════════════════════════════
function buildCompaniesPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Gestion Entreprises</div>
      <div style="position:relative;width:220px">
        <i class="fas fa-search" style="position:absolute;left:12px;top:8px;color:var(--text3);font-size:12px"></i>
        <input type="text" placeholder="Rechercher…"
          style="padding:6px 14px 6px 28px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;color:var(--text);font-size:13px;outline:none;width:100%"
          oninput="filterTable('companies-tbody',this.value)">
      </div>
    </div>
    <div class="data-table-wrap card">
      <table class="data-table">
        <thead><tr><th>Entreprise</th><th>NIU</th><th>Contact</th><th>Localisation</th><th>Boîtes</th><th>Abonnés</th><th>Action</th></tr></thead>
        <tbody id="companies-tbody"><tr><td colspan="7" style="text-align:center">Chargement…</td></tr></tbody>
      </table>
    </div>
  </div>`;
}

function renderCompaniesTable(){
  const tbody = document.getElementById('companies-tbody');
  if(!tbody) return;
  if(!DB_COMPANIES.length){
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Aucune entreprise</td></tr>';
    return;
  }
  tbody.innerHTML = DB_COMPANIES.map(e=>`<tr>
    <td><div style="font-weight:600">${e.nom_agence||'—'}</div><div style="font-size:11px;color:var(--text3)">ID: ${e.id}</div></td>
    <td style="font-size:12px">${e.niu||'—'}</td>
    <td style="font-size:12px">${e.addresse_mail||'—'}</td>
    <td style="font-size:12px">${e.lieu_residence||'—'}</td>
    <td><span class="badge badge-info">${e.nb_boites||0} BB</span></td>
    <td>${e.nb_abonnes||0}</td>
    <td><button class="btn-icon" onclick="showCompanyDetailDB(${e.id})">Profil</button></td>
  </tr>`).join('');
}

async function showCompanyDetailDB(id){
  const e = DB_COMPANIES.find(c=>c.id===id);
  if(!e) return;
  // Charger blocs blockchain de cette entreprise
  let bcCount = 0;
  try {
    const r = await fetch(`/api/blockchain/events?per_page=1`);
    const d = await r.json();
    bcCount = d.total;
  } catch(ex){}
  
  const imageUrl = e.logo || e.image || e.cni_file || e.photo;
  const canViewImage = imageUrl && (String(e.created_by||'')===String(localStorage.getItem('currentUserId')) || currentRole==='superadmin');
  
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <div class="modal-header"><div class="modal-title">${e.nom_agence||'Entreprise'}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="grid-3" style="margin-bottom:16px">
            <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Boîtes</div><div class="stat-value">${e.nb_boites||0}</div></div>
            <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Abonnés</div><div class="stat-value">${e.nb_abonnes||0}</div></div>
            <div class="stat-card" style="--accent:var(--purple)" onclick="navigateTo('blockchain');closeModal()" style="cursor:pointer">
              <div class="stat-label"><i class="fas fa-link"></i> Blocs scellés</div>
              <div class="stat-value">${bcCount}</div>
              <div class="stat-sub" style="color:var(--cyan)">↗ Voir</div>
            </div>
          </div>
          <div class="settings-item"><div class="settings-item-label">NIU</div><span>${e.niu||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Email</div><span>${e.addresse_mail||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Localisation</div><span>${e.lieu_residence||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Créé le</div><span>${e.created_at ? new Date(e.created_at).toLocaleDateString('fr-FR') : '—'}</span></div>
          ${canViewImage ? `
          <div class="settings-item">
            <div class="settings-item-label"><i class="fas fa-image"></i> Logo / Document</div>
            <button class="btn-icon" onclick="openImageModal('${escapeHTML(imageUrl)}', 'Logo Entreprise', 'Logo - ${escapeHTML(e.nom_agence||'')}')"><i class="fas fa-eye"></i> Voir</button>
          </div>
          ` : (imageUrl ? `<div class="settings-item"><div class="settings-item-label">Logo / Document</div><span style="color:var(--text3)">Visible uniquement par le créateur</span></div>` : '')}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-secondary" onclick="openEditCompanyModal(${e.id})"><i class="fas fa-edit"></i> Modifier</button>
          <button class="btn-primary" style="width:auto" onclick="navigateTo('blockchain');closeModal()"><i class="fas fa-link"></i> Données Scellées</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

// ══════════════════════════════════════════════════════
//  CLIENTS PAGE (DB)
// ══════════════════════════════════════════════════════
function buildClientsPage(){
  const isOwner = currentRole==='owner'||currentRole==='agence';
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">${isOwner?'Gestion Clients':'Abonnés'}</div>
      <button class="btn-icon" onclick="showModal('addClient')"><i class="fas fa-plus"></i> Nouveau Client</button>
    </div>
    <div class="grid-3" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Total Clients</div><div class="stat-value" id="cl-total">${DB_CLIENTS.length}</div></div>
      <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Abonnements Actifs</div><div class="stat-value" id="cl-actifs">${DB_CLIENTS.filter(c=>c.status==='Actif').length}</div></div>
      <div class="stat-card" style="--accent:var(--amber)"><div class="stat-label">Expirations</div><div class="stat-value" id="cl-expir">${DB_CLIENTS.filter(c=>c.status==='Expiré').length}</div></div>
    </div>
    <div class="card">
      <div class="card-header">
        <span class="card-title">Liste des Clients (BD)</span>
        <div style="position:relative;width:180px">
          <i class="fas fa-search" style="position:absolute;left:8px;top:7px;color:var(--text3);font-size:12px"></i>
          <input type="text" placeholder="Rechercher…" style="padding:5px 10px 5px 26px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;color:var(--text);font-size:12px;outline:none;width:100%" oninput="filterTable('clients-tbody',this.value)">
        </div>
      </div>
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Client</th><th>Login</th><th>Boîte</th><th>Type Abo</th><th>Statut</th><th>Frais</th><th>Action</th></tr></thead>
          <tbody id="clients-tbody"><tr><td colspan="7" style="text-align:center">Chargement…</td></tr></tbody>
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">Ajouter un Client / Abonnement</span></div>
      <div class="form-row">
        <div class="form-field"><label>Nom</label><input type="text" id="new-client-name" placeholder="Nom"></div>
        <div class="form-field"><label>Prénom</label><input type="text" id="new-client-firstname" placeholder="Prénom"></div>
        <div class="form-field"><label>Téléphone</label><input type="text" id="new-client-phone" placeholder="+237…"></div>
        <div class="form-field"><label>Email</label><input type="email" id="new-client-email" placeholder="email@…"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>N° CNI</label><input type="text" id="new-client-n-cni" placeholder="CNI-XXX"></div>
        <div class="form-field"><label>Login</label><input type="text" id="new-client-login" placeholder="login"></div>
        <div class="form-field"><label>Mot de passe</label><input type="password" id="new-client-password" placeholder="••••"></div>
        <div class="form-field"><label>Lieu résidence</label><input type="text" id="new-client-location" placeholder="Ville"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Conteneur</label>
          <select id="container-select" required><option value="">Chargement…</option></select>
        </div>
        <div class="form-field"><label>Type Colis</label><input type="text" id="new-client-cargo-type" placeholder="Électronique…"></div>
        <div class="form-field"><label>Nom Colis</label><input type="text" id="new-client-cargo-name"></div>
        <div class="form-field"><label>Valeur (CFA)</label><input type="number" id="new-client-value" placeholder="0"></div>
        <div class="form-field"><label>Destination</label><input type="text" id="new-client-destination" placeholder="Ville de livraison"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Période</label>
          <select id="new-client-period" onchange="calcSubPrice(this)">
            <option value="transit">Transit</option>
            <option value="month">Ce mois</option>
            <option value="year">Cette année</option>
          </select>
        </div>
        <div class="form-field"><label>Prix Abonnement</label><input type="text" id="sub-price-calc" value="5 000 CFA" readonly style="color:var(--cyan);font-weight:600"></div>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Photo CNI</label>
        <div class="upload-zone" onclick="document.getElementById('client-cni').click()">
          <div class="upload-icon"><i class="fas fa-id-card"></i></div>
          <div class="upload-text">Inventaire</div>
        </div>
        <input type="file" id="client-cni" accept="image/*, application/pdf" style="display:none" onchange="previewFile(this,'client-cni-preview')">
        <div id="client-cni-preview"></div>
      </div>
      <button class="btn-primary" onclick="addNewClient()"><i class="fas fa-check"></i> Créer le Compte Client</button>
    </div>
  </div>`;
}

function renderClientsTable(){
  const tbody = document.getElementById('clients-tbody');
  if(!tbody) return;
  if(!DB_CLIENTS.length){
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Aucun client enregistré</td></tr>';
  } else {
    tbody.innerHTML = DB_CLIENTS.map(c=>`<tr>
      <td><div style="font-weight:600">${c.nom||''} ${c.prenom||''}</div><div style="font-size:11px;color:var(--text3)">${c.address_mail||'—'}</div></td>
      <td style="font-size:12px">${c.login||'—'}</td>
      <td><span class="badge badge-info">${c.id_boite||'—'}</span></td>
      <td><span class="tag">${c.type_a||'—'}</span></td>
      <td><span class="badge badge-${c.status==='Actif'?'ok':c.status==='Expiré'?'danger':'warn'}">${c.status||'—'}</span></td>
      <td style="font-family:var(--mono);font-size:12px">${c.frais ? Number(c.frais).toLocaleString()+' CFA' : '—'}</td>
      <td><button class="btn-icon" onclick="showClientDetailDB('${c.id_cni}')">Profil</button></td>
    </tr>`).join('');
  }

  const totalEl = document.getElementById('cl-total');
  const actifsEl = document.getElementById('cl-actifs');
  const expirEl = document.getElementById('cl-expir');
  if(totalEl) totalEl.textContent = DB_CLIENTS.length;
  if(actifsEl) actifsEl.textContent = DB_CLIENTS.filter(c=>c.status==='Actif').length;
  if(expirEl) expirEl.textContent = DB_CLIENTS.filter(c=>c.status==='Expiré').length;
}

function showClientDetailDB(id){
  const c = DB_CLIENTS.find(x=>x.id_cni===id);
  if(!c) return;
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:600px">
        <div class="modal-header">
          <div class="modal-title" style="color:var(--cyan)">${c.nom||''} ${c.prenom||''}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div class="grid-2" style="margin-bottom:16px">
            <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Statut Abo</div><div class="stat-value">${c.status||'—'}</div></div>
            <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Type</div><div class="stat-value">${c.type_a||'—'}</div></div>
          </div>
          <div class="settings-item"><div class="settings-item-label">CNI</div><span>${c.id_cni||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Login</div><span>${c.login||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Email</div><span>${c.address_mail||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Téléphone</div><span>${c.contact||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Boîtes assignées</div><span class="badge badge-info">${(c.boites && c.boites.length ? c.boites.join(', ') : c.id_boite)||'—'}</span></div>
          ${(() => {
            const imageUrl = c.profile_image || c.cni_file;
            if (!imageUrl) return '';
            const canView = String(c.created_by||'')===String(localStorage.getItem('currentUserId')) || currentRole==='superadmin';
            const linkLabel = canView ? `<a href="${imageUrl}" target="_blank">Voir le document</a>` : `<span style="color:var(--text3)">Document visible uniquement par le créateur</span>`;
            const preview = canView ? (imageUrl.toLowerCase().endsWith('.pdf')
              ? `<div style="margin:16px 0"><embed src="${imageUrl}" type="application/pdf" width="100%" height="320px" style="border:1px solid var(--border);border-radius:12px"></embed></div>`
              : `<div style="margin:16px 0"><img src="${imageUrl}" alt="Profil" style="width:100%;max-height:320px;object-fit:contain;border-radius:12px;border:1px solid var(--border)"></div>`)
              : '';
            return `<div class="settings-item"><div class="settings-item-label">Document Profil</div><span>${linkLabel}</span></div>${preview}`;
          })()}
          <div class="settings-item"><div class="settings-item-label">Frais</div><span>${c.frais ? Number(c.frais).toLocaleString()+' CFA' : '—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Début</div><span>${c.debut_a||'—'}</span></div>
          <div class="settings-item"><div class="settings-item-label">Fin</div><span>${c.fin_a||'—'}</span></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-secondary" onclick="openExtendSubscriptionModal('${c.id_cni}')">Allonger Abonnement</button>
          <button class="btn-secondary" onclick="openIncreaseContainersModal('${c.id_cni}')">Ajouter Conteneurs</button>
          <button class="btn-primary" onclick="openEditClientModal('${c.id_cni}')"><i class="fas fa-edit"></i> Modifier</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

// ══════════════════════════════════════════════════════
//  DRIVERS PAGE (DB)
// ══════════════════════════════════════════════════════
function buildDriversPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Chauffeurs <small id="drv-total">${DB_DRIVERS.length} Enregistrés</small></div>
      <button class="btn-icon" onclick="showModal('addDriver')"><i class="fas fa-plus"></i> Nouveau Chauffeur</button>
    </div>
    <div class="data-table-wrap card">
      <table class="data-table">
        <thead><tr><th>Chauffeur</th><th>CNI</th><th>Login</th><th>Colis</th><th>Transport</th><th>Actions</th></tr></thead>
        <tbody id="drivers-tbody"><tr><td colspan="6" style="text-align:center">Chargement…</td></tr></tbody>
      </table>
    </div>
  </div>`;
}

function renderDriversTable(){
  const tbody = document.getElementById('drivers-tbody');
  if(!tbody) return;
  if(!DB_DRIVERS.length){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3)">Aucun chauffeur</td></tr>';
  } else {
    tbody.innerHTML = DB_DRIVERS.map(d=>`<tr>
      <td><div style="font-weight:600">${d.nom_chauffeurs || (d.nom ? `${d.nom} ${d.prenom||''}`.trim() : '—')}</div></td>
      <td style="font-size:12px">${d.id_cni||'—'}</td>
      <td style="font-size:12px">${d.login||'—'}</td>
      <td style="font-size:12px">${(typeof d.boites === 'string' && d.boites.length) ? d.boites : (Array.isArray(d.boites) && d.boites.length ? d.boites.join(', ') : (d.id_boite || 'Aucun'))}</td>
      <td style="font-size:12px">${d.blocked ? '<span class="badge badge-danger">Bloqué</span>' : (d.moyen_transport||'—')}</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn-icon" onclick="openDriverProfileModal('${d.id_cni}')"><i class="fas fa-user"></i></button>
          <button class="btn-icon" onclick="openDriverMessageModal('${d.id_cni}')"><i class="fas fa-envelope"></i></button>
          <button class="btn-icon" onclick="openDriverManageModal('${d.id_cni}')"><i class="fas fa-cogs"></i></button>
          <button class="btn-icon" onclick="navigateTo('containers')">Détails</button>
        </div>
      </td>
    </tr>`).join('');
  }

  const totalEl = document.getElementById('drv-total');
  if(totalEl) totalEl.textContent = DB_DRIVERS.length + ' Enregistrés';
}

// ══════════════════════════════════════════════════════
//  STATS PAGE
// ══════════════════════════════════════════════════════
function buildStatsPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Statistiques & Analytiques <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px">
        <select id="stats-boite-select" onchange="loadDynamicStats(document.getElementById('stats-period-select').value)"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Toutes les boîtes</option>
        </select>
        <select id="stats-period-select" onchange="loadDynamicStats(this.value)"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="24h">24 dernières heures</option>
          <option value="7d" selected>7 derniers jours</option>
          <option value="30d">30 derniers jours</option>
          <option value="3m">3 derniers mois</option>
          <option value="all">Tous</option>
        </select>
        <button class="export-btn" onclick="openAIAssistant()"><i class="fas fa-robot"></i> Rapport IA</button>
      </div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Temp. Moy</div><div class="stat-value" id="dyn-stat-temp">--°C</div><div class="stat-sub" id="dyn-sub-temp">Chargement…</div></div>
      <div class="stat-card" style="--accent:var(--amber)"><div class="stat-label">Alertes</div><div class="stat-value" id="dyn-stat-alerts">--</div><div class="stat-sub" id="dyn-sub-alerts">Chargement…</div></div>
      <div class="stat-card" style="--accent:var(--red)"><div class="stat-label">Chocs</div><div class="stat-value" id="dyn-stat-shocks">--</div><div class="stat-sub" id="dyn-sub-shocks">Chargement…</div></div>
      <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Fiabilité</div><div class="stat-value" id="dyn-stat-fiability">--%</div><div class="stat-sub" id="dyn-sub-fiability">Chargement…</div></div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card"><div class="card-header"><span class="card-title">Température</span><span class="badge badge-info"><i class="fas fa-circle" style="font-size:8px;color:var(--green)"></i> Live BD</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-temp"></canvas></div></div>
      <div class="card"><div class="card-header"><span class="card-title">Humidité</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-hum"></canvas></div></div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card"><div class="card-header"><span class="card-title">Chocs & Vibrations</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-shock"></canvas></div></div>
      <div class="card"><div class="card-header"><span class="card-title">Pression Atmosphérique</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-press"></canvas></div></div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card"><div class="card-header"><span class="card-title">Vitesse</span></div>
        <div class="chart-wrap" style="height:200px"><canvas id="chart-speed"></canvas></div></div>
      <div class="card"><div class="card-header"><span class="card-title">Répartition Alertes</span></div>
        <div class="chart-wrap" style="height:200px"><canvas id="chart-subs"></canvas></div></div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Abonnements actifs mensuels</span>
        <button class="export-btn" onclick="showToast('Export CSV','info')"><i class="fas fa-file-csv"></i> CSV</button></div>
      <div class="chart-wrap" style="height:180px"><canvas id="chart-revenue"></canvas></div>
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════
//  STATS PAGE (Sécurisé par rôle)
// ══════════════════════════════════════════════════════
async function loadDynamicStats(period='7d'){
  const boite = document.getElementById('stats-boite-select')?.value || '';
  let url = `/api/stats?period=${period}`;
  if(boite) url += `&boite=${boite}`;
  
  try {
    // REMPLACEMENT : secureApiFetch au lieu de fetch
    const res  = await secureApiFetch(url);
    const data = await res.json();
    
    if(!res.ok || data.status !== 'success') {
      ['dyn-stat-temp','dyn-stat-alerts','dyn-stat-shocks','dyn-stat-fiability'].forEach(id=>{
        const el = document.getElementById(id);
        if(el) el.textContent = '—';
      });
      return;
    }
    
    const kpi = data.kpi;
    const labels = {'24h':'Sur 24h','7d':'Sur 7 jours','30d':'Ce mois','3m':'Ce trimestre','all':'Depuis toujours'};
    const lbl = labels[period] || period;
    
    document.getElementById('dyn-stat-temp').textContent      = kpi.avg_temp+'°C';
    document.getElementById('dyn-stat-alerts').textContent    = kpi.total_alertes;
    document.getElementById('dyn-stat-shocks').textContent    = kpi.total_shocks;
    document.getElementById('dyn-stat-fiability').textContent = kpi.fiabilite+'%';
    
    ['temp','alerts','shocks','fiability'].forEach(k=>{
      const el = document.getElementById(`dyn-sub-${k}`);
      if(el) el.textContent = lbl;
    });
    
    const cd = data.charts;
    const updateChart = (id, labels, data) => {
      if(charts[id]){ charts[id].data.labels=labels; charts[id].data.datasets[0].data=data; charts[id].update(); }
    };
    updateChart('chart-temp',  cd.labels, cd.temp);
    updateChart('chart-hum',   cd.labels, cd.hum);
    updateChart('chart-press', cd.labels, cd.press);
    updateChart('chart-speed', cd.labels, cd.speed);
    updateChart('chart-shock', cd.labels, cd.shocks);
    if(charts['chart-subs']){ charts['chart-subs'].data.datasets[0].data = cd.alerts_dist; charts['chart-subs'].update(); }
    if(charts['chart-revenue'] && cd.abonnements){
      charts['chart-revenue'].data.labels = cd.abonnements.labels || [];
      charts['chart-revenue'].data.datasets[0].data = cd.abonnements.data || [];
      charts['chart-revenue'].update();
    }
  } catch(e){
      console.warn('Accès aux statistiques restreint ou erreur réseau.', e);
      ['dyn-stat-temp','dyn-stat-alerts','dyn-stat-shocks','dyn-stat-fiability'].forEach(id=>{
        const el = document.getElementById(id);
        if(el) el.textContent = '—';
      });
  }
}

// Sécurisation de la liste déroulante des boîtes
async function populateStatsBoiteSelect(){
  const sel = document.getElementById('stats-boite-select');
  if(!sel) return;
  try {
    // REMPLACEMENT : secureApiFetch récupère uniquement les boîtes autorisées pour l'utilisateur
    const res  = await secureApiFetch('/api/containers/all');
    const data = await res.json();
    const ids = Array.from(new Set(data.filter(c=>c.id_boite).map(c=>String(c.id_boite).trim()).filter(Boolean)));
    ids.sort((a,b)=>a.localeCompare(b, undefined, {numeric:true, sensitivity:'base'}));
    sel.innerHTML = '<option value="">Toutes les boîtes</option>' +
      ids.map(id=>`<option value="${id}">${id}</option>`).join('');
  } catch(e){ console.warn('populateStatsBoiteSelect', e); }
}

// ══════════════════════════════════════════════════════
//  EVENTS PAGE
// ══════════════════════════════════════════════════════
function buildEventsPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Événements & Alertes</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <select id="evt-severity-filter" onchange="refreshEventTable()"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Tous les niveaux</option>
          <option value="alert">Alertes seulement</option>
          <option value="normal">Normaux seulement</option>
        </select>
        <select id="evt-period-filter" onchange="refreshEventTable()"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Période</option>
          <option value="5h">5 dernières heures</option>
          <option value="24h">24 dernières heures</option>
          <option value="7d" selected>7 derniers jours</option>
          <option value="30d">30 derniers jours</option>
        </select>
        <select id="container-select" 
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none"
          onchange="refreshEventTable()">
          <option value="">Tous conteneurs</option>
        </select>
        <button class="btn-icon" onclick="refreshEventTable()"><i class="fas fa-sync"></i></button>
        <button class="export-btn" onclick="openAIAssistant()"><i class="fas fa-robot"></i> Rapport</button>
      </div>
    </div>
    <div class="grid-3" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--red)"><div class="stat-label">Alertes BD</div><div class="stat-value" id="evt-danger">--</div></div>
      <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Scan Normaux</div><div class="stat-value" id="evt-normal">--</div></div>
      <div class="stat-card" style="--accent:var(--amber)"><div class="stat-label">Total Événements</div><div class="stat-value" id="evt-total">--</div></div>
    </div>
    <div class="card">
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Heure</th><th>Boîte</th><th>Type</th><th>Sévérité</th><th>Message / Capteurs</th><th>Audio</th><th>Action</th></tr></thead>
          <tbody id="events-tbody"><tr><td colspan="7" style="text-align:center">Chargement…</td></tr></tbody>
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">Configuration Seuils d'Alerte (BD)</span></div>
      <div class="form-row">
        <div class="form-field"><label>Conteneur cible</label>
          <select id="threshold-container-select" onchange="loadThresholds(this.value)">
            <option value="">Sélectionner…</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Température Max (°C)</label><input type="number" id="t-temp" value="32"></div>
        <div class="form-field"><label>Humidité Max (%)</label><input type="number" id="t-hum" value="75"></div>
        <div class="form-field"><label>Choc Max (G)</label><input type="number" id="t-choc" value="5"></div>
        <div class="form-field"><label>Pression Min (hPa)</label><input type="number" id="t-press" value="995"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Vitesse Max (km/h)</label><input type="number" id="t-vit" value="90"></div>
        <div class="form-field"><label>Angle Max (°)</label><input type="number" id="t-angle" value="30"></div>
        <div class="form-field"><label>Vent Ref (km/h)</label><input type="number" id="t-vent" value="60"></div>
        <div class="form-field"><label>Notification</label>
          <select><option>SMS + Email + App</option><option>App seulement</option><option>Email seulement</option></select>
        </div>
      </div>
      <button class="btn-primary" onclick="saveThresholds()"><i class="fas fa-save"></i> Sauvegarder les Seuils (BD)</button>
    </div>
  </div>`;
}

async function refreshEventTable(){
  const severity = document.getElementById('evt-severity-filter')?.value || '';
  const period   = document.getElementById('evt-period-filter')?.value || '';
  const container = document.getElementById('container-select')?.value || '';
  let url = '/api/events?limit=100';
  if (period) url += `&period=${encodeURIComponent(period)}`;
  if (severity) url += `&severity=${severity}`;
  if (container) url += `&container=${container}`;
  try {
    const res = await secureApiFetch(url); // Modifié
    const events = await res.json();
    const tbody  = document.getElementById('events-tbody');
    if(!tbody) return;
    if (!res.ok || !Array.isArray(events)) {
      console.error('refreshEventTable invalid response', res.status, events);
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Impossible de charger les événements</td></tr>';
      return;
    }
    DB_EVENTS = events;
    const alerts = events.filter(e=>e.notif && e.notif!=='[]');
    const norms  = events.filter(e=>!e.notif || e.notif==='[]');
    const setEl  = (id,v)=>{ const el=document.getElementById(id); if(el) el.textContent=v; };
    setEl('evt-danger', alerts.length);
    setEl('evt-normal', norms.length);
    setEl('evt-total',  events.length);
    if(!events.length){
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Aucun événement</td></tr>';
      return;
    }

    tbody.innerHTML = events.map(e=>{
      const isAlert = e.notif && String(e.notif).trim() !== '[]';
      const safeNotif = typeof e.notif === 'string' ? e.notif : null;
      let msgs = [];
      if (safeNotif) {
        try { msgs = JSON.parse(safeNotif) || []; } catch (ex) { msgs = []; }
      }
      const severityValue = isAlert ? 'danger' : 'ok';
      const typeTag = isAlert ? 'Alerte' : 'Normal';
      const message = msgs.length ? msgs.join(' | ') : (e.log_action || (isAlert ? 'Alerte critique' : 'Scan régulier'));
      const audio = e.media_1_url
        ? `<audio controls src="${e.media_1_url}" style="height:24px;width:110px"></audio>`
        : '<span style="color:var(--text3);font-size:11px">—</span>';
      const sensorStr = `T:${e.temperature ?? '—'}°C H:${e.humidite ?? '—'}% V:${e.vitesse ?? '—'} km/h G:${e.chocs ?? '—'}`;
      const eventDate = e.horodatage ? new Date(e.horodatage) : null;
      const formattedDate = eventDate && !Number.isNaN(eventDate.getTime())
        ? eventDate.toLocaleString('fr-FR')
        : '—';
      return `<tr>
        <td style="font-family:var(--mono);font-size:11px">${formattedDate}</td>
        <td><span class="badge badge-info">${escapeHTML(e.id_boite ?? '—')}</span></td>
        <td><span class="tag">${typeTag}</span></td>
        <td><span class="badge badge-${severityValue}">${severityValue.toUpperCase()}</span></td>
        <td style="font-size:11px;max-width:220px">
          <div>${escapeHTML(String(message)).substring(0,60)}${String(message).length>60?'…':''}</div>
          <div style="color:var(--text3)">${escapeHTML(sensorStr)}</div>
        </td>
        <td>${audio}</td>
        <td><button class="btn-icon" onclick="showContainerDetailDB('${escapeHTML(e.id_boite || e.id || '')}')"><i class="fas fa-box"></i> Ouvrir</button></td>
      </tr>`;
    }).join('');
  } catch(e){
    console.error('refreshEventTable', e);
    const tbody = document.getElementById('events-tbody');
    if(tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Erreur de chargement des événements</td></tr>';
  }
}

let liveEventInterval = null;
function startLiveMonitoring(){
  if(liveEventInterval) clearInterval(liveEventInterval);
  liveEventInterval = setInterval(refreshEventTable, 15000);
}

// ══════════════════════════════════════════════════════
//  BLOCKCHAIN PAGE
// ══════════════════════════════════════════════════════
function buildBlockchainPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title"><i class="fas fa-link" style="color:var(--cyan)"></i> Données Scellées <small>Blockchain ARGOS</small></div>
      <div style="display:flex;gap:8px">
        <button class="btn-icon" onclick="verifyChain()"><i class="fas fa-shield-alt"></i> Vérifier Intégrité</button>
        <button class="btn-icon" onclick="loadBlockchainData()"><i class="fas fa-sync"></i> Actualiser</button>
      </div>
    </div>
    <div class="alert" style="background:rgba(0,212,255,.08);border:1px solid var(--cyan);border-radius:var(--radius);padding:12px;margin-bottom:16px;font-size:13px">
      <i class="fas fa-info-circle" style="color:var(--cyan)"></i>
      Chaque événement critique (alertes capteurs, ventes, configurations) est automatiquement scellé avec SHA-256
      dans cette blockchain immuable. Chaque bloc référence le hash du précédent, garantissant l'intégrité totale.
    </div>
    <div id="bc-stats" style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap">
      <span style="color:var(--text3)">Chargement statistiques…</span>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header">
        <span class="card-title">Filtres</span>
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;padding:12px">
        <select id="bc-filter-type" onchange="loadBlockchainData()"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Tous les types</option>
          <option value="ALERTE_CRITIQUE">Alertes Critiques</option>
          <option value="VENTE_ATTRIBUTION">Ventes / Attribution</option>
          <option value="CONFIG_SEUILS">Configuration Seuils</option>
          <option value="GENESIS">Bloc Genèse</option>
        </select>
        <select id="bc-filter-boite" onchange="loadBlockchainData()"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Toutes les boîtes</option>
          ${DB_CONTAINERS.filter(c=>c.id_boite).map(c=>`<option value="${c.id_boite}">${c.id_boite}</option>`).join('')}
        </select>
      </div>
    </div>
    <div class="card">
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Bloc #</th><th>Type Événement</th><th>Boîte</th><th>Horodatage</th><th>Données</th><th>Action</th></tr></thead>
          <tbody id="bc-tbody"><tr><td colspan="6" style="text-align:center">Chargement…</td></tr></tbody>
        </table>
      </div>
    </div>
    <div id="bc-pagination" style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"></div>
  </div>`;
}

// ══════════════════════════════════════════════════════
//  BLOG PAGE
// ══════════════════════════════════════════════════════
function buildBlogPage(){
  // On lance le chargement des publications en tâche de fond
  setTimeout(loadPublications, 100);

  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Publications & Annonces</div>
      <button class="btn-icon" onclick="document.getElementById('form-pub').scrollIntoView({behavior:'smooth'})">
        <i class="fas fa-plus"></i> Nouvelle Publication
      </button>
    </div>
    
    <div class="grid-2" style="margin-bottom:16px" id="blog-posts-list">
       <div style="grid-column:1/-1;text-align:center;padding:20px;color:var(--text3)">
          <i class="fas fa-spinner fa-spin"></i> Chargement des publications...
       </div>
    </div>

    <div class="card" id="form-pub">
      <div class="card-header"><span class="card-title">Rédiger une Publication (Multi-Canal)</span></div>
      
      <div class="alert alert-info" style="margin-bottom:16px; font-size:12px;">
         <i class="fas fa-info-circle"></i> La publication sera sauvegardée et envoyée aux utilisateurs concernés par Email, WhatsApp et Notification In-App.
      </div>

      <div class="form-row">
        <div class="form-field"><label>Titre</label><input type="text" placeholder="Titre de la publication" id="blog-title"></div>
        <div class="form-field"><label>Niveau</label>
          <select id="blog-level">
            <option value="Information">Information (Bleu)</option>
            <option value="Avertissement">Avertissement (Orange)</option>
            <option value="Urgent">Urgent (Rouge)</option>
          </select>
        </div>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Contenu du message</label>
        <textarea rows="4" placeholder="Tapez votre annonce ici..." id="blog-content" style="width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:10px;color:var(--text);resize:vertical"></textarea>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Destinataires cibles</label>
        <select id="blog-target">
          <option value="Tous les utilisateurs">Tous les utilisateurs</option>
          <option value="Propriétaires BB seulement">Propriétaires BB et Clients</option>
          <option value="Chauffeurs seulement">Chauffeurs seulement</option>
        </select>
      </div>
      <button class="btn-primary" onclick="submitPublication()">
        <i class="fas fa-paper-plane"></i> Publier & Notifier
      </button>
    </div>
  </div>`;
}

// Fonction pour récupérer et afficher les publications depuis la BD
async function loadPublications() {
    const listEl = document.getElementById('blog-posts-list');
    if(!listEl) return;
    
    try {
        const res = await fetch('/api/publications');
        const data = await res.json();
        
        if(!data.length) {
            listEl.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text3)">Aucune publication pour le moment.</div>';
            return;
        }

        listEl.innerHTML = data.map(pub => {
            // Choix des couleurs et icones selon le niveau
            let color = "var(--cyan)";
            let icon = "fa-info-circle";
            let badge = "badge-info";
            
            if(pub.niveau === "Urgent") { color = "var(--red)"; icon = "fa-exclamation-circle"; badge = "badge-danger"; }
            else if(pub.niveau === "Avertissement") { color = "var(--amber)"; icon = "fa-exclamation-triangle"; badge = "badge-warn"; }

            return `
            <div class="card" style="border-left:3px solid ${color}">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <span class="badge ${badge}"><i class="fas ${icon}"></i> ${pub.niveau.toUpperCase()}</span>
                    <span style="font-size:11px;color:var(--text3)"><i class="fas fa-clock"></i> ${new Date(pub.date_pub).toLocaleString('fr-FR')}</span>
                </div>
                <div style="font-size:15px;font-weight:600;margin-bottom:6px">${pub.titre}</div>
                <p style="font-size:13px;color:var(--text2);white-space:pre-wrap;">${pub.contenu}</p>
                <div style="margin-top:10px;font-size:10px;color:var(--text3);border-top:1px solid var(--border);padding-top:6px;">
                    Cible: ${pub.cible}
                </div>
            </div>`;
        }).join('');
    } catch(e) {
        listEl.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--red)">Erreur de chargement.</div>';
    }
}


// Fonction pour envoyer le formulaire de publication
async function submitPublication() {
    const titre = document.getElementById('blog-title').value.trim();
    const niveau = document.getElementById('blog-level').value;
    const contenu = document.getElementById('blog-content').value.trim();
    const cible = document.getElementById('blog-target').value;

    if(!titre || !contenu) {
        showToast("Veuillez remplir le titre et le contenu.", "warn");
        return;
    }

    showToast("Envoi en cours...", "info");

    try {
        const res = await fetch('/api/publications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titre, niveau, contenu, cible })
        });
        
        if(res.ok) {
            showToast("Publication envoyée avec succès aux utilisateurs !", "success");
            // Réinitialiser le formulaire
            document.getElementById('blog-title').value = '';
            document.getElementById('blog-content').value = '';
            // Recharger la liste
            loadPublications();
        } else {
            showToast("Erreur lors de la publication.", "danger");
        }
    } catch(e) {
        showToast("Erreur réseau.", "danger");
    }
}


// ══════════════════════════════════════════════════════
//  SETTINGS PAGE
// ══════════════════════════════════════════════════════
function buildSettingsPage(){
  const isAdmin = currentRole==='superadmin';
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Paramètres <small>Configuration</small></div>
      <button class="btn-primary" style="width:auto;padding:8px 20px" onclick="saveSettings()"><i class="fas fa-save"></i> Sauvegarder</button>
    </div>
    <div class="grid-2">
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-user"></i> Profil Utilisateur</div>
          <div class="form-field" style="margin-bottom:12px"><label>Rôle</label><input type="text" value="${currentRole.toUpperCase()}" readonly style="opacity:.6"></div>
          <div class="form-field" style="margin-bottom:12px"><label>ID Utilisateur</label><input type="text" value="${currentUserId||'—'}" readonly style="opacity:.6"></div>
          <div class="form-field" style="margin-bottom:12px"><label>Langue Interface</label>
            <select id="setting-lang"><option value="fr" ${currentLang==='fr'?'selected':''}>Français</option><option value="en" ${currentLang==='en'?'selected':''}>English</option></select>
          </div>
          <div class="form-field" style="margin-bottom:12px"><label>Nom affiché</label><input type="text" id="setting-username" value="${currentUserName||''}" placeholder="Nom d'utilisateur"></div>
          <div class="settings-item">
            <div class="settings-item-info"><div class="settings-item-label">Notifications générales</div><div class="settings-item-desc">Activer les alertes dans l'application</div></div>
            <label class="toggle-switch"><input type="checkbox" id="setting-notifs" ${notifsEnabled ? 'checked' : ''}><span class="toggle-slider"></span></label>
          </div>
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-bell"></i> Notifications</div>
          ${[['Alertes SMS','Recevoir les alertes par SMS',true],
             ['Alertes Email','Notifications par email',true],
             ['Alertes WhatsApp','Notifications WhatsApp',false],
             ['Rapport Quotidien','Rapport PDF automatique',true]].map(([l,d,c])=>`
          <div class="settings-item">
            <div class="settings-item-info"><div class="settings-item-label">${l}</div><div class="settings-item-desc">${d}</div></div>
            <label class="toggle-switch"><input type="checkbox" ${c?'checked':''}><span class="toggle-slider"></span></label>
          </div>`).join('')}
        </div>
        <div class="card">
          <div class="settings-title"><i class="fas fa-shield-alt"></i> Sécurité</div>
          <div class="form-field" style="margin-bottom:12px"><label>Mot de Passe Actuel</label><input type="password" id="pw-current" placeholder="••••••••"></div>
          <div class="form-field" style="margin-bottom:12px"><label>Nouveau Mot de Passe</label><input type="password" id="pw-new" placeholder="••••••••"></div>
          <div class="form-field" style="margin-bottom:16px"><label>Confirmer</label><input type="password" id="pw-confirm" placeholder="••••••••"></div>
          <button class="btn-secondary" onclick="changePassword()">Changer le Mot de Passe</button>
        </div>
      </div>
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-desktop"></i> Monitoring</div>
          <div class="settings-item">
            <div class="settings-item-info"><div class="settings-item-label">Fréquence d'actualisation</div></div>
            <select id="refresh-rate" onchange="changeRefreshRate(this.value)"
            style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:4px 8px;color:var(--text);font-size:12px;outline:none">
                <option value="5" ${refreshSec === 5 ? 'selected' : ''}>5 secondes</option>
                <option value="10" ${refreshSec === 10 ? 'selected' : ''}>10 secondes</option>
                <option value="30" ${refreshSec === 30 ? 'selected' : ''}>30 secondes</option>
                <option value="60" ${refreshSec === 60 ? 'selected' : ''}>1 minute</option>
            </select>
          </div>
          ${[['Historique GPS','Afficher les traces GPS',true],
             ['Mode Hors Ligne','Cache données localement',false],
             ['Enregistrement Audio','Enregistrer sons détectés',true],
             ['Rapport Automatique','Génération à chaque incident',true]].map(([l,d,c])=>`
          <div class="settings-item">
            <div class="settings-item-info"><div class="settings-item-label">${l}</div><div class="settings-item-desc">${d}</div></div>
            <label class="toggle-switch"><input type="checkbox" ${c?'checked':''}><span class="toggle-slider"></span></label>
          </div>`).join('')}
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-map"></i> Carte & Affichage</div>
          <div class="form-field" style="margin-bottom:12px">
            <label>Fond de Carte par défaut</label>
            <select id="map-layer-select" onchange="mapLayerIdx=this.selectedIndex">
              ${MAP_LAYERS.map((l,i)=>`<option value="${i}">${l.name}</option>`).join('')}
            </select>
          </div>
          <div class="form-field" style="margin-bottom:12px">
            <label>Unité Température</label>
            <select><option>Celsius (°C)</option><option>Fahrenheit (°F)</option></select>
          </div>
          ${[['Animations Carte','',true],['Marqueurs Pulsants','',true]].map(([l,d,c])=>`
          <div class="settings-item">
            <div class="settings-item-info"><div class="settings-item-label">${l}</div></div>
            <label class="toggle-switch"><input type="checkbox" ${c?'checked':''}><span class="toggle-slider"></span></label>
          </div>`).join('')}
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-palette"></i> Apparence</div>
          <div class="settings-item">
            <div class="settings-item-info"><div class="settings-item-label">Mode Sombre</div><div class="settings-item-desc">Basculer thème clair / sombre</div></div>
            <label class="toggle-switch"><input type="checkbox" id="theme-toggle" onchange="toggleTheme()"><span class="toggle-slider"></span></label>
          </div>
        </div>
        ${(currentRole==='superadmin'||currentRole==='owner') ? `
        <div class="card" style="margin-bottom:16px;border:1px solid var(--cyan)">
          <div class="settings-title"><i class="fas fa-link" style="color:var(--cyan)"></i> Données Scellées (Blockchain)</div>
          <p style="font-size:12px;color:var(--text2);margin-bottom:12px">Accédez à l'historique immuable de tous les événements critiques scellés cryptographiquement.</p>
          <button class="btn-primary" onclick="navigateTo('blockchain')"><i class="fas fa-link"></i> Voir les Données Scellées</button>
          <button class="btn-icon" style="margin-left:8px" onclick="verifyChain()"><i class="fas fa-shield-alt"></i> Vérifier Intégrité</button>
        </div>` : ''}
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-robot"></i> Assistant IA</div>
          <p style="font-size:12px;color:var(--text2);margin-bottom:12px">Utilisez l'assistant pour générer des rapports, résumer des incidents ou obtenir des recommandations.</p>
          <button class="btn-primary" onclick="openAIAssistant()"><i class="fas fa-robot"></i> Ouvrir l'IA</button>
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-info-circle"></i> À Propos</div>
          <div style="font-size:13px;color:var(--text2);line-height:1.8">
            <div>Plateforme ARGOS v3.0.0</div>
            <div style="color:var(--text3)">Surveillance Boîtes Noires & Conteneurs</div>
            <div style="color:var(--text3)">Blockchain SHA-256 intégrée • TimescaleDB • PostgreSQL</div>
            <div style="margin-top:8px">© 2026 Équipe ARGOS</div>
          </div>
          <div style="margin-top:12px;display:flex;gap:8px">
            <button class="btn-icon" onclick="doLogout()"><i class="fas fa-sign-out-alt"></i> Déconnexion</button>
            <button class="btn-icon" onclick="openSupportChat()"><i class="fas fa-headset"></i> Support WhatsApp</button>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

// save seting 

// ── LOGIQUE DE SAUVEGARDE DES PARAMÈTRES ────────────────
function saveSettings() {
    // 1. Récupération des valeurs du formulaire
    const newLang = document.getElementById('setting-lang').value;
    const newName = document.getElementById('setting-username').value.trim() || 'Utilisateur';
    const newNotifs = document.getElementById('setting-notifs').checked;

    // 2. Mise à jour des variables globales
    currentLang = newLang;
    currentUserName = newName;
    notifsEnabled = newNotifs;

    // 3. Sauvegarde dans le LocalStorage (pour que ça reste après F5)
    localStorage.setItem('argos_lang', currentLang);
    localStorage.setItem('currentUserName', currentUserName);
    localStorage.setItem('argos_notifs', notifsEnabled);

    // 4. Mise à jour visuelle immédiate de la Sidebar
    const nameEl = document.getElementById('sidebar-user-name');
    if (nameEl) nameEl.textContent = currentUserName;

    // 5. Recharger le menu latéral et la page courante avec la nouvelle langue
    buildNav();
    if (currentPage) renderPage(currentPage);

    // On force un toast "Success" même si les notifs sont coupées pour confirmer la sauvegarde
    const tempNotif = notifsEnabled; 
    notifsEnabled = true;
    showToast(currentLang === 'fr' ? 'Paramètres sauvegardés' : 'Settings saved', 'success');
    notifsEnabled = tempNotif;
}

// Fonction pour reconstruire le menu (traduite)
function buildNavigationMenu() {
    const navList = document.getElementById('nav-list');
    if (!navList || !NAV[currentRole]) return;

    // On utilise t() pour traduire les labels si possible, sinon on garde l'original
    navList.innerHTML = NAV[currentRole].map(item => {
        const translatedLabel = (I18N[currentLang] && I18N[currentLang][`nav_${item.id}`]) ? I18N[currentLang][`nav_${item.id}`] : item.label;
        return `
            <div class="nav-item" onclick="navigateTo('${item.id}')">
                <i class="${item.icon}"></i> <span>${translatedLabel}</span>
            </div>
        `;
    }).join('');
}

function changeRefreshRate(v){
  refreshSec = parseInt(v) || 10;
  startAutoRefresh();
  showToast(`Actualisation toutes les ${v} secondes`, 'info');
}

function changePassword(){
  const c = document.getElementById('pw-current')?.value;
  const n = document.getElementById('pw-new')?.value;
  const f = document.getElementById('pw-confirm')?.value;
  if(!c||!n||!f){ showToast('Remplissez tous les champs','warn'); return; }
  if(n !== f){ showToast('Les mots de passe ne correspondent pas','warn'); return; }
  showToast('Mot de passe mis à jour (simulation)','success');
}

function openSupportChat(){
  const phone = '237650000000';
  const text = encodeURIComponent('Bonjour ARGOS, je souhaite une assistance technique.');
  window.open(`https://wa.me/${phone}?text=${text}`,'_blank');
  showToast('Ouverture du support WhatsApp…','info');
}

function doLogout(){
  if (typeof notifsEnabled !== 'undefined' && notifsEnabled) {
      showToast('Déconnexion…', 'info');
  }
  showToast('Déconnexion…','info');
  localStorage.removeItem('currentRole');
  localStorage.removeItem('currentUserId');
  localStorage.removeItem('isLoggedIn');
  setTimeout(()=>{
    document.getElementById('app').style.display='none';
    document.getElementById('login-screen').style.display='flex';
    currentRole = 'superadmin';
    currentPage = '';
  }, 1000);
}

// ══════════════════════════════════════════════════════
//  MAP INIT & CONTROLS
// ══════════════════════════════════════════════════════
let tileLayerRef = null;

function initMap(mapId, role){
  const el = document.getElementById(mapId);
  if(!el) return;
  if(maps[mapId]){ maps[mapId].remove(); delete maps[mapId]; }
  const map = L.map(mapId, {center:[5.0, 11.0], zoom: role==='client'?9:6, zoomControl:false});
  maps[mapId] = map;
  L.control.zoom({position:'bottomright'}).addTo(map);
  tileLayerRef = L.tileLayer(MAP_LAYERS[mapLayerIdx].url, {attribution:'© ARGOS', maxZoom:19}).addTo(map);
  placeDBMarkersOnMap(map, role);
  if(role === 'sell'){
    map.on('click', e=>{
      selectedSaleCoords = e.latlng;
      const coordEl = document.getElementById('map-sale-coords');
      if(coordEl) coordEl.innerHTML = `<i class="fas fa-map-marker-alt"></i> Lat: ${e.latlng.lat.toFixed(6)}, Lng: ${e.latlng.lng.toFixed(6)}`;
      map.eachLayer(l=>{ if(l._clickMarker) map.removeLayer(l); });
      const m = L.marker(e.latlng).addTo(map); m._clickMarker = true;
    });
  }
}

function placeDBMarkersOnMap(map, role){
  const containers = role==='client' ? DB_CONTAINERS.slice(0,1) : DB_CONTAINERS;
  containers.forEach(c=>{
    if(!c.lat || !c.lon) return;
    if(c.status==='off' && role!=='superadmin') return;
    const color = c.status==='ok'?'#00e676':c.status==='warning'?'#ffab00':c.status==='danger'?'#ff4444':'#5a7290';
    const markerHtml = `<div class="marker-pulse">
      <div class="marker-outer" style="border-color:${color}"></div>
      <div class="marker-inner" style="background:${color};box-shadow:0 0 8px ${color}"></div>
    </div>`;
    const icon = L.divIcon({html:markerHtml, className:'', iconSize:[24,24], iconAnchor:[12,12]});
    const marker = L.marker([c.lat, c.lon], {icon}).addTo(map);
    marker._containerId = c.id_boite || c.id;
    const alertsHtml = c.alerts && c.alerts.length ? c.alerts.slice(0,2).map(a=>`<div style="color:#ff4444;font-size:10px">⚠ ${a.substring(0,35)}</div>`).join('') : '<div style="color:#00e676;font-size:10px">✓ Nominal</div>';
    marker.bindPopup(`
      <div style="font-family:'Space Grotesk',sans-serif;min-width:200px">
        <div style="font-family:monospace;font-size:15px;color:#00d4ff;margin-bottom:6px">${c.id_boite||c.id}</div>
        <div style="font-size:12px;color:#ccc">${c.type_conteneurs||'—'}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:8px">
          <div style="text-align:center;background:rgba(0,0,0,.3);padding:5px;border-radius:4px">
            <div style="font-size:15px;font-weight:700;color:${c.temp>32?'#ff4444':c.temp>28?'#ffab00':'#00e676'}">${c.temp??'—'}°C</div>
            <div style="font-size:9px;color:#8fa3bc">TEMP</div>
          </div>
          <div style="text-align:center;background:rgba(0,0,0,.3);padding:5px;border-radius:4px">
            <div style="font-size:15px;font-weight:700;color:#00d4ff">${c.speed??0}</div>
            <div style="font-size:9px;color:#8fa3bc">KM/H</div>
          </div>
        </div>
        <div style="margin-top:6px">${alertsHtml}</div>
        <div style="margin-top:6px;font-size:10px;color:#8fa3bc">MàJ: ${c.lastUpdate}</div>
      </div>`);
    if(trailsOn){
      const trail = fetchAndDrawTrail(map, c.id_boite||c.id);
    }
  });
}

async function fetchAndDrawTrail(map, id_boite){
  try {
    const res  = await fetch(`/api/events?container=${id_boite}&limit=50`);
    const evts = await res.json();
    const pts  = evts.filter(e=>e.lat&&e.lon).map(e=>[Number(e.lat),Number(e.lon)]);
    if(pts.length>1){
      const line = L.polyline(pts, {color:'#00d4ff', weight:2, opacity:.5, dashArray:'4,4'}).addTo(map);
      trailLayers.push(line);
    }
  } catch(e){}
}

function refreshMapMarkers(){
  const map = maps['map-main'];
  if(!map) return;
  // Remove old markers
  map.eachLayer(l=>{ if(l instanceof L.Marker && l._containerId) map.removeLayer(l); });
  // Re-place from fresh DB_CONTAINERS
  placeDBMarkersOnMap(map, currentRole);
}

function showAllContainers(){
  const map = maps['map-main'];
  if(!map) return;
  const pts = DB_CONTAINERS.filter(c=>c.lat&&c.lon).map(c=>[c.lat,c.lon]);
  if(pts.length) map.fitBounds(L.latLngBounds(pts).pad(.2));
}

function fitAllMarkers(){ showAllContainers(); }

function toggleMapLayer(){
  const map = maps['map-main'];
  if(!map) return;
  mapLayerIdx = (mapLayerIdx + 1) % MAP_LAYERS.length;
  if(tileLayerRef) map.removeLayer(tileLayerRef);
  tileLayerRef = L.tileLayer(MAP_LAYERS[mapLayerIdx].url, {attribution:'© ARGOS', maxZoom:19}).addTo(map);
  showToast(`Fond de carte: ${MAP_LAYERS[mapLayerIdx].name}`, 'info');
}

function toggleTrails(){
  const map = maps['map-main'];
  if(!map) return;
  trailsOn = !trailsOn;
  if(!trailsOn){
    trailLayers.forEach(l=>map.removeLayer(l));
    trailLayers = [];
    showToast('Traces GPS désactivées','info');
  } else {
    DB_CONTAINERS.forEach(c=>{ if(c.id_boite) fetchAndDrawTrail(map, c.id_boite); });
    showToast('Traces GPS activées','success');
  }
  const btn = document.getElementById('btn-trails');
  if(btn) btn.style.background = trailsOn ? 'var(--cyan)' : '';
}

function toggleHeatmap(){
  const map = maps['map-main'];
  if(!map) return;
  heatmapOn = !heatmapOn;
  showToast(heatmapOn ? 'Heatmap alertes activée' : 'Heatmap désactivée', heatmapOn?'success':'info');
  const btn = document.getElementById('btn-heat');
  if(btn) btn.style.background = heatmapOn ? 'var(--red)' : '';
}

function focusContainerDB(id){
  const c = DB_CONTAINERS.find(x=>(String(x.id_boite)===String(id)||String(x.id)===String(id))&&x.lat&&x.lon);
  if(!c || !maps['map-main']) return;
  maps['map-main'].flyTo([c.lat, c.lon], 13, {animate:true, duration:1});
}

async function fetchOSRMRoute(waypoints, mode='driving'){
  try {
    const coords = waypoints.map(p=>`${p[1]},${p[0]}`).join(';');
    const url    = `https://router.project-osrm.org/route/v1/${mode}/${coords}?overview=full&geometries=geojson`;
    const resp   = await fetch(url);
    const data   = await resp.json();
    if(data.code==='Ok' && data.routes.length>0){
      return data.routes[0].geometry.coordinates.map(c=>[c[1],c[0]]);
    }
  } catch(e){ return waypoints; }
}

// ══════════════════════════════════════════════════════
//  CHARTS
// ══════════════════════════════════════════════════════
function initCharts(page){
  Chart.defaults.color       = '#8fa3bc';
  Chart.defaults.borderColor = 'rgba(30,45,66,.6)';

  function mkChart(id, type, labels, datasets, opts={}){
    const el = document.getElementById(id);
    if(!el) return;
    if(charts[id]) charts[id].destroy();
    charts[id] = new Chart(el, {
      type, data:{labels, datasets},
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:datasets.length>1,labels:{color:'#8fa3bc',boxWidth:12,font:{size:11}}},...(opts.plugins||{})},
        scales:(type==='doughnut'||type==='pie')?{}:{
          x:{grid:{color:'rgba(30,45,66,.5)'},ticks:{font:{size:10},maxTicksLimit:8}},
          y:{grid:{color:'rgba(30,45,66,.5)'},ticks:{font:{size:10}},...(opts.y||{})}
        },
        animation:{duration:600}, ...opts
      }
    });
    return charts[id];
  }

  mkChart('chart-temp',  'line', [], [{label:'Température (°C)', data:[], borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,.08)', borderWidth:2, fill:true, tension:.4, pointRadius:2}]);
  mkChart('chart-hum',   'line', [], [{label:'Humidité (%)',      data:[], borderColor:'#2979ff', backgroundColor:'rgba(41,121,255,.08)',borderWidth:2, fill:true, tension:.4, pointRadius:2}]);
  mkChart('chart-shock', 'bar',  [], [{label:'Chocs (G)',         data:[], backgroundColor:'#ffab00', borderRadius:4}]);
  mkChart('chart-press', 'line', [], [{label:'Pression (hPa)',    data:[], borderColor:'#b44dff', backgroundColor:'rgba(180,77,255,.08)', borderWidth:2, fill:true, tension:.4, pointRadius:2}]);
  mkChart('chart-speed', 'line', [], [{label:'Vitesse (km/h)',    data:[], borderColor:'#00e676', borderWidth:2, fill:false, tension:.4, pointRadius:2}]);
  // Graphique mensuel des abonnements issus de la base.
  mkChart('chart-revenue', 'line', [],
    [{
      label: 'Abonnements actifs créés',
      data: [],
      backgroundColor: 'rgba(0, 212, 255, 0.1)', // Fond bleuté transparent
      borderColor: 'var(--cyan)', 
      borderWidth: 2, 
      fill: true,        // Remplissage sous la courbe
      tension: 0.3,      // Courbe légèrement lissée
      pointBackgroundColor: '#fff',
      pointRadius: 3
    }]
  );
  mkChart('chart-subs', 'doughnut', ['Choc','Temp.','Humidité','Vitesse','Pression'],
    [{data:[], backgroundColor:['#ff4444','#ffab00','#2979ff','#00e676','#b44dff'], borderWidth:0, hoverOffset:6}]);
}


// ══════════════════════════════════════════════════════
//  MODALE PROFIL ENTREPRISE (DESIGN EN BLOCS)
// ══════════════════════════════════════════════════════

function openDashboardEnterpriseProfile(encodedData) {
  const ent = JSON.parse(decodeURIComponent(encodedData));
  const isActive = (ent.statut || 'active').toLowerCase() !== 'inactif';

  // 1. Boutons conditionnels
  let buttonsHtml = `
    <button class="btn-primary" style="width:auto" onclick="promptAddContainer('${ent.id}')">
      <i class="fas fa-plus"></i> Ajouter un conteneur
    </button>
  `;

  if (isActive) {
    buttonsHtml += `
      <button class="btn-secondary" style="width:auto; color:var(--red); border-color:var(--red)" onclick="promptEndContract('${ent.id}')">
        <i class="fas fa-ban"></i> Fin de contrat
      </button>
    `;
  } else {
    buttonsHtml += `
      <button class="btn-secondary" style="width:auto; color:var(--green); border-color:var(--green)" onclick="promptRenewContract('${ent.id}')">
        <i class="fas fa-sync"></i> Renouveller le contrat
      </button>
    `;
  }

  // 2. Formatage des données en "Blocs" (Grille CSS)
  let dataRowsHtml = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:12px; padding: 4px;">';
  for (const [key, value] of Object.entries(ent)) {
    let valStr = value;
    if (typeof value === 'object' && value !== null) valStr = JSON.stringify(value);
    
    // On met en forme la clé (enlever les underscores, majuscules)
    const label = key.replace(/_/g, ' ').toUpperCase();

    dataRowsHtml += `
      <div class="profile-data-block">
        <div style="color:var(--text3); font-size:10px; font-weight:700; margin-bottom:6px; letter-spacing:0.5px;">
          <i class="fas fa-caret-right" style="color:var(--cyan); margin-right:4px;"></i>${label}
        </div>
        <div style="font-size:13px; color:var(--text); word-break:break-all; font-family:var(--font-main); font-weight:500;">
          ${valStr !== null && valStr !== '' ? valStr : '<span style="color:var(--border)">Non renseigné</span>'}
        </div>
      </div>
    `;
  }
  dataRowsHtml += '</div>'; // Fin de la grille

  const imageUrl = ent.profile_image || ent.cni_file || ent.image || ent.document || ent.logo;
  const imageHtml = imageUrl ? `
    <div style="margin-bottom:16px;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <div style="font-size:12px;color:var(--text3);font-weight:600;">Document d'inscription</div>
        <a href="${escapeHTML(imageUrl)}" target="_blank" class="btn-icon" style="padding:8px 12px;">Voir le document</a>
      </div>
      ${imageUrl.toLowerCase().endsWith('.pdf')
        ? `<div style="margin-top:12px"><embed src="${escapeHTML(imageUrl)}" type="application/pdf" width="100%" height="320px" style="border:1px solid var(--border);border-radius:12px"></embed></div>`
        : `<div style="margin-top:12px"><img src="${escapeHTML(imageUrl)}" alt="Document entreprise" style="width:100%;max-height:320px;object-fit:contain;border-radius:12px;border:1px solid var(--border)"></div>`}
    </div>` : '';

  const html = `
    <style>
      .prof-search-wrap { display: flex; align-items: center; background: var(--bg3); border-radius: 20px; padding: 6px; width: 34px; transition: width 0.3s ease; overflow: hidden; cursor: pointer; border: 1px solid var(--border); }
      .prof-search-wrap.expanded { width: 220px; cursor: text; padding: 6px 12px; border-color: var(--cyan); }
      .prof-search-wrap input { border: none; background: transparent; color: #fff; width: 100%; outline: none; font-size:13px; display: none; font-family: var(--font-main); }
      .prof-search-wrap.expanded input { display: block; margin-left: 8px; }
      .modal-body-scroll { max-height: 65vh; overflow-y: auto; padding-right: 8px; }
      .modal-body-scroll::-webkit-scrollbar { width: 6px; }
      .modal-body-scroll::-webkit-scrollbar-thumb { background: var(--border3); border-radius: 10px; }
      .modal-body-scroll::-webkit-scrollbar-thumb:hover { background: var(--text3); }
    </style>
    
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:750px">
        
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-building" style="color:var(--cyan)"></i> Profil : ${ent.nom || 'Entreprise'}</div>
          
          <div class="prof-search-wrap" id="prof-search-box" onclick="this.classList.add('expanded'); document.getElementById('prof-search-input').focus()">
            <i class="fas fa-search" style="color:var(--text3); margin-left:4px;"></i>
            <input type="text" id="prof-search-input" placeholder="Filtrer les blocs..." onkeyup="filterProfileBlocks(this.value)">
          </div>
          
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        
        <div class="modal-body modal-body-scroll" id="profile-rows-container">
          ${imageHtml}
          ${dataRowsHtml}
        </div>
        
        <div class="modal-footer" style="justify-content: flex-start; gap:10px; border-top:1px solid var(--border); padding-top:16px;">
          ${buttonsHtml}
        </div>
        
      </div>
    </div>
  `;
  document.getElementById('modal-root').innerHTML = html;
}

function filterProfileBlocks(query) {
  const q = query.toLowerCase();
  document.querySelectorAll('.profile-data-block').forEach(block => {
    block.style.display = block.innerText.toLowerCase().includes(q) ? 'block' : 'none';
  });
}

// ══════════════════════════════════════════════════════
//  ACTIONS DU PROFIL (AJOUT & FIN CONTRAT AVEC MODALES)
// ══════════════════════════════════════════════════════

function promptAddContainer(entId) {
  const html = `
    <div class="modal-overlay" style="z-index:1100; background:rgba(0,0,0,0.8);" onclick="if(event.target===this) document.getElementById('modal-sub-root').innerHTML=''">
      <div class="modal" style="max-width:550px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-box" style="color:var(--cyan)"></i> Enregistrer un Conteneur</div>
          <button class="modal-close" onclick="document.getElementById('modal-sub-root').innerHTML=''"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          
          <div class="grid-2" style="gap:16px; margin-bottom:16px;">
            <div class="form-field">
              <label>ID Conteneur</label>
              <input type="text" id="new-cont-id" placeholder="Ex: CONT-1029" style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none;">
            </div>
            <div class="form-field">
              <label>Statut</label>
              <select id="new-cont-status" style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none;">
                <option value="ok">OK (Actif)</option>
                <option value="warning">En Alerte</option>
                <option value="danger">Critique</option>
                <option value="off">Hors Ligne</option>
              </select>
            </div>
          </div>
          
          <div class="grid-2" style="gap:16px; margin-bottom:16px;">
            <div class="form-field">
              <label>Type de Conteneur</label>
              <select id="new-cont-type" style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none;">
                <option value="DRY">DRY (Standard)</option>
                <option value="HighCube">High Cube</option>
                <option value="Refrigere">Réfrigéré</option>
                <option value="OpenTop">Open Top</option>
              </select>
            </div>
            <div class="form-field">
              <label>Résistance</label>
              <input type="text" id="new-cont-res" placeholder="Ex: Standard, Renforcée" style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none;">
            </div>
          </div>
          
          <div class="form-field">
            <label>Taille / Périmètre</label>
            <input type="text" id="new-cont-taille" placeholder="Ex: 20 pieds / 14.6m" style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none;">
          </div>

          <div style="font-size:11px; color:var(--text3); margin-top:16px; padding:10px; background:var(--bg4); border-radius:var(--radius); border-left:3px solid var(--cyan);">
            <i class="fas fa-link" style="color:var(--cyan)"></i> Ce conteneur sera rattaché au compte de cette entreprise et une Boîte seras assigner a ce conteneur.
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="document.getElementById('modal-sub-root').innerHTML=''">Annuler</button>
          <button class="btn-primary" onclick="submitNewContainer('${entId}')"><i class="fas fa-save"></i> Enregistrer</button>
        </div>
      </div>
    </div>
  `;
  
  let subRoot = document.getElementById('modal-sub-root');
  if(!subRoot){ subRoot = document.createElement('div'); subRoot.id = 'modal-sub-root'; document.body.appendChild(subRoot); }
  subRoot.innerHTML = html;
}

function submitNewContainer(entId) {
  const cId = document.getElementById('new-cont-id').value;
  if(!cId) { showToast('L\'ID du conteneur est requis', 'warn'); return; }
  
  // Ici vous ferez votre fetch() vers votre route Flask (ex: /api/company/add_container)
  showToast(`Le conteneur ${cId} a bien été rattaché à l'entreprise !`, 'success');
  document.getElementById('modal-sub-root').innerHTML = ''; // Ferme la sous-modale
}

function promptEndContract(entId) {
  const html = `
    <div class="modal-overlay" style="z-index:1100; background:rgba(0,0,0,0.8);" onclick="if(event.target===this) document.getElementById('modal-sub-root').innerHTML=''">
      <div class="modal" style="max-width:450px; border-top: 3px solid var(--red);">
        <div class="modal-header">
          <div class="modal-title" style="color:var(--red)"><i class="fas fa-exclamation-triangle"></i> Fin de contrat</div>
          <button class="modal-close" onclick="document.getElementById('modal-sub-root').innerHTML=''"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <p style="font-size:13px; color:var(--text2); margin-bottom:12px;">Vous êtes sur le point de désactiver ce profil. Veuillez justifier la raison de cette clôture :</p>
          <textarea id="end-contract-reason" rows="4" placeholder="Saisissez la justification détaillée ici..." style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none; resize:none; font-family:var(--font-main);"></textarea>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="document.getElementById('modal-sub-root').innerHTML=''">Annuler</button>
          <button class="btn-primary" style="background:var(--red); border-color:var(--red);" onclick="submitEndContract('${entId}')"><i class="fas fa-check"></i> Confirmer la fin</button>
        </div>
      </div>
    </div>
  `;
  
  let subRoot = document.getElementById('modal-sub-root');
  if(!subRoot){ subRoot = document.createElement('div'); subRoot.id = 'modal-sub-root'; document.body.appendChild(subRoot); }
  subRoot.innerHTML = html;
}

function submitEndContract(entId) {
  const motif = document.getElementById('end-contract-reason').value.trim();
  if(!motif) { showToast('Une justification est requise.', 'warn'); return; }
  
  // Ici vous ferez le fetch() vers /api/company/end_contract
  showToast("Contrat clôturé. Motif enregistré.", "success");
  document.getElementById('modal-sub-root').innerHTML = '';
  closeModal(); // Ferme le profil principal
  loadSADashboardData(); // Met à jour le tableau
}

function promptRenewContract(entId) {
  // Pour rester cohérent, on fait pareil pour le renouvellement
  const html = `
    <div class="modal-overlay" style="z-index:1100; background:rgba(0,0,0,0.8);" onclick="if(event.target===this) document.getElementById('modal-sub-root').innerHTML=''">
      <div class="modal" style="max-width:400px; border-top: 3px solid var(--green);">
        <div class="modal-header">
          <div class="modal-title" style="color:var(--green)"><i class="fas fa-sync"></i> Renouveler le contrat</div>
          <button class="modal-close" onclick="document.getElementById('modal-sub-root').innerHTML=''"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <p style="font-size:13px; color:var(--text2); margin-bottom:12px;">Combien de mois souhaitez-vous ajouter à la nouvelle période ?</p>
          <input type="number" id="renew-months" min="1" placeholder="Ex: 12" style="width:100%; padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); color:#fff; outline:none; font-size:16px; text-align:center;">
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="document.getElementById('modal-sub-root').innerHTML=''">Annuler</button>
          <button class="btn-primary" style="background:var(--green); border-color:var(--green);" onclick="submitRenewContract('${entId}')"><i class="fas fa-check"></i> Renouveler</button>
        </div>
      </div>
    </div>
  `;
  let subRoot = document.getElementById('modal-sub-root');
  if(!subRoot){ subRoot = document.createElement('div'); subRoot.id = 'modal-sub-root'; document.body.appendChild(subRoot); }
  subRoot.innerHTML = html;
}

function submitRenewContract(entId) {
  const mois = document.getElementById('renew-months').value;
  if(!mois || isNaN(mois) || mois <= 0) { showToast('Veuillez entrer un nombre valide.', 'warn'); return; }
  
  showToast(`Le contrat a été renouvelé pour ${mois} mois.`, "success");
  document.getElementById('modal-sub-root').innerHTML = '';
  closeModal(); 
  loadSADashboardData(); 
}
// ══════════════════════════════════════════════════════
//  DASHBOARD DATA LOADERS
// ══════════════════════════════════════════════════════
async function loadSADashboardData(){
  try {
    const res  = await fetch('/api/dashboard/superadmin');
    const data = await res.json();
    if(data.status !== 'success') return;
    const kpi = data.kpi || {};
    document.getElementById('dash-tot-ent')?.textContent !== undefined && (document.getElementById('dash-tot-ent').textContent = kpi.entreprises || 0);
    document.getElementById('dash-tot-subs')?.textContent !== undefined && (document.getElementById('dash-tot-subs').textContent = kpi.abonnes || 0);
    document.getElementById('dash-tot-alerts')?.textContent !== undefined && (document.getElementById('dash-tot-alerts').textContent = kpi.alertes || 0);

    // Blocs blockchain count
    try {
      const bcRes = await secureApiFetch('/api/blockchain/stats');
      const bcD   = await bcRes.json();
      const el = document.getElementById('dash-bc-count');
      if(el) el.textContent = bcD.total_blocks || 0;
    } catch(e){}

    const alertesRec = Array.isArray(data.alertes_recentes) ? data.alertes_recentes : [];
    const critiques = Array.isArray(data.conteneurs_critiques) ? data.conteneurs_critiques : [];
    const topEntreprises = Array.isArray(data.top_entreprises) ? data.top_entreprises : [];
    const chartData = data.charts || {};

    // Alertes recentes
    const alEl = document.getElementById('dash-alertes-list');
    if(alEl){
      alEl.innerHTML = alertesRec.length
        ? alertesRec.map(a=>`
          <div class="timeline-item">
            <div class="timeline-dot" style="background:var(--red)"></div>
            <div class="timeline-content">
              <div style="font-size:12px">${a.message || 'Alerte'}</div>
              <div class="timeline-time">${a.boite || '—'} • ${a.time || '—'}</div>
            </div>
          </div>`).join('')
        : '<div style="padding:20px;text-align:center;color:var(--text3)">Aucune alerte récente</div>';
    }

    // Top critiques
    const critEl = document.getElementById('dash-crit-containers');
    if(critEl){
      critEl.innerHTML = critiques.length
        ? critiques.map(c=>`
          <div class="container-item status-danger" style="margin-bottom:8px;cursor:pointer" onclick="showContainerDetailDB('${c.id}')">
            <div style="width:10px;height:10px;border-radius:50%;background:var(--red)"></div>
            <div class="container-info">
              <div class="container-id">${c.id || '—'}</div>
              <div class="container-meta">${c.count || 0} alertes enregistrées</div>
            </div>
            <span class="badge badge-danger">CRITIQUE</span>
          </div>`).join('')
        : '<div style="padding:16px;text-align:center;color:var(--text3)">Aucun conteneur critique</div>';
    }

  // Entreprises recentes
    const entEl = document.getElementById('dash-top-entreprises');
    if(entEl){
      entEl.innerHTML = topEntreprises.map(e => {
        const encodedData = encodeURIComponent(JSON.stringify(e));
        return `<tr>
        <td><div style="font-weight:600">${e.nom || '—'}</div></td>
        <td><span class="badge badge-info">${e.boites || 0} BB</span></td>
        <td>${e.clients || 0}</td>
        <td><span class="badge badge-${(String(e.statut || '').toLowerCase() === 'inactif' ? 'danger' : 'ok')}">${e.statut || 'active'}</span></td>
        <td style="font-size:12px">${e.contact || '—'}</td>
        <td><button class="btn-icon" type="button" onclick="openDashboardEnterpriseProfile('${encodedData}')">Profil</button></td>
      </tr>`;
      }).join('');
    }
  // Doughnut (répartition des alertes)
    if(charts['chart-subs'] && Array.isArray(chartData.alerts_dist)){
      charts['chart-subs'].data.datasets[0].data = chartData.alerts_dist;
      charts['chart-subs'].update();
    }

    // Refresh map markers
    await loadContainerData();
    if(maps['map-main']) refreshMapMarkers();
    if(charts['chart-revenue'] && chartData.abonnements) {
      charts['chart-revenue'].data.labels = chartData.abonnements.labels || [];
      charts['chart-revenue'].data.datasets[0].data = chartData.abonnements.data || [];
      charts['chart-revenue'].update();
    }

  } catch(e){ console.error('loadSADashboardData', e); }
}

async function loadOwnerDashboardData(){
  if(!currentUserId) return;
  try {
    const res  = await fetch(`/api/dashboard/owner?owner_id=${currentUserId}`);
    const data = await res.json();
    if(data.status !== 'success') return;
    const actif = data.boites.filter(b=>b.status!=='off').length;
    const alts  = data.boites.filter(b=>b.alerts&&b.alerts.length>0).length;
    document.getElementById('ow-active')?.textContent !== undefined && (document.getElementById('ow-active').textContent = actif);
    document.getElementById('ow-alerts')?.textContent !== undefined && (document.getElementById('ow-alerts').textContent = data.kpi?.total_alertes||alts);
    document.getElementById('ow-events')?.textContent !== undefined && (document.getElementById('ow-events').textContent = data.kpi?.total_events||'—');
    const boiteEl = document.getElementById('owner-boxes-list');
    if(boiteEl){
      boiteEl.innerHTML = data.boites.length
        ? data.boites.map(b=>`
          <div class="container-item status-${b.status}" style="margin-bottom:8px;cursor:pointer" onclick="showContainerDetailDB('${b.id_boite}')">
            <div style="width:10px;height:10px;border-radius:50%;background:${b.status==='ok'?'var(--green)':b.status==='warning'?'var(--amber)':b.status==='danger'?'var(--red)':'var(--text3)'}"></div>
            <div class="container-info">
              <div class="container-id">${b.id_boite}</div>
              <div style="font-size:11px;color:var(--text3)">${b.type_conteneur||'—'} | T:${b.temp??'—'}°C</div>
            </div>
            <span class="badge badge-${b.status==='ok'?'ok':b.status==='warning'?'warn':'danger'}">${b.status.toUpperCase()}</span>
          </div>`).join('')
        : '<div style="padding:16px;text-align:center;color:var(--text3)">Aucune boîte assignée</div>';
    }
    const badgeEl = document.getElementById('owner-boites-badge');
    if(badgeEl) badgeEl.innerHTML = `<span class="badge-dot"></span>${data.boites.length} Boîtes`;

    // bc count
    try {
      const bcRes = await secureApiFetch('/api/blockchain/stats');
      const bcD   = await bcRes.json();
      const el = document.getElementById('ow-bc');
      if(el) el.textContent = bcD.total_blocks;
    } catch(ex){}

    await loadContainerData();
    if(maps['map-main']) refreshMapMarkers();
    initCharts('dashboard');
    loadDynamicStats('7d');
  } catch(e){ console.error('loadOwnerDashboardData', e); }
}

async function loadContainerData() {
    try {
        const res = await secureApiFetch('/api/containers/all');
        if (res.ok) DB_CONTAINERS = await res.json();
    } catch (e) { console.error("Erreur chargement conteneurs"); }
}

// ══════════════════════════════════════════════════════
//  THRESHOLDS
// ══════════════════════════════════════════════════════
async function loadThresholds(id_boite){
  if(!id_boite) return;
  try {
    const res  = await fetch(`/api/config/thresholds/${id_boite}`);
    const data = await res.json();
    const set  = (id,v)=>{ const el=document.getElementById(id); if(el) el.value=v; };
    set('t-temp',  data.temp_max);
    set('t-hum',   data.humi_max);
    set('t-choc',  data.choc_max);
    set('t-press', data.pression_min);
    set('t-vit',   data.vitesse_max);
    set('t-angle', data.angle_max);
    showToast(`Seuils chargés pour ${id_boite}`,'info');
  } catch(e){ showToast('Erreur chargement seuils','warn'); }
}

async function saveThresholds(){
  const selEl  = document.getElementById('threshold-container-select') || document.getElementById('container-select');
  const id_boite = selEl?.value;
  if(!id_boite){ showToast('Veuillez choisir un conteneur','warn'); return; }
  const g = id=>document.getElementById(id)?.value;
  try {
    const res = await fetch('/api/config/thresholds', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        id_boite, temp_max:g('t-temp'), humi_max:g('t-hum'),
        choc_max:g('t-choc'), pression_min:g('t-press'),
        vitesse_max:g('t-vit'), angle_max:g('t-angle')
      })
    });
    const d = await res.json();
    if(res.ok) showToast('Seuils sauvegardés et scellés en blockchain ✓','success');
    else showToast(d.error||'Erreur','danger');
  } catch(e){ showToast('Erreur de communication','danger'); }
}

// ══════════════════════════════════════════════════════
//  CONTAINERS SELECT
// ══════════════════════════════════════════════════════

async function populateContainerSelect(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    try {
        const res = await secureApiFetch('/api/containers/all');
        const data = await res.json();
        const list = Array.isArray(data) ? data : [];
        const opts = list.map(c => `<option value="${escapeHTML(c.id_boite || c.id)}">${escapeHTML(c.id_boite || c.id)}${c.type_conteneurs ? ' — ' + escapeHTML(c.type_conteneurs) : ''}</option>`).join('');
        const defaultLabel = selectId === 'container-select' ? 'Tous conteneurs' : 'Choisir un conteneur…';
        sel.innerHTML = `<option value="">${defaultLabel}</option>` + opts;
        const tsel = document.getElementById('threshold-container-select');
        if (tsel) tsel.innerHTML = '<option value="">Sélectionner…</option>' + opts;
        const ssel = document.getElementById('stats-boite-select');
        if (ssel) ssel.innerHTML = '<option value="">Toutes les boîtes</option>' + opts;
    } catch(e) { console.error(e); }
}

async function loadAvailableContainers() {
    const sel = document.getElementById('container-select');
    if (!sel) return;
    try {
        const res = await secureApiFetch('/api/containers/disponibles');
        const data = await res.json();
        if (!data.length) {
            sel.innerHTML = '<option value="">Aucun conteneur disponible</option>';
            return;
        }
        sel.innerHTML = '<option value="">Choisir…</option>' + data.map(c => {
            const value = c.id_boite || c.id || c.id_conteneurs;
            const containerId = c.id_conteneurs || c.id || value;
            const label = containerId ? `${containerId}${c.id_boite ? ' / BB:' + c.id_boite : ''}` : value;
            return `<option value="${value}">${escapeHTML(label)}</option>`;
        }).join('');
    } catch(e) {
        console.error('loadAvailableContainers', e);
        sel.innerHTML = '<option value="">Erreur chargement</option>';
    }
}

// ══════════════════════════════════════════════════════
//  FORM ACTIONS
// ══════════════════════════════════════════════════════
function handleContainerTypeChange(){
  const type = document.getElementById('container-type').value;
  document.getElementById('container-volume-section').style.display = type ? 'block' : 'none';
  document.getElementById('open-top-note').style.display    = type==='OpenTop' ? 'block' : 'none';
  document.getElementById('pouce-field').style.display      = type==='DRY' ? 'block' : 'none';
  if(type==='HighCube'){ document.getElementById('container-volume').value='67'; calcPerimeter(); }
}

function calcPerimeter(){
  const vol = parseFloat(document.getElementById('container-volume').value) || 0;
  if(vol>0){
    const L = vol / (2.4 * 2.6);
    document.getElementById('container-perimeter').value = (2*(L+2.4)).toFixed(2)+' m';
  }
}

function updateContainerIdFields(){
  const qty = parseInt(document.getElementById('sell-qty').value) || 0;
  const section = document.getElementById('container-ids-section');
  if(!section) return;
  section.innerHTML = '';
  if(qty>0){
    const lbl = document.createElement('label');
    lbl.textContent = 'IDs des Conteneurs liés';
    lbl.style.cssText = 'display:block;margin-bottom:8px;font-size:12px;color:var(--text2)';
    section.appendChild(lbl);
    for(let i=0;i<qty;i++){
      const wrap = document.createElement('div');
      wrap.className = 'form-field';
      wrap.style.marginBottom = '10px';
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.placeholder = `ID Conteneur ${i+1} (ex: CONT-${String(i+1).padStart(3,'0')})`;
      inp.className = 'container-id-input';
      inp.id = `sell-container-id-${i}`;
      inp.oninput = () => updateIsoFeedback(inp, `iso-feedback-${i}`);
      wrap.appendChild(inp);
      const fb = document.createElement('small');
      fb.id = `iso-feedback-${i}`;
      fb.style.cssText = 'display:block;margin-top:4px;color:var(--text3);font-size:11px';
      wrap.appendChild(fb);
      section.appendChild(wrap);
    }
  }
  // Update summary
  const qs = parseInt(document.getElementById('sell-qty').value)||0;
  const company = document.getElementById('sell-company')?.value || '—';
  const sub = document.getElementById('sell-sub')?.value || '—';
  const summaryEl = document.getElementById('sale-summary');
  if(summaryEl) summaryEl.innerHTML = qs>0 ? `
    <div class="settings-item"><div class="settings-item-label">Entreprise</div><span>${company}</span></div>
    <div class="settings-item"><div class="settings-item-label">Nombre de BB</div><span>${qs}</span></div>
    <div class="settings-item"><div class="settings-item-label">Abonnement</div><span>${sub}</span></div>
    <div class="settings-item"><div class="settings-item-label">Montant estimé</div><span style="color:var(--cyan);font-weight:600">${(qs * (sub==='monthly'?15000:150000)).toLocaleString()} CFA</span></div>
  ` : '<div style="text-align:center;padding:20px;color:var(--text3)">Remplissez le formulaire</div>';
}
// On ajoute le paramètre optionnel forceUpdate = false
async function submitSale(forceUpdate = false) {
  const ids = [];
  document.querySelectorAll('.container-id-input').forEach(inp => { 
      if (inp.value) ids.push(inp.value.trim()); 
  });
  
  const nom_agence  = document.getElementById('sell-company')?.value.trim();
  const login       = document.getElementById('sell-login')?.value.trim();
  const password    = document.getElementById('sell-password')?.value;
  const email       = document.getElementById('sell-email')?.value.trim();
  const niu         = document.getElementById('sell-niu')?.value.trim();
  const location    = document.getElementById('sell-location')?.value.trim();
  const type_abo    = document.getElementById('sell-sub')?.value;
  const type_cont   = document.getElementById('container-type')?.value;
  const perim       = document.getElementById('container-perimeter')?.value;

  // 1. Vérification des champs requis
  if (!nom_agence || !login || !password || !email || !niu || ids.length === 0) {
    showToast('Veuillez remplir tous les champs obligatoires et ajouter au moins un conteneur.', 'warn'); 
    return;
  }
  if (!selectedSaleCoords || !selectedSaleCoords.lat) {
    showToast('Cliquez sur la carte pour sélectionner la position géographique de l\'entreprise.', 'warn'); 
    return;
  }

  try {
    // 2. Envoi des données (avec le paramètre force_update)
    const res = await fetch('/api/sell_containers', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nom_agence, login, password, email, niu, location,
        type_abonnement: type_abo, 
        conteneurs_ids: ids,
        perim, 
        type_conteneur: type_cont,
        lat: selectedSaleCoords.lat, 
        lon: selectedSaleCoords.lng,
        force_update: forceUpdate // <-- LE FAMEUX GARDE-FOU
      })
    });
    
    const d = await res.json();

    // 3. INTERCEPTION DU GARDE-FOU (L'entreprise existe déjà)
    if (res.status === 202 || d.status === 'confirm_required') {
        // Demande de confirmation à l'utilisateur
        const userConfirms = window.confirm(d.message);
        
        if (userConfirms) {
            // L'utilisateur dit OUI : On relance la même fonction en forçant la mise à jour
            return submitSale(true); 
        } else {
            // L'utilisateur dit NON : On annule tout
            showToast('Opération annulée.', 'info');
            return;
        }
    }

    // 4. SUCCÈS (Création ou Mise à jour réussie)
    if (res.ok && d.status === 'success') {
      showToast(`Entreprise enregistrée ! Boîtes noires liées: ${(d.boites||[]).join(', ')} ✓`, 'success');
      
      // Nettoyer le formulaire visuellement (optionnel mais très propre)
      document.querySelectorAll('.input-field').forEach(el => el.value = '');
      selectedSaleCoords = {lat: 0, lng: 0};
      
      // Redirection et Rafraîchissement
      if (document.activeElement) document.activeElement.blur(); 
      navigateTo('companies'); 
      
      // On force le moteur à télécharger la nouvelle base de données immédiatement
      if (typeof startAutoRefresh === 'function') {
          await startAutoRefresh();
      }
    } else {
      showToast('Erreur: ' + (d.error || 'Impossible d\'attribuer les conteneurs'), 'danger');
    }
  } catch(e) { 
      console.error(e);
      showToast('Erreur réseau ou serveur injoignable', 'danger'); 
  }
}

async function addNewClient() {
  const name = document.getElementById('new-client-name')?.value;
  const id_boite = document.getElementById('container-select')?.value; 
  const type_a = document.getElementById('new-client-period')?.value || 'Mensuel'; 

  if (!name) { 
      showToast('Le nom du client est requis', 'warn'); 
      return; 
  }
  if (!id_boite) { 
      showToast('Veuillez sélectionner un conteneur/boîte noire à affilier', 'warn'); 
      return; 
  }

  const formData = new FormData();
  formData.append('nom', name);
  formData.append('prenom', document.getElementById('new-client-firstname')?.value || '');
  formData.append('contact', document.getElementById('new-client-phone')?.value || '');
  formData.append('email', document.getElementById('new-client-email')?.value || '');
  formData.append('id_cni', document.getElementById('new-client-n-cni')?.value || '');
  formData.append('login', document.getElementById('new-client-login')?.value || '');
  formData.append('password', document.getElementById('new-client-password')?.value || '');
  
  // Données de liaison pour la table abonner
  formData.append('id_boite', id_boite);
  formData.append('type_a', type_a);
  formData.append('destination', document.getElementById('new-client-destination')?.value || '');
  formData.append('description', `${document.getElementById('new-client-cargo-type')?.value || ''} ${document.getElementById('new-client-cargo-name')?.value || ''}`.trim());
  formData.append('cargo_value', document.getElementById('new-client-value')?.value || '');

  const fileInput = document.getElementById('client-cni');
  if (fileInput?.files?.[0]) {
      formData.append('cni', fileInput.files[0]);
  }

  try {
    showToast('Enregistrement et affiliation du client...', 'info');
    
    // Utilisation du canal sécurisé pour l'envoi du formulaire
    const resp = await secureApiFetch('/api/register_user_file', { 
        method: 'POST', 
        body: formData 
    });
    const d = await resp.json();
    
    if (resp.ok) { 
        showToast(`Client ${name} créé avec succès et rattaché à la boîte ${id_boite} ✓`, 'success'); 
        if (typeof loadClientsData === 'function') loadClientsData();
        closeModal();
    } else { 
        showToast(d.error || 'Erreur lors de la création du compte', 'danger'); 
    }
  } catch (e) { 
      showToast('Erreur de communication avec le serveur d\'authentification', 'danger'); 
  }
}

// ══════════════════════════════════════════════════════
//  NOTIFICATIONS & CLOCK
// ══════════════════════════════════════════════════════
function buildNotifications(){ buildNotificationsFromDB(); }
async function buildNotificationsFromDB(){
  const listEl  = document.getElementById('notif-list');
  const countEl = document.getElementById('notif-count');
  if(!listEl) return;

  // 1. Récupérer les alertes matérielles des conteneurs
  let notifs = DB_CONTAINERS.filter(c=>c.alerts&&c.alerts.length>0).slice(0,6).flatMap(c=>
    c.alerts.slice(0,2).map(a=>({
      text:`<i class="fas fa-exclamation-triangle" style="color:var(--amber)"></i> ${c.id_boite}: ${a.substring(0,40)}`,
      sub:c.lastUpdate, 
      sev:'warn',
      action: "navigateTo('events')"
    }))
  );

  // 2. Récupérer les publications et annonces
  try {
    const res = await fetch('/api/publications');
    if(res.ok) {
        const pubs = await res.json();
        
        // Sauvegarde globale pour pouvoir les afficher dans la modale
        window.recentPublications = pubs; 
        
        pubs.slice(0, 5).forEach(pub => {
            let canSee = false;
            if(pub.cible === "Tous les utilisateurs" || currentRole === 'superadmin') {
                canSee = true;
            } else if (pub.cible === "Propriétaires BB seulement" && (currentRole === 'owner' || currentRole === 'client' || currentRole === 'agence')) {
                canSee = true;
            } else if (pub.cible === "Chauffeurs seulement" && currentRole === 'driver') {
                canSee = true;
            }

            if(canSee) {
                let icon = pub.niveau === 'Urgent' ? '<i class="fas fa-exclamation-circle" style="color:var(--red)"></i>' : '<i class="fas fa-bullhorn" style="color:var(--cyan)"></i>';
                notifs.unshift({
                    text: `${icon} <strong>Nouveau message :</strong> ${pub.titre}`,
                    sub: new Date(pub.date_pub).toLocaleString('fr-FR'),
                    sev: pub.niveau === 'Urgent' ? 'danger' : 'info',
                    // MODIFICATION ICI : Appel de la modale au lieu de la redirection
                    action: `openPublicationModal(${pub.id})` 
                });
            }
        });
    }
  } catch(e) {
      console.error("Erreur chargement notifications publications", e);
  }

  // 3. Affichage final
  notifs = notifs.slice(0, 10);
  if(!notifs.length){
    notifs = [{
        text:'<i class="fas fa-check-circle" style="color:var(--green)"></i> Aucune nouvelle notification', 
        sub:'Maintenant', 
        sev:'ok', 
        action: ""
    }];
  }

  listEl.innerHTML  = notifs.map(n=>`
    <div class="notif-item" onclick="closeNotif(); ${n.action}">
        <div style="font-size:13px;color:var(--text)">${n.text}</div>
        <div class="notif-time">${n.sub}</div>
    </div>
  `).join('');
  
  if(countEl) countEl.textContent = Math.max(0, notifs.filter(n=>n.sev!=='ok').length);
}


// ══════════════════════════════════════════════════════
//  THEME & MISC
// ══════════════════════════════════════════════════════
function toggleTheme(){
  const isLight = document.body.classList.toggle('theme-light');
  localStorage.setItem('theme', isLight?'light':'dark');
  const tog = document.getElementById('theme-toggle');
  if(tog) tog.checked = isLight;
}

// Simple horloge affichée dans la topbar
function startClock(){
  const el = document.getElementById('live-time');
  if(!el) return;
  const fmt = ()=>{ el.textContent = new Date().toLocaleTimeString(); };
  fmt();
  if(liveInterval) clearInterval(liveInterval);
  liveInterval = setInterval(fmt, 1000);
}


function toggleSidebar(){ document.getElementById('sidebar').classList.toggle('open'); }
function toggleNotif(){ document.getElementById('notif-panel').classList.toggle('open'); }
function closeNotif(){ document.getElementById('notif-panel').classList.remove('open'); }

// ═══════════════════════════════════════════════════════
// FONCTION GÉNÉRIQUE POUR AFFICHER L'IMAGE DANS UNE MODALE
// ═══════════════════════════════════════════════════════
function openImageModal(imageUrl, altText = 'Image', title = 'Document') {
  if (!imageUrl) {
    showToast('Aucune image disponible', 'warn');
    return;
  }
  
  const escapedUrl = escapeHTML(imageUrl);
  const isPDF = imageUrl.toLowerCase().endsWith('.pdf');
  
  const contentHtml = isPDF
    ? `<embed src="${escapedUrl}" type="application/pdf" width="100%" height="600px" style="border:1px solid var(--border);border-radius:12px"></embed>`
    : `<img src="${escapedUrl}" alt="${escapeHTML(altText)}" style="width:100%;max-height:80vh;object-fit:contain;border-radius:12px;border:1px solid var(--border)">`;
  
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:900px;max-height:90vh;overflow:auto">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-image"></i> ${escapeHTML(title)}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body" style="text-align:center;padding:20px">
          ${contentHtml}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          ${!isPDF ? `<a href="${escapedUrl}" target="_blank" class="btn-primary" download><i class="fas fa-download"></i> Télécharger</a>` : ''}
        </div>
      </div>
    </div>`;
}

function closeModal(){ document.getElementById('modal-root').innerHTML = ''; }

function showToast(msg, type='info'){
  const panel = document.getElementById('alert-panel');
  if(!panel) return;
  const icons = {info:'<i class="fas fa-info-circle"></i>', success:'<i class="fas fa-check-circle"></i>',
                 warn:'<i class="fas fa-exclamation-triangle"></i>', danger:'<i class="fas fa-skull"></i>'};
  const toast = document.createElement('div');
  toast.className = `alert-toast alert-toast-${type}`;
  toast.innerHTML = `<span>${icons[type]||icons.info}</span><span>${msg}</span>`;
  panel.appendChild(toast);
  try {
    if(type==='danger'||type==='warn'){ soundAlert.currentTime=0; soundAlert.play().catch(()=>{}); }
    else { soundInfo.currentTime=0; soundInfo.play().catch(()=>{}); }
  } catch(e){}
  setTimeout(()=>{ toast.style.opacity='0'; toast.style.transition='opacity .3s'; setTimeout(()=>toast.remove(),300); }, 4000);
}

function previewFile(input, previewId){
  const file = input.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = e=>{
    const div = document.getElementById(previewId);
    if(div) div.innerHTML = `<img src="${e.target.result}" style="max-width:100%;max-height:120px;border-radius:var(--radius);margin-top:8px;border:1px solid var(--border)">`;
  };
  reader.readAsDataURL(file);
}

function setTab(el, group, val){
  el.parentElement.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
}

function filterTable(tbodyId, val){
  const tbody = document.getElementById(tbodyId);
  if(!tbody) return;
  tbody.querySelectorAll('tr').forEach(row=>{
    row.style.display = !val || row.textContent.toLowerCase().includes(val.toLowerCase()) ? '' : 'none';
  });
}

function filterContainers(val){
  document.querySelectorAll('#containers-grid > div').forEach(el=>{
    el.style.display = !val || el.textContent.toLowerCase().includes(val.toLowerCase()) ? 'block' : 'none';
  });
}

// ? fonction de geolocalisation pour les conteneurs pour la fonction continuer 
async function geocode(ville) {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(ville)}&format=json&limit=1`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.length) return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
    throw new Error("Ville non trouvée");
}

function filterContainersStatus(status, tabEl){
  if(tabEl){ tabEl.parentElement.querySelectorAll('.tab').forEach(t=>t.classList.remove('active')); tabEl.classList.add('active'); }
  document.querySelectorAll('#containers-grid > div').forEach(el=>{
    el.style.display = status==='all' || el.className.includes('status-'+status) ? 'block' : 'none';
  });
}

function filterContainersList(val){
  document.querySelectorAll('#containers-sidebar-list .container-item').forEach(el=>{
    el.style.display = !val || el.textContent.toLowerCase().includes(val.toLowerCase()) ? 'flex' : 'none';
  });
}

function globalSearch(val){
  if(val.length < 2) return;
  const found = DB_CONTAINERS.find(c=>(c.id_boite||c.id).toLowerCase().includes(val.toLowerCase()));
  if(found) showToast(`Trouvé: ${found.id_boite||found.id} — ${found.type_conteneurs||'—'}`,'info');
}

// ══════════════════════════════════════════════════════
//  MODALS
// ══════════════════════════════════════════════════════
function showModal(type){
  if(type==='addDriver'){
    const options = DB_CONTAINERS.filter(c=>c.id_boite||c.id||c.id_conteneurs).map(c=>{
      const value = c.id_boite||c.id||c.id_conteneurs;
      const label = `${value}${c.type_conteneurs ? ' — ' + c.type_conteneurs : ''}`;
      return `<option value="${value}">${escapeHTML(label)}</option>`;
    }).join('');
    document.getElementById('modal-root').innerHTML = `
      <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
        <div class="modal">
          <div class="modal-header"><div class="modal-title"><i class="fas fa-truck"></i> Nouveau Chauffeur</div>
            <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
          <div class="modal-body">
            <div class="form-row">
              <div class="form-field"><label>Nom Complet</label><input type="text" id="new-drv-nom"></div>
              <div class="form-field"><label>Téléphone</label><input type="text" id="new-drv-phone"></div>
            </div>
            <div class="form-field"><label>CNI</label><input type="text" id="new-drv-cni"></div>
            <div class="form-field"><label>Login</label><input type="text" id="new-drv-login"></div>
            <div class="form-field"><label>Mot de Passe</label><input type="password" id="new-drv-pwd"></div>
            <div class="form-field"><label>Conteneur affilié</label>
              <select id="new-drv-boite"><option value="">Aucun conteneur</option>${options}</select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" onclick="closeModal()">Annuler</button>
            <button class="btn-primary" style="width:auto" onclick="createDriver()">
              <i class="fas fa-check"></i> Créer</button>
          </div>
        </div>
      </div>`;
  } else if(type==='addClient'){
    closeModal();
    navigateTo(currentRole==='owner'?'clients-own':'clients-sa');
  } else if(type==='settings'){
    // Débloquer le bouton avatar -> ouvrir la page Paramètres
    closeModal();
    navigateTo('settings');
  }
}

// ══════════════════════════════════════════════════════
//  JOURNEY (vider/continuer)
// ══════════════════════════════════════════════════════
function viderContainer(id){
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <div class="modal-header"><div class="modal-title">Vidage — ${id}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <p style="color:var(--text2)">Le conteneur sera vidé et passe en mode DOWN. Souhaitez-vous confirmer ?</p>
          <div class="form-field"><label>Motif</label><input type="text" id="vider-reason" placeholder="Raison du vidage"></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="showToast('Vidage enregistré — ${id}','success');closeModal()">Valider</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

function createDriver(){
  const nom = document.getElementById('new-drv-nom')?.value.trim();
  const phone = document.getElementById('new-drv-phone')?.value.trim();
  const cni = document.getElementById('new-drv-cni')?.value.trim();
  const login = document.getElementById('new-drv-login')?.value.trim();
  const pwd = document.getElementById('new-drv-pwd')?.value;

  if (!nom || !cni || !login || !pwd) {
    showToast('Veuillez remplir le nom, le CNI, le login et le mot de passe.', 'warn');
    return;
  }

  const [prenom, ...rest] = nom.split(' ');
  const nomfam = rest.join(' ');
  const id_boite = document.getElementById('new-drv-boite')?.value || null;

  const formData = new FormData();
  formData.append('id_cni', cni);
  formData.append('login', login);
  formData.append('password', pwd);
  formData.append('nom', nomfam || '');
  formData.append('prenom', prenom);
  formData.append('contact', phone);
  formData.append('id_boite', id_boite);
  const fileInput = document.getElementById('new-drv-cni-image');
  if (fileInput?.files?.[0]) {
    formData.append('cni', fileInput.files[0]);
  }

  fetch('/api/register_driver', {
    method: 'POST',
    body: formData
  }).then(async res => {
    const data = await res.json();
    if (res.ok) {
      showToast('Chauffeur créé avec succès.', 'success');
      closeModal();
      await loadDriversData();
    } else {
      showToast(data.error || 'Erreur création chauffeur', 'danger');
    }
  }).catch(e => {
    console.error(e);
    showToast('Erreur réseau création chauffeur', 'danger');
  });
}

function openDriverMessageModal(id){
  const d = DB_DRIVERS.find(x=>x.id_cni===id);
  if(!d) return showToast('Chauffeur introuvable','warn');
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:520px">
        <div class="modal-header"><div class="modal-title"><i class="fas fa-envelope"></i> Message à ${escapeHTML(d.nom_chauffeurs||d.nom||'Chauffeur')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-field"><label>Message</label><textarea id="driver-msg-text" rows="5" placeholder="Tapez votre message ici..."></textarea></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="sendDriverMessage('${id}')"><i class="fas fa-paper-plane"></i> Envoyer</button>
        </div>
      </div>
    </div>`;
}

async function sendDriverMessage(id){
  const text = document.getElementById('driver-msg-text')?.value.trim();
  if(!text) return showToast('Veuillez écrire un message.','warn');
  try {
    const res = await fetch('/api/driver/message', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id_cni:id, message:text})
    });
    const data = await res.json();
    if(res.ok){ showToast('Message envoyé au chauffeur.','success'); closeModal(); }
    else showToast(data.error || 'Erreur envoi message','danger');
  } catch(e){ console.error(e); showToast('Erreur réseau message','danger'); }
}

function openDriverProfileModal(id){
  const d = DB_DRIVERS.find(x=>x.id_cni===id);
  if(!d) return showToast('Chauffeur introuvable','warn');
  const imageUrl = d.profile_image || d.cni_file || d.image || d.document || d.logo;
  const currentBoites = [];
  if(Array.isArray(d.boites)) currentBoites.push(...d.boites);
  else if(typeof d.id_boites === 'string' && d.id_boites) {
    try { currentBoites.push(...JSON.parse(d.id_boites)); } catch(e) {}
  } else if(d.id_boite) {
    currentBoites.push(d.id_boite);
  }
  const boitesHtml = currentBoites.length
    ? currentBoites.map(b => `<span class="badge badge-info" style="margin-right:6px">${escapeHTML(b)}</span>`).join('')
    : '<span style="color:var(--text3)">Aucun conteneur lié</span>';
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:680px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-user"></i> Profil Chauffeur — ${escapeHTML(d.nom_chauffeurs||d.nom||'')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div class="grid-2" style="gap:16px;margin-bottom:16px">
            <div class="form-field"><label>Nom</label><input readonly value="${escapeHTML(d.nom_chauffeurs||d.nom||'')}"></div>
            <div class="form-field"><label>CNI</label><input readonly value="${escapeHTML(d.id_cni||'')}"></div>
          </div>
          <div class="grid-2" style="gap:16px;margin-bottom:16px">
            <div class="form-field"><label>Login</label><input readonly value="${escapeHTML(d.login||'')}"></div>
            <div class="form-field"><label>Transport</label><input readonly value="${escapeHTML(d.moyen_transport||'')}"></div>
          </div>
          <div class="form-field"><label>Conteneurs liés</label><div style="display:flex;flex-wrap:wrap;gap:8px;padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius)">${boitesHtml}</div></div>
          ${imageUrl ? `
          <div class="settings-item">
            <div class="settings-item-label"><i class="fas fa-image"></i> Document / Photo</div>
            <button class="btn-icon" onclick="openImageModal('${escapeHTML(imageUrl)}', 'Photo Chauffeur', 'Document - ${escapeHTML(d.nom_chauffeurs||d.nom||'')}')"><i class="fas fa-eye"></i> Voir</button>
          </div>
          ` : ''}
        </div>
        <div class="modal-footer" style="justify-content:flex-start;gap:10px;">
          <button class="btn-secondary" onclick="closeModal()"><i class="fas fa-times"></i> Fermer</button>
          <button class="btn-icon" onclick="openEditDriverModal('${id}')"><i class="fas fa-edit"></i></button>
          <button class="btn-icon" onclick="promptDriverAddContainer('${id}')"><i class="fas fa-plus"></i></button>
        </div>
      </div>
    </div>`;
}

function promptDriverAddContainer(id){
  fetch('/api/containers/available')
    .then(res => res.ok ? res.json() : Promise.reject(res))
    .then(data => {
      const options = Array.isArray(data) && data.length
        ? data.map(c => {
            const value = c.id_boite || c.id || '';
            const label = `${c.id || ''}${c.id_boite ? ' / ' + c.id_boite : ''}`;
            return value ? `<option value="${escapeHTML(value)}">${escapeHTML(label)}</option>` : '';
          }).filter(Boolean).join('')
        : '<option value="">Aucun conteneur disponible</option>';
      document.getElementById('modal-root').innerHTML = `
        <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
          <div class="modal" style="max-width:520px">
            <div class="modal-header"><div class="modal-title"><i class="fas fa-plus"></i> Ajouter un conteneur</div>
              <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
            <div class="modal-body">
              <div class="form-field"><label>Sélectionner un conteneur</label>
                <select id="driver-add-container-select">${options}</select>
              </div>
              <div style="font-size:12px;color:var(--text3);margin-top:10px">Sélectionnez un conteneur lié à un propriétaire.</div>
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" onclick="closeModal()">Annuler</button>
              <button class="btn-primary" onclick="submitDriverAddContainer('${id}')"><i class="fas fa-check"></i> Ajouter</button>
            </div>
          </div>
        </div>`;
    })
    .catch(err => {
      console.error(err);
      showToast('Impossible de charger les conteneurs disponibles.','danger');
    });
}

async function submitDriverAddContainer(id){
  const selected = document.getElementById('driver-add-container-select')?.value;
  if(!selected) return showToast('Veuillez choisir un conteneur.','warn');
  const d = DB_DRIVERS.find(x=>x.id_cni===id);
  if(!d) return showToast('Chauffeur introuvable','warn');
  let existing = [];
  if(Array.isArray(d.boites)) existing = [...d.boites];
  else if(typeof d.id_boites === 'string' && d.id_boites){
    try{ existing = JSON.parse(d.id_boites) || []; } catch(e){ existing = []; }
  } else if(d.id_boite){ existing = [d.id_boite]; }
  if(!existing.includes(selected)) existing.push(selected);
  try {
    const res = await fetch('/api/driver/manage', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id_cni:id, id_boites: existing, blocked: !!d.blocked})
    });
    const data = await res.json();
    if(res.ok){
      showToast('Conteneur ajouté au chauffeur.','success');
      closeModal();
      await loadDriversData();
    } else {
      showToast(data.error || 'Erreur ajout conteneur','danger');
    }
  } catch(e){ console.error(e); showToast('Erreur réseau ajout conteneur','danger'); }
}

function openDriverManageModal(id){
  const d = DB_DRIVERS.find(x=>x.id_cni===id);
  if(!d) return showToast('Chauffeur introuvable','warn');
  const options = DB_CONTAINERS.map(c => {
    const value = c.id_boite || c.id || c.id_conteneurs || '';
    const label = `${value}${c.type_conteneurs ? ' — ' + c.type_conteneurs : ''}`;
    const selected = (d.boites && Array.isArray(d.boites)) ? (d.boites.includes(value)?'selected':'') : (value===d.id_boite ? 'selected' : '');
    return value ? `<option value="${value}" ${selected}>${escapeHTML(label)}</option>` : '';
  }).filter(Boolean).join('');
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:560px">
        <div class="modal-header"><div class="modal-title"><i class="fas fa-cogs"></i> Gérer ${escapeHTML(d.nom_chauffeurs||d.nom||'Chauffeur')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-field"><label>Conteneurs affiliés (sélection multiple possible)</label>
            <select id="driver-assign-boites" multiple size="6">${options || '<option value="">Aucun conteneur disponible</option>'}</select>
            <div style="font-size:11px;color:var(--text3);margin-top:6px">Maintenez Ctrl/Cmd pour sélectionner plusieurs conteneurs.</div>
          </div>
          <div class="settings-item" style="margin-top:12px">
            <div class="settings-item-info"><div class="settings-item-label">Bloquer le chauffeur</div><div class="settings-item-desc">Il ne pourra plus être affecté à de nouvelles missions.</div></div>
            <label class="toggle-switch"><input type="checkbox" id="driver-blocked" ${d.blocked ? 'checked' : ''}><span class="toggle-slider"></span></label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-primary" onclick="updateDriverAssignment('${id}')"><i class="fas fa-save"></i> Sauvegarder</button>
        </div>
      </div>
    </div>`;
}

async function updateDriverAssignment(id){
  const sel = document.getElementById('driver-assign-boites');
  let id_boite = null;
  let id_boites = [];
  if(sel){
    const values = Array.from(sel.selectedOptions||[]).map(o=>o.value).filter(Boolean);
    id_boites = values;
    id_boite = values.length===1?values[0]:null;
  }
  const blocked = !!document.getElementById('driver-blocked')?.checked;
  try {
    const res = await fetch('/api/driver/manage', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id_cni:id, id_boite, id_boites, blocked})
    });
    const data = await res.json();
    if(res.ok){ showToast('Affectation chauffeur mise à jour.','success'); closeModal(); await loadDriversData(); }
    else showToast(data.error || 'Erreur mise à jour chauffeur','danger');
  } catch(e){ console.error(e); showToast('Erreur réseau mise à jour','danger'); }
}

function continuerContainer(id){
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:540px">
        <div class="modal-header"><div class="modal-title">Continuer — ${id}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-field"><label>Moyen de transport</label>
              <select id="cont-mode"><option value="driving">Camion</option><option value="ferry">Navire</option><option value="train">Train</option></select>
            </div>
            <div class="form-field"><label>Destination</label><input type="text" id="cont-dest" placeholder="Ville…"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="executeContinuer('${id}')">Valider & Tracer</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

async function executeContinuer(id){
  const dest = document.getElementById('cont-dest')?.value;
  const mode = document.getElementById('cont-mode')?.value || 'driving';
  if(!dest){ showToast('Destination requise','warn'); return; }
  const c = DB_CONTAINERS.find(x=>x.id_boite===id||x.id===id);
  closeModal();
  showToast(`${id}: trajet vers ${dest} défini.`,'success');
  if(c && c.lat && c.lon && maps['map-main']){
    const destLat = Number(c.lat) + (Math.random()-.5)*1.2;
    const destLng = Number(c.lon) + (Math.random()-.5)*1.2;
    const route = await fetchOSRMRoute([[c.lat,c.lon],[destLat,destLng]], mode);
    if(route) L.polyline(route, {color:'#00d4ff', weight:3, opacity:.8}).addTo(maps['map-main']);
  }
}

// ══════════════════════════════════════════════════════
//  PROXIMITY CHECK
// ══════════════════════════════════════════════════════
function startDestinationProximityCheck(){
  // Lightweight version without continuous distance checks
}

function openPublicationModal(pubId) {
    // 1. Vérifier si on a bien les publications en mémoire
    if (!window.recentPublications) return;
    const pub = window.recentPublications.find(p => p.id === pubId);
    if (!pub) return;

    // 2. SÉCURITÉ : Si une modale est déjà ouverte (ou buggée), on la supprime d'abord
    const existingModal = document.getElementById('pub-modal-overlay');
    if (existingModal) existingModal.remove();

    // 3. Déterminer l'apparence des badges
    let targetBadge = "badge-info";
    let targetIcon = "fa-globe"; 
    if (pub.cible !== "Tous les utilisateurs") {
        targetBadge = "badge-warn";
        targetIcon = "fa-lock"; 
    }

    // 4. Construire le design de la fenêtre (Modale)
    // Note : onclick="this.remove()" sur le fond noir permet de fermer la fenêtre en cliquant à côté
    const modalHtml = `
    <div id="pub-modal-overlay" onclick="this.remove()" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:99999; display:flex; align-items:center; justify-content:center; backdrop-filter: blur(3px);">
        
        <div class="card" onclick="event.stopPropagation()" style="width: 90%; max-width: 500px; max-height: 80vh; overflow-y: auto; position:relative; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid var(--border);">
            
            <button onclick="document.getElementById('pub-modal-overlay').remove()" style="position:absolute; top:15px; right:15px; background:none; border:none; color:var(--text); font-size:20px; cursor:pointer;">
                <i class="fas fa-times"></i>
            </button>
            
            <div style="margin-bottom:15px; padding-right: 30px;">
                <span class="badge ${targetBadge}"><i class="fas ${targetIcon}"></i> ${pub.cible}</span>
                <span class="badge ${pub.niveau === 'Urgent' ? 'badge-danger' : 'badge-info'}"><i class="fas fa-bullhorn"></i> ${pub.niveau}</span>
            </div>
            
            <h2 style="margin-bottom: 5px; color: var(--cyan); font-size: 18px; font-family: var(--font-main);">${pub.titre}</h2>
            <div style="font-size:11px; color:var(--text3); margin-bottom: 20px;">
                <i class="fas fa-clock"></i> Publié le ${new Date(pub.date_pub).toLocaleString('fr-FR')}
            </div>
            
            <div style="font-size:13px; color:var(--text); white-space:pre-wrap; line-height: 1.6; padding: 15px; background: var(--bg2); border-radius: var(--radius); border: 1px solid var(--border);">
                ${pub.contenu}
            </div>
            
        </div>
    </div>
    `;

    // 5. Afficher la modale à l'écran (Ceci doit rester DANS la fonction)
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// ══════════════════════════════════════════════════════
//  AI ASSISTANT
// ══════════════════════════════════════════════════════
// Le frontend ne stocke aucune clé API. Gemini est appelé via le proxy Flask.
const AI_CHAT_ENDPOINT = '/api/ai/chat';
const AI_CHAT_PROVIDER = 'Google Gemini';

function openAIAssistant(containerId=null){
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:900px;max-height:85vh;display:flex;flex-direction:column">
        <div class="modal-header">
          <div class="modal-title" style="font-family:var(--display);color:var(--cyan)">
            <i class="fa-solid fa-robot"></i> Assistant IA — Rapports ARGOS
          </div>
          <button class="modal-close" onclick="closeModal()"><i class="fa-solid fa-times"></i></button>
        </div>
        <div class="modal-body" style="flex:1;display:flex;flex-direction:column;padding:0;overflow:hidden">
          <div id="ai-chat-messages" style="flex:1;overflow-y:auto;padding:16px"></div>
          <div style="padding:12px;background:var(--bg2);border-top:1px solid var(--border)">
            <div id="ai-suggestions" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">
              <button class="ai-chip" onclick="quickAIMessage('incident')"> Signaler incident</button>
              <button class="ai-chip" onclick="quickAIMessage('pertes')"> Évaluer pertes</button>
              <button class="ai-chip" onclick="quickAIMessage('chronologie')">⏱ Chronologie</button>
              <button class="ai-chip" onclick="quickAIMessage('excuse')">✍ Lettre d'excuse</button>
            </div>
            <div style="display:flex;gap:8px">
              <input type="text" id="ai-chat-input" placeholder="Décrivez l'incident ou demandez un rapport…"
                style="flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:8px 12px;color:var(--text);font-size:13px"
                onkeydown="if(event.key==='Enter')sendAIMessage()">
              <button class="btn-primary" style="width:auto;padding:8px 16px" onclick="sendAIMessage()">
                <i class="fa-solid fa-paper-plane"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
  setTimeout(()=>{
    addAIMessage('Bonjour ! Je suis l\'assistant de rédaction ARGOS. Je peux générer des rapports d\'incidents, évaluer des pertes, reconstituer des chronologies ou rédiger des correspondances professionnelles. Que souhaitez-vous ?');
    if(containerId){
      const c = DB_CONTAINERS.find(x=>x.id_boite===containerId||x.id===containerId);
      if(c){
        const ctx = `Boîte: ${c.id_boite||c.id} | Type: ${c.type_conteneurs} | Statut: ${c.status} | T:${c.temp}°C | H:${c.humidity}% | P:${c.pressure}hPa | V:${c.speed}km/h | G:${c.shock}G | Alertes: ${(c.alerts||[]).join(' / ')||'aucune'}`;
        sendAIMessage(`Génère un rapport professionnel complet pour ce conteneur:\n\n${ctx}`);
      }
    }
  }, 300);
}

function quickAIMessage(type){
  const msgs = {
    incident:'Je souhaite déclarer un incident survenu sur un conteneur.',
    pertes:"J'ai besoin d'un rapport détaillé des pertes matérielles.",
    chronologie:'Aidez-moi à retracer la chronologie des événements du trajet.',
    excuse:"Rédigez une lettre d'excuse professionnelle pour cet incident."
  };
  const msg = msgs[type] || '';
  if(msg){ document.getElementById('ai-chat-input').value=msg; sendAIMessage(msg); }
}

function addAIMessage(content){
  const c = document.getElementById('ai-chat-messages');
  if(!c) return;
  const div = document.createElement('div');
  div.className = 'ai-msg ai';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = content;
  div.appendChild(bubble);
  c.appendChild(div); c.scrollTop = c.scrollHeight;
  return div;
}

function addUserMessage(content){
  const c = document.getElementById('ai-chat-messages');
  if(!c) return;
  const div = document.createElement('div');
  div.className = 'ai-msg user';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = content;
  div.appendChild(bubble);
  c.appendChild(div); c.scrollTop = c.scrollHeight;
}

function formatAIReply(content){
  const escaped = String(content ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
  return escaped
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

async function sendAIMessage(msgText=null){
  const input = document.getElementById('ai-chat-input');
  if(!input) return;
  const text = msgText || input.value.trim();
  if(!text) return;
  
  addUserMessage(text);
  if(!msgText) input.value = '';
  input.disabled = true;
  const loading = addAIMessage(`<em>${AI_CHAT_PROVIDER} rédige une réponse...</em>`);
  
  //cette logique pour récupérer les données live
  const containers = Array.isArray(DB_CONTAINERS) ? DB_CONTAINERS : [];
  const ctx = containers.slice(0,5).map(c=>`${c.id_boite||c.id}: ${c.status} T:${c.temp}°C ${(c.alerts||[]).join(' ')}`).join('\n');
  const sys = `Tu es ReportAI, assistant de rédaction pour l'application ARGOS (suivi de conteneurs Cameroun). Contexte:\n${ctx}\nAide l'utilisateur avec des rapports professionnels en français.`;
  
  try {
    const res = await fetch(AI_CHAT_ENDPOINT, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ 
          message: text,
          systemPrompt: sys,
          contextData: ctx
      })
    });
    
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || `Serveur IA erreur ${res.status}`);
    
    // gère plusieurs formats de réponse
    const resp = data.reply || data.provider_response?.choices?.[0]?.message?.content || data.provider_response?.choices?.[0]?.text || JSON.stringify(data);
    if(loading) loading.remove();
    addAIMessage(formatAIReply(resp));
  } catch(e){
    if(loading) loading.remove();
    addAIMessage(`<span style="color:var(--red)">Erreur IA: ${formatAIReply(e.message)}</span>`);
  } finally {
    input.disabled = false;
    input.focus();
  }
}

// ══════════════════════════════════════════════════════
//  GEO UTILS
// ══════════════════════════════════════════════════════
function getDistanceFromLatLonInM(lat1,lon1,lat2,lon2){
  const R = 6371000, dLat=deg2rad(lat2-lat1), dLon=deg2rad(lon2-lon1);
  const a = Math.sin(dLat/2)**2 + Math.cos(deg2rad(lat1))*Math.cos(deg2rad(lat2))*Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}
function deg2rad(d){ return d*(Math.PI/180); }

// ══════════════════════════════════════════════════════
//  KEYBOARD SHORTCUTS
// ══════════════════════════════════════════════════════
document.addEventListener('keydown', e=>{
  if(e.key==='Escape'){ closeModal(); closeNotif(); }
  if(e.ctrlKey && e.key==='k'){ e.preventDefault(); openAIAssistant(); }
});

// ══════════════════════════════════════════════════════
//  AUTO START
// ══════════════════════════════════════════════════════
window.onload = ()=>{
  const savedRole = localStorage.getItem('currentRole');
  const savedUid  = localStorage.getItem('currentUserId');
  if(savedRole && localStorage.getItem('isLoggedIn')){
    currentRole   = savedRole;
    currentUserId = savedUid || null;
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app').style.display = 'flex';
    initApp();
  }
};
