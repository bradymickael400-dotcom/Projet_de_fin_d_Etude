// ═══════════════════════════════════════════════════════
//  ARGOS — script.js  (version DB-live complète)
// ═══════════════════════════════════════════════════════

// ── STATE ──────────────────────────────────────────────
let currentRole = 'superadmin';
let currentPage = '';
let currentUserId = null;
let pendingQrUuid = null;
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
let sidebarCollapseTimer = null;
let sidebarAutoCollapseBound = false;

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
let MAP_BLACK_BOXES = []; // boîtes suivies sans conteneur, visibles sur la carte
let MAP_GPS_POSITIONS = []; // positions issues exclusivement de /api/containers/positions
let MAP_FILTER = 'all';
let MAP_TRAIL_VERSION = 0;
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

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('fr-FR');
}

function boxLabel(c) {
  return c?.numero_serie || c?.boite_label || c?.id_boite || c?.id || '—';
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

// ── API AUTHENTIFIEE ──────────────────────────────────────
const nativeFetch = window.fetch.bind(window);

window.fetch = function argosAuthenticatedFetch(resource, options = {}) {
    const url = typeof resource === 'string' ? resource : (resource && resource.url) || '';
    const isArgosApi = url.startsWith('/api/') || url.startsWith(window.location.origin + '/api/');
    const isPublicAuth = url.includes('/api/login') || url.includes('/api/auth/login-availability');
    const token = sessionStorage.getItem('argosAccessToken') || localStorage.getItem('argosAccessToken') || '';
    if (isArgosApi && !isPublicAuth && token) {
        options.headers = {
            ...(options.headers || {}),
            'Authorization': `Bearer ${token}`,
        };
    }
    return nativeFetch(resource, options).then(response => {
        if (response.status === 401 && isArgosApi && !isPublicAuth) {
            sessionStorage.removeItem('argosAccessToken');
            localStorage.removeItem('argosAccessToken');
            localStorage.removeItem('isLoggedIn');
        }
        return response;
    });
};

async function secureApiFetch(endpoint, options = {}) {
    const token = sessionStorage.getItem('argosAccessToken') || localStorage.getItem('argosAccessToken') || '';
    options.headers = {
        ...(options.headers || {}),
        ...(token ? {'Authorization': `Bearer ${token}`} : {}),
    };
    return await fetch(endpoint, options);
}

// Audio
const soundInfo  = new Audio('/static/audio/notif.mp3');
const soundAlert = new Audio('/static/audio/notif.mp3');
soundInfo.volume = 0.5; soundAlert.volume = 0.8;

// Fond de cartes disponibles
const MAP_LAYERS = [
  { name:'OpenStreetMap',    url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png', attribution:'© OpenStreetMap contributors' },
  { name:'Satellite Esri',   url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attribution:'Tiles © Esri — Sources: Esri, Maxar, Earthstar Geographics and the GIS User Community' },
  { name:'Terrain Stadia',   url:'https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}{r}.png', attribution:'© Stadia Maps © OpenMapTiles © OpenStreetMap contributors' },
];

// ── NAV ────────────────────────────────────────────────
const NAV = {
  superadmin:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie',          label:'Dashboard'},
    {id:'map',       icon:'fa-solid fa-map-location-dot',   label:'Monitoring'},
    {id:'containers',icon:'fa-solid fa-box',                label:'Conteneurs'},
    {id:'my-boxes',  icon:'fa-solid fa-inbox',              label:'Mes Boîtes'},
    // {id:'nouvelle-bn',icon:'fa-solid fa-plus-circle',      label:'Nouvelle BN'},
    {id:'sell',      icon:'fa-solid fa-arrow-up-from-bracket',label:'Attribution'},
    {id:'companies', icon:'fa-solid fa-building',           label:'Entreprises'},
    {id:'clients-sa',icon:'fa-solid fa-users',              label:'Abonnés'},
    {id:'stats',     icon:'fa-solid fa-chart-line',         label:'Statistiques'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation',label:'Événements'},
    {id:'blockchain',icon:'fa-solid fa-link',               label:'Données Scellées'},
    {id:'blog',      icon:'fa-solid fa-newspaper',          label:'Publications'},
    {id:'documents', icon:'fa-solid fa-folder-open',         label:'Dossiers'},
    {id:'archive',   icon:'fa-solid fa-archive',            label:'Archive'},
    {id:'settings',  icon:'fa-solid fa-gear',               label:'Paramètres'},
  ],
  company:[
    {id:'dashboard',icon:'fa-solid fa-chart-pie',label:'Dashboard'},
    {id:'map',icon:'fa-solid fa-map',label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',label:'Conteneurs Liés'},
    {id:'clients-own',icon:'fa-solid fa-users',label:'Mes Clients'},
    {id:'stats',icon:'fa-solid fa-chart-line',label:'Statistiques'},
    {id:'events',icon:'fa-solid fa-triangle-exclamation',label:'Alertes'},
    {id:'documents',icon:'fa-solid fa-folder-open',label:'Dossiers'},
    {id:'archive',   icon:'fa-solid fa-archive',            label:'Archive'},
    {id:'settings',icon:'fa-solid fa-gear',label:'Paramètres'},
  ],
  owner:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie',   label:'Mon Dashboard'},
    {id:'map',       icon:'fa-solid fa-map',          label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',          label:'Mes Conteneurs'},
    {id:'my-boxes',  icon:'fa-solid fa-inbox',        label:'Mes Boîtes'},
    {id:'drivers',   icon:'fa-solid fa-truck',        label:'Chauffeurs'},
    {id:'clients-own',icon:'fa-solid fa-users',       label:'Clients'},
    {id:'stats',     icon:'fa-solid fa-chart-line',   label:'Analytiques'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation',label:'Alertes'},
    {id:'blockchain',icon:'fa-solid fa-link',         label:'Données Scellées'},
    {id:'documents', icon:'fa-solid fa-folder-open',   label:'Dossiers'},
    {id:'archive',   icon:'fa-solid fa-archive',            label:'Archive'},
    {id:'settings',  icon:'fa-solid fa-gear',         label:'Paramètres'},
  ],
  driver:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie',           label:'Ma Mission'},
    {id:'map',       icon:'fa-solid fa-map',                  label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',                  label:'Mon Conteneur'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation', label:'Alertes'},
    {id:'documents', icon:'fa-solid fa-folder-open',           label:'Dossiers'},
    {id:'settings',  icon:'fa-solid fa-gear',                 label:'Paramètres'},
  ],
  client:[
    {id:'dashboard', icon:'fa-solid fa-chart-pie', label:'Mon Colis'},
    {id:'map',       icon:'fa-solid fa-map',        label:'Suivi'},
    {id:'events',    icon:'fa-solid fa-triangle-exclamation', label:'Événements'},
    {id:'documents', icon:'fa-solid fa-folder-open', label:'Dossiers'},
    {id:'settings',  icon:'fa-solid fa-gear',       label:'Paramètres'},
  ],
  port_authority:[
    {id:'dashboard', icon:'fa-solid fa-anchor', label:'Vue Portuaire'},
    {id:'containers',icon:'fa-solid fa-box', label:'Conteneurs Port'},
    {id:'events', icon:'fa-solid fa-triangle-exclamation', label:'Alertes'},
    {id:'blockchain',icon:'fa-solid fa-link', label:'Données Scellées'},
    {id:'archive',   icon:'fa-solid fa-archive',            label:'Archive'},
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
