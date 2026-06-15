// ===== STATE =====
let currentRole = 'superadmin';
let currentPage = '';
let maps = {};
let charts = {};
let liveInterval = null;
let sensorInterval = null;

// ===== DATA =====
const COMPANIES = [
  {id:'E001',name:'TransAfrique SARL',location:'Douala, Cameroun',boxes:3,status:'active',sub:'owner',lat:4.0511,lng:9.7679,contact:'Jean Mballa',phone:'+237 6 90 11 22 33',clients:12,revenue:450000,joined:'2024-01',ownedBoxes:['BN-001','BN-002','BN-003']},
  {id:'E002',name:'Sahel Logistics',location:'Yaoundé, Cameroun',boxes:1,status:'active',sub:'owner',lat:3.8667,lng:11.5167,contact:'Fatou Diop',phone:'+237 6 55 77 88 99',clients:8,revenue:180000,joined:'2024-03',ownedBoxes:['BN-004']},
  {id:'E003',name:'CargoCentral',location:'Bafoussam, Cameroun',boxes:2,status:'warning',sub:'subscriber',lat:5.4767,lng:10.4195,contact:'Paul Nguemo',phone:'+237 6 22 33 44 55',clients:5,revenue:120000,joined:'2024-05',ownedBoxes:['BN-005','BN-006']},
  {id:'E004',name:'ExportPlus',location:'Ngaoundéré, Cameroun',boxes:0,status:'active',sub:'subscriber',lat:7.3291,lng:13.5846,contact:'Ali Hassan',phone:'+237 6 11 22 33 44',clients:3,revenue:75000,joined:'2024-06',ownedBoxes:[]},
];
const CONTAINERS = [
  {id:'BN-001',company:'TransAfrique SARL',driver:'Marc Essono',status:'ok',temp:22.4,humidity:58,pressure:1013,shock:0,lat:4.8156,lng:11.5095,speed:72,route:'Douala → Yaoundé',progress:68,lastUpdate:'12:34:22',events:[],securityOn:true,cargo:'Électronique',value:12500000,destinations:[],mode:'driving',currentDest:0},
  {id:'BN-002',company:'TransAfrique SARL',driver:'Samuel Biya',status:'warning',temp:34.8,humidity:82,pressure:1009,shock:2,lat:5.2012,lng:11.9456,speed:0,route:'Yaoundé → Bafoussam',progress:45,lastUpdate:'12:33:55',events:['TEMP_HIGH','HUM_HIGH'],securityOn:true,cargo:'Alimentaire',value:3200000,destinations:[],mode:'driving',currentDest:0},
  {id:'BN-003',company:'TransAfrique SARL',driver:'Pierre Ateba',status:'danger',temp:28.1,humidity:65,pressure:1005,shock:7,lat:6.1234,lng:12.4567,speed:0,route:'Ngaoundéré → Douala',progress:23,lastUpdate:'12:35:01',events:['SHOCK_DETECTED','VIBRATION_HIGH'],securityOn:false,cargo:'Matériaux',value:8750000,destinations:[],mode:'driving',currentDest:0},
  {id:'BN-004',company:'Sahel Logistics',driver:'Amina Bah',status:'ok',temp:26.3,humidity:61,pressure:1011,shock:0,lat:3.9456,lng:11.4123,speed:58,route:'Yaoundé → Douala',progress:81,lastUpdate:'12:34:45',events:[],securityOn:true,cargo:'Textile',value:2100000,destinations:[],mode:'driving',currentDest:0},
  {id:'BN-005',company:'CargoCentral',driver:'David Fouda',status:'warning',temp:31.2,humidity:77,pressure:1007,shock:1,lat:5.5123,lng:10.3456,speed:45,route:'Bafoussam → Douala',progress:34,lastUpdate:'12:33:10',events:['WIND_ALERT'],securityOn:true,cargo:'Pharmaceutique',value:15800000,destinations:[],mode:'driving',currentDest:0},
  {id:'BN-006',company:'CargoCentral',driver:'Hervé Nkomo',status:'off',temp:null,humidity:null,pressure:null,shock:0,lat:5.4767,lng:10.4195,speed:0,route:'En stationnement',progress:0,lastUpdate:'08:12:00',events:[],securityOn:false,cargo:'Vide',value:0,destinations:[],mode:'driving',currentDest:0},
];
const EVENTS_LOG = [
  {id:'EVT001',container:'BN-003',type:'SHOCK_DETECTED',severity:'danger',msg:'Choc violent détecté — Accélération 8.2G',time:'12:35:01',lat:6.1234,lng:12.4567},
  {id:'EVT002',container:'BN-002',type:'TEMP_HIGH',severity:'warning',msg:'Température critique — 34.8°C (seuil: 32°C)',time:'12:33:55',lat:5.2012,lng:11.9456},
  {id:'EVT003',container:'BN-002',type:'HUM_HIGH',severity:'warning',msg:'Humidité élevée — 82% (seuil: 75%)',time:'12:33:55',lat:5.2012,lng:11.9456},
  {id:'EVT004',container:'BN-003',type:'VIBRATION_HIGH',severity:'danger',msg:'Vibrations anormales détectées',time:'12:34:50',lat:6.1234,lng:12.4567},
  {id:'EVT005',container:'BN-005',type:'WIND_ALERT',severity:'warning',msg:'Vent violent — 68 km/h (seuil: 60 km/h)',time:'12:30:22',lat:5.5123,lng:10.3456},
];
const CLIENTS = [
  {id:'C001',name:'Ibrahim Moussa',company:'TransAfrique SARL',container:'BN-001',cargo:'TV & Électro',phone:'+237 6 45 12 78 90',period:'transit',status:'active',value:850000,paid:true},
  {id:'C002',name:'Rose Tchouamba',company:'TransAfrique SARL',container:'BN-002',cargo:'Riz importé 5T',phone:'+237 6 78 23 45 67',period:'month',status:'active',value:320000,paid:true},
  {id:'C003',name:'Bello Adamou',company:'Sahel Logistics',container:'BN-004',cargo:'Pagnes brodés',phone:'+237 6 33 67 89 01',period:'transit',status:'active',value:180000,paid:false},
];

// ===== NAVIGATION CONFIG =====
const NAV = {
  superadmin:[
    {id:'dashboard',icon:'fa-solid fa-chart-pie',label:'Dashboard'},
    {id:'map',icon:'fa-solid fa-map-location-dot',label:'Monitoring'},
    {id:'containers',icon:'fa-solid fa-box',label:'Conteneurs'},
    {id:'sell',icon:'fa-solid fa-arrow-up-from-bracket',label:'Attribution'},
    {id:'companies',icon:'fa-solid fa-building',label:'Entreprises'},
    {id:'clients-sa',icon:'fa-solid fa-users',label:'Abonnés'},
    {id:'stats',icon:'fa-solid fa-chart-line',label:'Statistiques'},
    {id:'events',icon:'fa-solid fa-triangle-exclamation',label:'Événements'},
    {id:'blog',icon:'fa-solid fa-newspaper',label:'Publications'},
    {id:'settings',icon:'fa-solid fa-gear',label:'Paramètres'},
  ],
  owner:[
    {id:'dashboard',icon:'fa-solid fa-chart-pie',label:'Mon Dashboard'},
    {id:'map',icon:'fa-solid fa-map',label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',label:'Mes Conteneurs'},
    {id:'drivers',icon:'fa-solid fa-truck',label:'Chauffeurs'},
    {id:'subscribers',icon:'fa-solid fa-handshake',label:'Mes Abonnés'},
    {id:'clients-own',icon:'fa-solid fa-users',label:'Clients'},
    {id:'stats',icon:'fa-solid fa-chart-line',label:'Analytiques'},
    {id:'events',icon:'fa-solid fa-triangle-exclamation',label:'Alertes'},
    {id:'settings',icon:'fa-solid fa-gear',label:'Paramètres'},
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
  driver:[
    {id:'dashboard',icon:'fa-solid fa-chart-pie',label:'Ma Mission'},
    {id:'map',icon:'fa-solid fa-map',label:'Carte'},
    {id:'containers',icon:'fa-solid fa-box',label:'Mes Conteneurs'},
    {id:'events',icon:'fa-solid fa-triangle-exclamation',label:'Alertes'},
    {id:'settings',icon:'fa-solid fa-gear',label:'Paramètres'},
  ],
  client:[
    {id:'dashboard',icon:'fa-solid fa-chart-pie',label:'Mon Colis'},
    {id:'map',icon:'fa-solid fa-map',label:'Suivi'},
    {id:'containers',icon:'fa-solid fa-box',label:'Détails'},
    {id:'events',icon:'fa-solid fa-triangle-exclamation',label:'Événements'},
    {id:'settings',icon:'fa-solid fa-gear',label:'Paramètres'},
  ],
};
// ==== stockage de conversation dans localStorage pour persistance entre les pages ====

const aiState = {
  conversation: [],
  reportData: null,
  attachedImages: []
};

// ===== LOGIN =====
function doLogin(){
  currentRole = document.getElementById('login-role').value;
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  initApp();
}

// ===== APP INIT =====
function initApp(){
  const roleLabels={superadmin:'SUPER ADMIN',owner:'PROPRIÉTAIRE BB',company:'ENTREPRISE',driver:'CHAUFFEUR',client:'CLIENT'};
  const roleInit={superadmin:'SA',owner:'PB',company:'EN',driver:'CH',client:'CL'};
  document.getElementById('topbar-role-label').textContent = roleLabels[currentRole]||'';
  document.getElementById('user-avatar').textContent = roleInit[currentRole]||'?';
  buildNav();
  buildNotifications();
  startClock();
  navigateTo(NAV[currentRole][0].id);
  startSensorSimulation();
  startDestinationProximityCheck();
}

function buildNav(){
  const items = NAV[currentRole]||[];
  let html = '<div style="padding:20px 0">';
  items.forEach(item=>{
    html+=`<div class="nav-item" id="nav-${item.id}" onclick="navigateTo('${item.id}')"><span class="nav-icon"><i class="${item.icon}"></i></span><span class="nav-label">${item.label}</span></div>`;
  });
  html+='</div>';
  document.getElementById('nav-container').innerHTML = html;
}
function navigateTo(page){
  if(currentPage===page) return;
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));
  const navEl = document.getElementById('nav-'+page);
  if(navEl) navEl.classList.add('active');
  
  if(page === 'ai'){
    openAIAssistant();
    return;
  }
  currentPage = page;
  renderPage(page);
}
// function navigateTo(page){
//   if(currentPage===page) return;
//   document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));
//   const navEl = document.getElementById('nav-'+page);
//   if(navEl) navEl.classList.add('active');
//   currentPage = page;
//   renderPage(page);
// }

// ===== PAGES RENDERER =====
function renderPage(page){
  const c = document.getElementById('pages-container');
  switch(page){
    case 'dashboard': c.innerHTML = buildDashboard(); break;
    case 'map': c.innerHTML = buildMapPage(); break;
    case 'containers': c.innerHTML = buildContainersPage(); break;
    case 'sell': c.innerHTML = buildSellPage(); break;
    case 'companies': c.innerHTML = buildCompaniesPage(); break;
    case 'clients-sa': case 'clients-own': c.innerHTML = buildClientsPage(); break;
    case 'subscribers': c.innerHTML = buildSubscribersPage(); break;
    case 'drivers': c.innerHTML = buildDriversPage(); break;
    case 'stats': c.innerHTML = buildStatsPage(); break;
    case 'events': c.innerHTML = buildEventsPage(); break;
    case 'blog': c.innerHTML = buildBlogPage(); break;
    case 'settings': c.innerHTML = buildSettingsPage(); break;
    default: c.innerHTML = buildDashboard();
  }
  setTimeout(()=>initPageScripts(page), 50);
}

function initPageScripts(page){
  if(page==='dashboard' || page==='stats') initCharts(page) ; initMap('map-main', currentRole) ;
  if(page==='map') initMap('map-main', currentRole);
  if(page==='sell') initMap('map-sale', 'sell');
  if(page==='containers') {/* list init */}
}

// ===== DASHBOARD =====
function buildDashboard(){
  if(currentRole==='superadmin') return buildSADashboard();
  if(currentRole==='driver') return buildDriverDashboard();
  if(currentRole==='client') return buildClientDashboard();
  return buildOwnerDashboard();
}

function buildSADashboard(){
  return `
  <div class="page active" id="page-dashboard">
    <div class="page-header">
      <div class="page-title">Dashboard Global <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px">
        <span class="badge badge-ok"><span class="badge-dot"></span>Système Opérationnel</span>
        <button class="btn-icon" onclick="showToast('Actualisation en cours...','info')"><i class="fas fa-sync-alt"></i> Actualiser</button>
      </div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)">
        <div class="stat-label">Boîtes Actives</div>
        <div class="stat-value" id="stat-boxes">5</div>
        <div class="stat-trend up"><i class="fas fa-arrow-up"></i> +2 ce mois</div>
      </div>
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label">Entreprises Abonnées</div>
        <div class="stat-value" id="stat-companies">4</div>
        <div class="stat-trend up"><i class="fas fa-arrow-up"></i> +1 ce mois</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label">Alertes Actives</div>
        <div class="stat-value" id="stat-alerts">${EVENTS_LOG.length}</div>
        <div class="stat-trend down"><i class="fas fa-arrow-down"></i> 3 critiques</div>
      </div>
      <div class="stat-card" style="--accent:var(--purple)">
        <div class="stat-label">Recette Totale (CFA)</div>
        <div class="stat-value" style="font-size:20px">825K</div>
        <div class="stat-trend up"><i class="fas fa-arrow-up"></i> +12% vs mois dernier</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Carte Globale</span><button class="btn-icon" onclick="navigateTo('map')"><i class="fas fa-expand"></i> Plein écran</button></div>
        <div class="map-container" style="height:280px"><div id="map-main"></div></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Alertes Récentes</span><span class="badge badge-danger">${EVENTS_LOG.filter(e=>e.severity==='danger').length} Critiques</span></div>
        ${EVENTS_LOG.slice(0,5).map(e=>`
        <div class="timeline-item">
          <div class="timeline-dot" style="background:${e.severity==='danger'?'var(--red)':'var(--amber)'}"></div>
          <div class="timeline-content">
            <div class="timeline-text">${e.msg}</div>
            <div class="timeline-time">${e.container} • ${e.time}</div>
          </div>
        </div>`).join('')}
      </div>
    </div>
    <div class="grid-3" style="margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Statut Conteneurs</span></div>
        ${CONTAINERS.map(c=>`
        <div class="container-item status-${c.status}" style="margin-bottom:8px" onclick="showContainerDetail('${c.id}')">
          <div style="width:10px;height:10px;border-radius:50%;background:${c.status==='ok'?'var(--green)':c.status==='warning'?'var(--amber)':c.status==='danger'?'var(--red)':'var(--text3)'}"></div>
          <div class="container-info">
            <div class="container-id">${c.id}</div>
            <div class="container-meta">${c.route}</div>
          </div>
          <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}">${c.status.toUpperCase()}</span>
        </div>`).join('')}
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Revenus Mensuels</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-revenue"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Distribution Abonnements</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-subs"></canvas></div>
        <div class="legend" style="height:120px">
            <br>
            <h3>Légende</h3>
            <ul id="legend-list" style="margin-top:8px">
              <li id="legend-humidity"><span class="legend-color"  style="background:var(--cyan)"></span> <p style="font-size:14px">Humidité</p> </li>
              <li id="legend-wind"><span class="legend-color"  style="background:var(--green)"></span> <p style="font-size:14px">Vent</p> </li>
              <li id="legend-shocks"><span class="legend-color"  style="background:var(--amber)"></span> <p style="font-size:14px">Chocs</p> </li>
              <li id="legend-pressure"><span class="legend-color"  style="background:var(--purple)"></span> <p style="font-size:14px">Pression</p> </li>
              <li id="legend-temperature"><span class="legend-color"  style="background:var(--hello)"></span> <p style="font-size:14px">Température</p> </li>
            </ul>
        </div>
      </div>
    </div>
    <div style="margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Top Entreprises</span><button class="btn-icon" onclick="navigateTo('companies')">Voir tout</button></div>
        <div class="data-table-wrap">
          <table class="data-table">
            <thead><tr><th>Entreprise</th><th>Boîtes</th><th>Clients</th><th>Statut</th><th>Revenu</th><th>Action</th></tr></thead>
            <tbody>${COMPANIES.map(e=>`
            <tr>
              <td><div style="font-weight:600">${e.name}</div><div style="font-size:11px;color:var(--text3)">${e.location}</div></td>
              <td><span class="badge badge-info">${e.boxes} BB</span></td>
              <td>${e.clients}</td>
              <td><span class="badge badge-${e.status==='active'?'ok':'warn'}">${e.status}</span></td>
              <td style="font-family:var(--mono)">${e.revenue.toLocaleString()} CFA</td>
              <td><button class="btn-icon" onclick="showCompanyDetail('${e.id}')">Profil</button></td>
            </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>`;
}

function buildOwnerDashboard(){
  const myContainers = CONTAINERS.filter(c=>c.company===COMPANIES[0].name);
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Mon Dashboard <small>TransAfrique SARL</small></div>
      <span class="badge badge-ok"><span class="badge-dot"></span>3 Boîtes Actives</span>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label">Boîtes Actives</div>
        <div class="stat-value">3</div>
        <div class="stat-sub">sur 3 au total</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label">Alertes</div>
        <div class="stat-value">2</div>
        <div class="stat-trend down"><i class="fas fa-arrow-down"></i> 1 critique</div>
      </div>
      <div class="stat-card" style="--accent:var(--cyan)">
        <div class="stat-label">Clients Actifs</div>
        <div class="stat-value">12</div>
        <div class="stat-trend up"><i class="fas fa-arrow-up"></i> +3 ce mois</div>
      </div>
      <div class="stat-card" style="--accent:var(--purple)">
        <div class="stat-label">Valeur Cargos</div>
        <div class="stat-value" style="font-size:20px">24.5M</div>
        <div class="stat-sub">CFA en transit</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Carte Temps Réel</span></div>
        <div class="map-container" style="height:320px"><div id="map-main"></div></div>
      </div>
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><span class="card-title">Capteurs BN-001</span></div>
          <div class="sensor-grid">
            <div class="sensor-tile" style="--sensor-color:var(--cyan)">
              <div class="sensor-unit"><i class="fas fa-thermometer-half"></i></div>
              <div class="sensor-val" id="live-temp">${CONTAINERS[0].temp}</div>
              <div class="sensor-label">Temp</div>
            </div>
            <div class="sensor-tile" style="--sensor-color:var(--blue)">
              <div class="sensor-unit"><i class="fas fa-tint"></i></div>
              <div class="sensor-val" id="live-hum">${CONTAINERS[0].humidity}</div>
              <div class="sensor-label">Humidité</div>
            </div>
            <div class="sensor-tile" style="--sensor-color:var(--purple)">
              <div class="sensor-unit"><i class="fas fa-compress-arrows-alt"></i></div>
              <div class="sensor-val" id="live-press">${CONTAINERS[0].pressure}</div>
              <div class="sensor-label">Pression</div>
            </div>
            <div class="sensor-tile" style="--sensor-color:var(--green)">
              <div class="sensor-unit"><i class="fas fa-tachometer-alt"></i></div>
              <div class="sensor-val" id="live-speed">${CONTAINERS[0].speed}</div>
              <div class="sensor-label">Vitesse</div>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Sécurité</span></div>
          ${myContainers.map(c=>`
          <div class="security-toggle" style="margin-bottom:8px">
            <div style="flex:1">
              <div style="font-size:13px;font-weight:600">${c.id}</div>
              <div style="font-size:11px;color:var(--text3)">${c.securityOn?'<i class="fas fa-lock"></i> Mode Sécurisé ACTIF':'<i class="fas fa-unlock-alt"></i> Mode Sécurisé INACTIF'}</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" ${c.securityOn?'checked':''} onchange="toggleSecurity('${c.id}',this.checked)">
              <span class="toggle-slider"></span>
            </label>
          </div>`).join('')}
        </div>
      </div>
    </div>
    <div class="grid-2" style="margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Température (24h)</span></div>
        <div class="chart-wrap" style="height:180px"><canvas id="chart-temp"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Chocs & Vibrations</span></div>
        <div class="chart-wrap" style="height:180px"><canvas id="chart-shock"></canvas></div>
      </div>
    </div>
  </div>`;
}

function buildDriverDashboard(){
  const myC = CONTAINERS[0];
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Ma Mission <small>En Cours</small></div>
      <span class="badge badge-ok"><span class="badge-dot"></span>${myC.route}</span>
    </div>
    <div class="grid-2" style="margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Conteneur Assigné</span></div>
        <div style="text-align:center;padding:20px 0">
          <div style="font-family:var(--display);font-size:36px;color:var(--cyan)">${myC.id}</div>
          <div style="font-size:14px;color:var(--text2);margin:8px 0">${myC.cargo}</div>
          <div style="font-size:24px;font-weight:700;color:var(--green)">Valeur: ${myC.value.toLocaleString()} CFA</div>
        </div>
        <div style="margin-top:12px">
          <div style="font-size:12px;color:var(--text3);margin-bottom:6px">Progression du trajet</div>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${myC.progress}%;background:var(--cyan)"></div>
          </div>
          <div style="text-align:right;font-size:12px;color:var(--cyan);margin-top:4px">${myC.progress}%</div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Mode Sécurité</span></div>
        <div style="text-align:center;padding:24px">
          <div style="font-size:64px;margin-bottom:16px"><i class="fas ${myC.securityOn?'fa-lock':'fa-unlock-alt'}" style="color:${myC.securityOn?'var(--green)':'var(--red)'}"></i></div>
          <div style="font-size:16px;font-weight:600;color:${myC.securityOn?'var(--green)':'var(--red)'}">${myC.securityOn?'MODE SÉCURISÉ ACTIF':'MODE SÉCURISÉ INACTIF'}</div>
          <p style="font-size:12px;color:var(--text3);margin:12px 0">Activez le mode sécurité lors des arrêts</p>
          <label class="toggle-switch" style="display:inline-block">
            <input type="checkbox" ${myC.securityOn?'checked':''} onchange="toggleSecurity('${myC.id}',this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)">
        <div class="stat-label"><i class="fas fa-thermometer-half"></i> Température</div>
        <div class="stat-value" id="drv-temp">${myC.temp}°C</div>
        <div class="stat-sub">Seuil: 32°C</div>
      </div>
      <div class="stat-card" style="--accent:var(--blue)">
        <div class="stat-label"><i class="fas fa-tint"></i> Humidité</div>
        <div class="stat-value" id="drv-hum">${myC.humidity}%</div>
        <div class="stat-sub">Seuil: 75%</div>
      </div>
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label"><i class="fas fa-tachometer-alt"></i> Vitesse</div>
        <div class="stat-value" id="drv-speed">${myC.speed} km/h</div>
        <div class="stat-sub">Max: 80 km/h</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label"><i class="fas fa-wave-square"></i> Chocs</div>
        <div class="stat-value">${myC.shock}</div>
        <div class="stat-sub">Ce trajet</div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Position Actuelle</span></div>
      <div class="map-container" style="height:300px"><div id="map-main"></div></div>
    </div>
  </div>`;
}

function buildClientDashboard(){
  const c = CONTAINERS[0];
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Mon Colis <small>Suivi en temps réel</small></div>
    </div>
    <div class="alert alert-info"><i class="fas fa-info-circle"></i> Votre colis <strong>TV & Électronique</strong> est en transit sur le conteneur ${c.id}. Livraison estimée : 14h30.</div>
    <div class="grid-2" style="margin-bottom:20px">
      <div class="card">
        <div class="card-header"><span class="card-title">Suivi GPS</span></div>
        <div class="map-container" style="height:280px"><div id="map-main"></div></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">État du Conteneur</span></div>
        <div class="sensor-grid" style="margin-bottom:16px">
          <div class="sensor-tile" style="--sensor-color:var(--green)">
            <div class="sensor-unit"><i class="fas fa-thermometer-half"></i></div>
            <div class="sensor-val">${c.temp}</div>
            <div class="sensor-label">Temp</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:var(--blue)">
            <div class="sensor-unit"><i class="fas fa-tint"></i></div>
            <div class="sensor-val">${c.humidity}</div>
            <div class="sensor-label">Humidité</div>
          </div>
        </div>
        <div class="stat-label" style="margin-bottom:6px">Progression</div>
        <div class="progress-bar">
          <div class="progress-fill" style="width:${c.progress}%;background:var(--green)"></div>
        </div>
        <div style="text-align:right;font-size:12px;color:var(--green);margin-top:4px">${c.progress}% — ${c.route}</div>
        <div style="margin-top:16px">
          <div class="badge badge-ok"><span class="badge-dot"></span>Marchandise en bon état</div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Historique des Événements</span></div>
      <div class="timeline-item">
        <div class="timeline-dot" style="background:var(--green)"></div>
        <div class="timeline-content"><div class="timeline-text">Conteneur chargé et scellé</div><div class="timeline-time">Aujourd'hui 08:15:00</div></div>
      </div>
      <div class="timeline-item">
        <div class="timeline-dot" style="background:var(--cyan)"></div>
        <div class="timeline-content"><div class="timeline-text">Départ de Douala — Mode sécurité activé</div><div class="timeline-time">Aujourd'hui 09:30:00</div></div>
      </div>
      <div class="timeline-item">
        <div class="timeline-dot" style="background:var(--cyan)"></div>
        <div class="timeline-content"><div class="timeline-text">Passage checkpoint km 145 — Tout normal</div><div class="timeline-time">Aujourd'hui 11:45:00</div></div>
      </div>
      <div class="timeline-item">
        <div class="timeline-dot" style="background:var(--cyan)"></div>
        <div class="timeline-content"><div class="timeline-text">En transit — Vitesse: ${c.speed} km/h</div><div class="timeline-time">Aujourd'hui ${c.lastUpdate}</div></div>
      </div>
    </div>
  </div>`;
}

// ===== MAP PAGE =====
function buildMapPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Carte Monitoring <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <span class="badge badge-ok"><span class="badge-dot"></span>${CONTAINERS.filter(c=>c.status==='ok').length} OK</span>
        <span class="badge badge-warn">${CONTAINERS.filter(c=>c.status==='warning').length} Alertes</span>
        <span class="badge badge-danger">${CONTAINERS.filter(c=>c.status==='danger').length} Critiques</span>
        <span class="badge badge-off">${CONTAINERS.filter(c=>c.status==='off').length} Hors ligne</span>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 280px;gap:16px;height:calc(100vh - 160px)">
      <div class="card" style="padding:0;overflow:hidden">
        <div class="map-container" style="height:100%;position:relative">
          <div id="map-main" style="height:100%"></div>
          <div class="map-overlay">
            <div class="map-legend">
              <div style="font-size:11px;font-weight:600;color:var(--text);margin-bottom:6px;letter-spacing:1px">LÉGENDE</div>
              <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Nominal</div>
              <div class="legend-item"><div class="legend-dot" style="background:var(--amber)"></div>Alerte</div>
              <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>Critique</div>
              <div class="legend-item"><div class="legend-dot" style="background:var(--text3)"></div>Hors ligne</div>
            </div>
          </div>
          <div class="map-controls">
            <button class="map-btn" onclick="showAllContainers()" title="Vue globale"><i class="fas fa-globe"></i></button>
            <button class="map-btn" onclick="toggleMapLayer()" title="Changer fond"><i class="fas fa-layer-group"></i></button>
            <button class="map-btn" onclick="toggleTrails()" title="Traces GPS"><i class="fas fa-route"></i></button>
            <button class="map-btn" onclick="toggleHeatmap()" title="Heatmap alertes"><i class="fas fa-fire"></i></button>
          </div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;overflow-y:auto">
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:10px">Conteneurs</div>
          <div style="position:relative; margin-bottom:10px">
            <i class="fas fa-search" style="position:absolute; left:10px; top:8px; color:var(--text3); font-size:12px;"></i>
            <input type="text" placeholder="Rechercher..." style="width:100%;padding-left:28px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:12px;outline:none;" oninput="filterContainersList(this.value)">
          </div>
          <div id="containers-sidebar-list">
            ${CONTAINERS.map(c=>`
            <div class="container-item status-${c.status}" style="margin-bottom:6px;cursor:pointer" onclick="focusContainer('${c.id}')">
              <div style="width:8px;height:8px;border-radius:50%;background:${c.status==='ok'?'var(--green)':c.status==='warning'?'var(--amber)':c.status==='danger'?'var(--red)':'var(--text3)'}"></div>
              <div class="container-info" style="min-width:0">
                <div class="container-id" style="font-size:12px">${c.id}</div>
                <div class="container-meta" style="font-size:10px">${c.route}</div>
                <div style="font-size:10px;color:var(--text3)">${c.speed} km/h • ${c.lastUpdate}</div>
              </div>
            </div>`).join('')}
          </div>
        </div>
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:10px">Données Live</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div class="sensor-tile" style="--sensor-color:var(--cyan);padding:10px">
              <div class="sensor-unit" style="font-size:10px"><i class="fas fa-thermometer-half"></i></div>
              <div class="sensor-val" style="font-size:20px" id="map-temp">${CONTAINERS[0].temp}</div>
              <div class="sensor-label" style="font-size:10px">Temp BN-001</div>
            </div>
            <div class="sensor-tile" style="--sensor-color:var(--amber);padding:10px">
              <div class="sensor-unit" style="font-size:10px"><i class="fas fa-wave-square"></i></div>
              <div class="sensor-val" style="font-size:20px" id="map-shock">${CONTAINERS[2].shock}</div>
              <div class="sensor-label" style="font-size:10px">Choc BN-003</div>
            </div>
          </div>
        </div>
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:10px">Alertes Actives</div>
          ${EVENTS_LOG.map(e=>`
          <div class="timeline-item" style="padding:6px 0">
            <div class="timeline-dot" style="background:${e.severity==='danger'?'var(--red)':'var(--amber)'}"></div>
            <div class="timeline-content">
              <div class="timeline-text" style="font-size:11px">${e.container} — ${e.type}</div>
              <div class="timeline-time">${e.time}</div>
            </div>
          </div>`).join('')}
        </div>
      </div>
    </div>
  </div>`;
}

// ===== CONTAINERS PAGE =====
function buildContainersPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Conteneurs <small>${CONTAINERS.length} Total</small></div>
      <div style="display:flex;gap:8px">
        <div style="position:relative; width:200px">
          <i class="fas fa-search" style="position:absolute; left:12px; top:8px; color:var(--text3); font-size:12px;"></i>
          <input type="text" placeholder="Rechercher..." id="container-search" style="padding-left:28px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;padding:6px 14px;color:var(--text);font-size:13px;outline:none;width:100%" oninput="filterContainers(this.value)">
        </div>
        ${currentRole==='owner'?'<button class="btn-icon" onclick="showModal(\'addContainer\')"><i class="fas fa-plus"></i> Ajouter</button>':''}
      </div>
    </div>
    <div class="tabs" id="cont-tabs">
      <div class="tab active" onclick="filterContainersStatus('all',this)">Tous (${CONTAINERS.length})</div>
      <div class="tab" onclick="filterContainersStatus('ok',this)"><i class="fas fa-check-circle" style="color:var(--green)"></i> Nominal (${CONTAINERS.filter(c=>c.status==='ok').length})</div>
      <div class="tab" onclick="filterContainersStatus('warning',this)"><i class="fas fa-exclamation-triangle" style="color:var(--amber)"></i> Alerte (${CONTAINERS.filter(c=>c.status==='warning').length})</div>
      <div class="tab" onclick="filterContainersStatus('danger',this)"><i class="fas fa-circle" style="color:var(--red); font-size: 8px;"></i> Critique (${CONTAINERS.filter(c=>c.status==='danger').length})</div>
      <div class="tab" onclick="filterContainersStatus('off',this)"><i class="fas fa-power-off" style="color:var(--text3)"></i> Hors ligne (${CONTAINERS.filter(c=>c.status==='off').length})</div>
    </div>
    <div id="containers-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px">
      ${CONTAINERS.map(c=>buildContainerCard(c)).join('')}
    </div>
  </div>`;
}

function buildContainerCard(c){
  const statusColors={ok:'var(--green)',warning:'var(--amber)',danger:'var(--red)',off:'var(--text3)',sleep:'#4a90e2',down:'var(--text3)'};
  const col = statusColors[c.status]||'var(--text3)';
  return `
  <div class="card container-item status-${c.status}" style="display:block;cursor:pointer" onclick="showContainerDetail('${c.id}')">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:8px">
        <div style="width:10px;height:10px;border-radius:50%;background:${col};${c.status!=='off'?'box-shadow:0 0 8px '+col:''}"></div>
        <span style="font-family:var(--display);font-size:16px;color:var(--cyan)">${c.id}</span>
      </div>
      <div style="display:flex;gap:6px">
        <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':c.status==='sleep'?'info':'off'}">${c.status.toUpperCase()}</span>
        ${c.securityOn?'<span class="badge badge-info"><i class="fas fa-lock"></i> Sécurisé</span>':'<span class="badge badge-off"><i class="fas fa-unlock-alt"></i> Non sécurisé</span>'}
      </div>
    </div>
    <div style="font-size:13px;color:var(--text2);margin-bottom:8px"><i class="fas fa-map-marker-alt"></i> ${c.route}</div>
    <div style="font-size:12px;color:var(--text3);margin-bottom:12px"><i class="fas fa-building"></i> ${c.company} • <i class="fas fa-truck"></i> ${c.driver}</div>
    ${c.status!=='off'?`
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px">
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:${c.temp>32?'var(--red)':c.temp>28?'var(--amber)':'var(--green)'}">${c.temp}</div>
        <div style="font-size:10px;color:var(--text3)"><i class="fas fa-thermometer-half"></i> °C</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:${c.humidity>75?'var(--red)':c.humidity>65?'var(--amber)':'var(--green)'}">${c.humidity}</div>
        <div style="font-size:10px;color:var(--text3)"><i class="fas fa-tint"></i> %</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:var(--text)">${c.speed}</div>
        <div style="font-size:10px;color:var(--text3)"><i class="fas fa-tachometer-alt"></i> km/h</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:16px;font-weight:700;font-family:var(--mono);color:${c.shock>5?'var(--red)':c.shock>0?'var(--amber)':'var(--green)'}">${c.shock}</div>
        <div style="font-size:10px;color:var(--text3)"><i class="fas fa-wave-square"></i> G</div>
      </div>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" style="width:${c.progress}%;background:${col}"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text3);margin-top:4px">
      <span>${c.progress}%</span><span>Mis à jour: ${c.lastUpdate}</span>
    </div>`:
    '<div style="text-align:center;padding:16px;color:var(--text3)"><i class="fas fa-power-off"></i> Boîte hors ligne — Dernière sync: '+c.lastUpdate+'</div>'}
    ${c.events.length>0?`<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">${c.events.map(e=>`<span class="badge badge-warn"><i class="fas fa-exclamation-triangle"></i> ${e}</span>`).join('')}</div>`:''}
    <div style="margin-top:10px;display:flex;gap:8px">
      <button class="btn-icon" style="font-size:12px;padding:4px 10px" onclick="event.stopPropagation(); viderContainer('${c.id}')"><i class="fas fa-dumpster"></i> Vider</button>
      <button class="btn-icon" style="font-size:12px;padding:4px 10px" onclick="event.stopPropagation(); continuerContainer('${c.id}')"><i class="fas fa-forward"></i> Continuer</button>
    </div>
  </div>`;
}

// ===== SELL PAGE (modifiée avec type conteneur, calculs) =====
function buildSellPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Ventes & Attribution <small>Boîtes Noires</small></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><span class="card-title">Nouvelle Vente / Attribution</span></div>
          <div class="form-row">
            <div class="form-field">
              <label>Nombre de Boîtes</label>
              <input type="number" min="1" placeholder="1" id="sell-qty">
            </div>
            <div class="form-field">
              <label>Nom de l'Entreprise</label>
              <input type="text" placeholder="Nom entreprise" id="sell-company">
            </div>
          </div>
          <div class="form-row">
            <div class="form-field">
              <label>Localisation</label>
              <input type="text" placeholder="Ville, Pays" id="sell-location">
            </div>
            <div class="form-field">
              <label>Téléphone</label>
              <input type="text" placeholder="+237 6..." id="sell-phone">
            </div>
          </div>
          <div class="form-row">
            <div class="form-field">
              <label>Email</label>
              <input type="email" placeholder="contact@entreprise.cm" id="sell-email">
            </div>
            <div class="form-field">
              <label>Type d'Abonnement</label>
              <select id="sell-sub">
                <option value="monthly">Mensuel — 15 000 CFA/BB</option>
                <option value="yearly">Annuel — 150 000 CFA/BB</option>
                <option value="custom">Personnalisé</option>
              </select>
            </div>
          </div>
          <!-- Nouveau bloc Type de Conteneur -->
          <div class="form-field" style="margin-bottom:16px">
            <label>Type de Conteneur <small>(pour agences sans moyen de transport)</small></label>
            <select id="container-type" onchange="handleContainerTypeChange()">
              <option value="">-- Sélectionner --</option>
              <option value="DRY">DRY</option>
              <option value="HighCube">High Cube</option>
              <option value="Refrigere">Réfrigéré</option>
              <option value="OpenTop">Open Top</option>
            </select>
            <small id="open-top-note" style="display:none;color:var(--amber);margin-top:4px;">Ces conteneurs sont dépourvus de toit.</small>
          </div>
          <div id="container-volume-section" style="display:none;">
            <div class="form-row">
              <div class="form-field">
                <label>Volume (m³)</label>
                <input type="number" id="container-volume" placeholder="Volume en m³" oninput="calcPerimeter()">
              </div>
              <div class="form-field">
                <label>Périmètre (m) - calculé</label>
                <input type="text" id="container-perimeter" readonly>
              </div>
            </div>
            <div class="form-field" id="pouce-field" style="display:none;">
              <label>Valeur en pouces</label>
              <input type="text" id="container-pouce" placeholder="ex: 20' ou 40'">
            </div>
          </div>
          <!-- Fin bloc conteneur -->
          <div class="form-field" style="margin-bottom:16px">
            <label>Photo CNI (Acheteur)</label>
            <div class="upload-zone" onclick="document.getElementById('cni-upload').click()">
              <div class="upload-icon"><i class="fas fa-id-card"></i></div>
              <div class="upload-text">Cliquer pour charger la photo CNI</div>
            </div>
            <input type="file" id="cni-upload" accept="image/*" style="display:none" onchange="previewFile(this,'cni-preview')">
            <div id="cni-preview"></div>
          </div>
          <div class="form-field" style="margin-bottom:16px">
            <label>Inventaire / Documents</label>
            <div class="upload-zone" onclick="document.getElementById('inv-upload').click()">
              <div class="upload-icon"><i class="fas fa-camera"></i></div>
              <div class="upload-text">Photos inventaire / documents</div>
            </div>
            <input type="file" id="inv-upload" accept="image/*,application/pdf" style="display:none">
          </div>
          <button class="btn-primary" onclick="submitSale()"><i class="fas fa-check"></i> Valider la Vente & Créer le Compte</button>
        </div>
      </div>
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><span class="card-title"><i class="fas fa-map-marker-alt"></i> Position Précise du Client</span></div>
          <p style="font-size:12px;color:var(--text3);margin-bottom:10px">Cliquez sur la carte pour marquer l'emplacement exact</p>
          <div class="map-container" style="height:300px"><div id="map-sale"></div></div>
          <div id="map-sale-coords" style="font-size:12px;color:var(--cyan);font-family:var(--mono);margin-top:8px;padding:6px;background:var(--bg3);border-radius:var(--radius)">Cliquez sur la carte pour obtenir les coordonnées...</div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Résumé Vente</span></div>
          <div id="sale-summary">
            <div style="text-align:center;padding:20px;color:var(--text3)">Remplissez le formulaire pour voir le résumé</div>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

// ===== COMPANIES PAGE =====
function buildCompaniesPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Gestion Entreprises</div>
      <div style="position:relative; width:220px">
        <i class="fas fa-search" style="position:absolute; left:12px; top:8px; color:var(--text3); font-size:12px;"></i>
        <input type="text" placeholder="Rechercher..." style="padding-left:28px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;padding:6px 14px;color:var(--text);font-size:13px;outline:none;width:100%">
      </div>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="setTab(this,'comp-tab','all')">Propriétaires BB (${COMPANIES.filter(c=>c.sub==='owner').length})</div>
      <div class="tab" onclick="setTab(this,'comp-tab','subscriber')">Abonnés (${COMPANIES.filter(c=>c.sub==='subscriber').length})</div>
      <div class="tab" onclick="setTab(this,'comp-tab','client')">Clients Finaux (${CLIENTS.length})</div>
    </div>
    <div class="data-table-wrap">
      <table class="data-table">
        <thead><tr><th>Entreprise</th><th>Contact</th><th>Localisation</th><th>Boîtes</th><th>Clients</th><th>Statut</th><th>Revenu</th><th>Actions</th></tr></thead>
        <tbody id="companies-tbody">
          ${COMPANIES.map(e=>`<tr>
            <td>
              <div style="font-weight:600">${e.name}</div>
              <div style="font-size:11px;color:var(--text3)">ID: ${e.id} • Depuis ${e.joined}</div>
            </td>
            <td>
              <div style="font-size:13px">${e.contact}</div>
              <div style="font-size:11px;color:var(--text3)">${e.phone}</div>
            </td>
            <td>${e.location}</td>
            <td>${e.boxes>0?'<span class="badge badge-info">'+e.boxes+' BB</span>':'<span class="badge badge-off">0</span>'}</td>
            <td>${e.clients}</td>
            <td><span class="badge badge-${e.status==='active'?'ok':'warn'}">${e.status}</span></td>
            <td style="font-family:var(--mono);font-size:14px">${e.revenue.toLocaleString()} CFA</td>
            <td>
              <div style="display:flex;gap:6px">
                <button class="btn-icon" onclick="showCompanyDetail('${e.id}')">Profil</button>
                <button class="btn-icon" onclick="showModal('editSub','${e.id}')">Abonnement</button>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

// ===== CLIENTS PAGE (modifiée avec assignation auto) =====
function buildClientsPage(){
  const isOwner = currentRole==='owner'||currentRole==='company';
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">${isOwner?'Gestion Clients':'Abonnés'}</div>
      <button class="btn-icon" onclick="showModal('addClient')"><i class="fas fa-plus"></i> Nouveau Client</button>
    </div>
    <div class="grid-3" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)">
        <div class="stat-label">Total Clients</div>
        <div class="stat-value">${CLIENTS.length}</div>
      </div>
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label">Abonnements Actifs</div>
        <div class="stat-value">${CLIENTS.filter(c=>c.status==='active').length}</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label">Paiements En Attente</div>
        <div class="stat-value">${CLIENTS.filter(c=>!c.paid).length}</div>
      </div>
    </div>
    <div class="card">
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Client</th><th>Conteneur</th><th>Colis</th><th>Valeur</th><th>Période</th><th>Statut</th><th>Paiement</th><th>Action</th></tr></thead>
          <tbody>
            ${CLIENTS.map(c=>`<tr>
              <td>
                <div style="font-weight:600">${c.name}</div>
                <div style="font-size:12px;color:var(--text3)">${c.phone}</div>
              </td>
              <td><span class="badge badge-info">${c.container}</span></td>
              <td>${c.cargo}</td>
              <td style="font-family:var(--mono);font-size:14px">${c.value.toLocaleString()} CFA</td>
              <td><span class="tag">${c.period==='transit'?'Transit':c.period==='month'?'1 Mois':'1 An'}</span></td>
              <td><span class="badge badge-${c.status==='active'?'ok':'off'}">${c.status}</span></td>
              <td><span class="badge badge-${c.paid?'ok':'danger'}">${c.paid?'<i class="fas fa-check"></i> Payé':'<i class="fas fa-clock"></i> En attente'}</span></td>
              <td><button class="btn-icon">Profil</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">Ajouter un Abonnement Client</span></div>
      <div class="form-row">
        <div class="form-field"><label>Nom</label><input type="text" placeholder="Nom du client" id="new-client-name"></div>
        <div class="form-field"><label>Prénom</label><input type="text" placeholder="Prénom" id="new-client-firstname"></div>
        <div class="form-field"><label>Téléphone</label><input type="text" placeholder="+237..." id="new-client-phone"></div>
        <div class="form-field"><label>Email</label><input type="email" placeholder="client@mail.com" id="new-client-email"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Type de Colis</label><input type="text" placeholder="Électronique, Alimentaire..." id="new-client-cargo-type"></div>
        <div class="form-field"><label>Nom du Colis</label><input type="text" placeholder="Description détaillée" id="new-client-cargo-name"></div>
        <div class="form-field"><label>Valeur (CFA)</label><input type="number" placeholder="0" id="new-client-value"></div>
        <div class="form-field"><label>Destination</label><input type="text" placeholder="Ville destination" id="new-client-dest"></div>
      </div>
      <div class="form-row">
        <div class="form-field">
          <label>Période</label>
          <select id="new-client-period" onchange="calcSubPrice(this)">
            <option value="transit">Durée du Transit (Prix unique)</option>
            <option value="month">Ce mois uniquement</option>
            <option value="year">Cette année</option>
          </select>
        </div>
        <div class="form-field"><label>Prix Abonnement</label><input type="text" id="sub-price-calc" value="5 000 CFA" readonly style="color:var(--cyan);font-weight:600"></div>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Photo CNI Client</label>
        <div class="upload-zone" onclick="document.getElementById('client-cni').click()">
          <div class="upload-icon"><i class="fas fa-id-card"></i></div>
          <div class="upload-text">Photo CNI</div>
        </div>
        <input type="file" id="client-cni" accept="image/*" style="display:none">
      </div>
      <button class="btn-primary" onclick="addNewClient()"><i class="fas fa-check"></i> Créer le Compte Client</button>
    </div>
  </div>`;
}

// ===== SUBSCRIBERS PAGE =====
function buildSubscribersPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Mes Abonnés <small>Entreprises</small></div>
      <button class="btn-icon" onclick="showModal('addSubscriber')"><i class="fas fa-plus"></i> Nouvel Abonné</button>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">Ajouter une Entreprise Abonnée</span></div>
      <div class="form-row">
        <div class="form-field"><label>Nom Entreprise</label><input type="text" placeholder="Nom entreprise"></div>
        <div class="form-field"><label>Lieu de Résidence</label><input type="text" placeholder="Ville, Pays"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Nombre de Colis</label><input type="number" placeholder="1"></div>
        <div class="form-field"><label>Valeur Marchandise (CFA)</label><input type="number" placeholder="0"></div>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Photos Inventaire</label>
        <div class="upload-zone" onclick="document.getElementById('inv-sub').click()">
          <div class="upload-icon"><i class="fas fa-camera"></i></div>
          <div class="upload-text">Photos de l'inventaire / marchandise</div>
        </div>
        <input type="file" id="inv-sub" accept="image/*" multiple style="display:none">
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Sélectionner la Période</label>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
          <div class="sub-card selected" onclick="selectPeriod(this,'transit')">
            <div style="font-size:24px;margin-bottom:8px"><i class="fas fa-truck"></i></div>
            <div style="font-weight:600;font-size:13px">Transit</div>
            <div class="sub-price">8 000</div>
            <div class="sub-period">CFA — Durée trajet</div>
          </div>
          <div class="sub-card" onclick="selectPeriod(this,'month')">
            <div style="font-size:24px;margin-bottom:8px"><i class="fas fa-calendar-alt"></i></div>
            <div style="font-weight:600;font-size:13px">Mensuel</div>
            <div class="sub-price">25 000</div>
            <div class="sub-period">CFA / mois</div>
          </div>
          <div class="sub-card" onclick="selectPeriod(this,'year')">
            <div style="font-size:24px;margin-bottom:8px"><i class="fas fa-calendar-check"></i></div>
            <div style="font-weight:600;font-size:13px">Annuel</div>
            <div class="sub-price">240 000</div>
            <div class="sub-period">CFA / an</div>
          </div>
        </div>
      </div>
      <button class="btn-primary" onclick="showToast('Abonné ajouté avec succès!','success')"><i class="fas fa-check"></i> Créer l'Abonnement</button>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Abonnés Actuels</span></div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">
        ${COMPANIES.filter(c=>c.sub==='subscriber').map(e=>`
        <div class="card" style="background:var(--card2)">
          <div style="font-weight:600;margin-bottom:6px">${e.name}</div>
          <div style="font-size:12px;color:var(--text3);margin-bottom:10px"><i class="fas fa-map-marker-alt"></i> ${e.location} • ${e.clients} clients</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="badge badge-ok">Actif</span>
            <div style="display:flex;gap:6px">
              <button class="btn-icon" style="padding:4px 8px;font-size:12px" onclick="showToast('Abonnement prolongé','success')"><i class="fas fa-plus"></i> Période</button>
              <button class="btn-icon" style="padding:4px 8px;font-size:12px;color:var(--red)" onclick="showToast('Abonnement annulé','info')"><i class="fas fa-times"></i> Annuler</button>
            </div>
          </div>
        </div>`).join('')}
      </div>
    </div>
  </div>`;
}

// ===== DRIVERS PAGE =====
function buildDriversPage(){
  const drivers = CONTAINERS.map(c=>({name:c.driver,container:c.id,status:c.status,speed:c.speed,route:c.route}));
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Chauffeurs <small>${drivers.length} Enregistrés</small></div>
      <button class="btn-icon" onclick="showModal('addDriver')"><i class="fas fa-plus"></i> Nouveau Chauffeur</button>
    </div>
    <div class="data-table-wrap card">
      <table class="data-table">
        <thead><tr><th>Chauffeur</th><th>Conteneur</th><th>Statut</th><th>Vitesse</th><th>Sécurité</th><th>Actions</th></tr></thead>
        <tbody>
          ${CONTAINERS.map(c=>`<tr>
            <td><div style="font-weight:600">${c.driver}</div></td>
            <td><span class="badge badge-info">${c.id}</span></td>
            <td><span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}">${c.status}</span></td>
            <td style="font-family:var(--mono)">${c.speed} km/h</td>
            <td><span class="badge badge-${c.securityOn?'ok':'danger'}"><i class="fas ${c.securityOn?'fa-lock':'fa-unlock-alt'}"></i> ${c.securityOn?'ON':'OFF'}</span></td>
            <td>
              <div style="display:flex;gap:6px">
                <button class="btn-icon" onclick="showToast('Message envoyé au chauffeur','info')"><i class="fas fa-envelope"></i> Message</button>
                <button class="btn-icon" onclick="navigateTo('containers')">Détails</button>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

// ===== STATS PAGE =====
function buildStatsPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Statistiques & Analytiques <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px">
        <select style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option>7 derniers jours</option>
          <option>30 derniers jours</option>
          <option>3 derniers mois</option>
        </select>
        <button class="export-btn" onclick="showToast('Export PDF en cours...','info')"><i class="fas fa-file-pdf"></i> Exporter Rapport</button>
      </div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)">
        <div class="stat-label">Temp. Moy</div>
        <div class="stat-value">26.8°C</div>
        <div class="stat-sub">Tous conteneurs</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label">Alertes (7j)</div>
        <div class="stat-value">18</div>
        <div class="stat-trend down"><i class="fas fa-arrow-down"></i> -3 vs semaine dernière</div>
      </div>
      <div class="stat-card" style="--accent:var(--red)">
        <div class="stat-label">Chocs Détectés</div>
        <div class="stat-value">10</div>
        <div class="stat-sub">Cette semaine</div>
      </div>
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label">Taux Fiabilité</div>
        <div class="stat-value">94%</div>
        <div class="stat-trend up"><i class="fas fa-arrow-up"></i> +2% vs mois</div>
      </div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card">
        <div class="card-header"><span class="card-title">Température — 24h (Live)</span><span class="badge badge-info"><i class="fas fa-circle" style="font-size:8px;color:var(--green)"></i> Live</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-temp"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Humidité — 24h</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-hum"></canvas></div>
      </div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card">
        <div class="card-header"><span class="card-title">Chocs & Vibrations</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-shock"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Pression Atmosphérique</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-press"></canvas></div>
      </div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card">
        <div class="card-header"><span class="card-title">Revenus Mensuels</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-revenue"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Répartition des Alertes</span></div>
        <div class="chart-wrap" style="height:220px"><canvas id="chart-subs"></canvas></div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Vitesse des Conteneurs — Temps Réel</span><button class="export-btn" onclick="showToast('Export CSV','info')"><i class="fas fa-file-csv"></i> CSV</button></div>
      <div class="chart-wrap" style="height:180px"><canvas id="chart-speed"></canvas></div>
    </div>
  </div>`;
}

// ===== EVENTS PAGE =====
function buildEventsPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Événements & Alertes</div>
      <div style="display:flex;gap:8px">
        <select style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option>Tous les niveaux</option>
          <option>Critique seulement</option>
          <option>Avertissement</option>
        </select>
        <button class="export-btn" onclick="showToast('Export rapport','info')"><i class="fas fa-file-alt"></i> Rapport</button>
      </div>
    </div>
    <div class="grid-3" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--red)">
        <div class="stat-label">Critiques</div>
        <div class="stat-value">${EVENTS_LOG.filter(e=>e.severity==='danger').length}</div>
      </div>
      <div class="stat-card" style="--accent:var(--amber)">
        <div class="stat-label">Avertissements</div>
        <div class="stat-value">${EVENTS_LOG.filter(e=>e.severity==='warning').length}</div>
      </div>
      <div class="stat-card" style="--accent:var(--green)">
        <div class="stat-label">Résolus (24h)</div>
        <div class="stat-value">3</div>
      </div>
    </div>
    <div class="card">
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Heure</th><th>Conteneur</th><th>Type</th><th>Sévérité</th><th>Message</th><th>Action</th></tr></thead>
          <tbody>
            ${EVENTS_LOG.map(e=>`<tr>
              <td style="font-family:var(--mono);font-size:14px">${e.time}</td>
              <td><span class="badge badge-info">${e.container}</span></td>
              <td><span class="tag">${e.type}</span></td>
              <td><span class="badge badge-${e.severity==='danger'?'danger':'warn'}">${e.severity.toUpperCase()}</span></td>
              <td style="font-size:14px">${e.msg}</td>
              <td>
                <div style="display:flex;gap:6px">
                  <button class="btn-icon" onclick="showContainerDetail('${e.container}')">Voir</button>
                  <button class="btn-icon" onclick="showToast('Événement acquitté','success')"><i class="fas fa-check"></i> Ack</button>
                </div>
              </td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">Configuration Seuils d'Alerte</span></div>
      <div class="form-row">
        <div class="form-field"><label>Température Max (°C)</label><input type="number" value="32"></div>
        <div class="form-field"><label>Humidité Max (%)</label><input type="number" value="75"></div>
        <div class="form-field"><label>Choc Max (G)</label><input type="number" value="5"></div>
        <div class="form-field"><label>Vent Max (km/h)</label><input type="number" value="60"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Pression Min (hPa)</label><input type="number" value="995"></div>
        <div class="form-field"><label>Vitesse Max (km/h)</label><input type="number" value="90"></div>
        <div class="form-field"><label>Angle Inclinaison (°)</label><input type="number" value="30"></div>
        <div class="form-field"><label>Notification</label>
          <select><option>SMS + Email + App</option><option>App seulement</option><option>Email seulement</option></select>
        </div>
      </div>
      <button class="btn-primary" onclick="showToast('Seuils mis à jour','success')"><i class="fas fa-save"></i> Sauvegarder les Seuils</button>
    </div>
  </div>`;
}

// ===== BLOG PAGE =====
function buildBlogPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Publications & Annonces</div>
      <button class="btn-icon" onclick="showModal('newPost')"><i class="fas fa-plus"></i> Nouvelle Publication</button>
    </div>
    <div class="grid-2" style="margin-bottom:16px">
      <div class="card" style="border-left:3px solid var(--red)">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span class="badge badge-danger"><i class="fas fa-exclamation-circle"></i> URGENT</span>
          <span style="font-size:11px;color:var(--text3)">Il y a 2 heures</span>
        </div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px">Alerte Météo: Vents Violents Prévus</div>
        <p style="font-size:13px;color:var(--text2)">Des vents de 70-80 km/h sont attendus sur l'axe Yaoundé-Bafoussam. Renforcez les mesures de sécurité sur les conteneurs BN-002 et BN-005.</p>
        <div style="margin-top:10px;font-size:12px;color:var(--text3)">Destinataires: Tous les utilisateurs • Visible par: Toutes les entreprises</div>
      </div>
      <div class="card" style="border-left:3px solid var(--cyan)">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span class="badge badge-info"><i class="fas fa-info-circle"></i> INFO</span>
          <span style="font-size:11px;color:var(--text3)">Hier</span>
        </div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px">Mise à Jour Plateforme v2.4</div>
        <p style="font-size:13px;color:var(--text2)">Nouvelles fonctionnalités: Détection de chocs améliorée, rapport PDF automatique, alertes WhatsApp.</p>
        <div style="margin-top:10px;font-size:12px;color:var(--text3)">Destinataires: Tous les utilisateurs</div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Rédiger une Publication</span></div>
      <div class="form-row">
        <div class="form-field"><label>Titre</label><input type="text" placeholder="Titre de la publication"></div>
        <div class="form-field"><label>Niveau</label>
          <select><option>Information</option><option>Avertissement</option><option>Urgent</option></select>
        </div>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Contenu</label>
        <textarea rows="4" placeholder="Contenu du message..."></textarea>
      </div>
      <div class="form-field" style="margin-bottom:16px">
        <label>Destinataires</label>
        <select>
          <option>Tous les utilisateurs</option>
          <option>Propriétaires BB seulement</option>
          <option>Chauffeurs seulement</option>
          <option>Entreprise spécifique</option>
        </select>
      </div>
      <button class="btn-primary" onclick="showToast('Publication envoyée à tous les utilisateurs','success')"><i class="fas fa-bullhorn"></i> Publier & Notifier</button>
    </div>
  </div>`;
}

// ===== SETTINGS PAGE =====
function buildSettingsPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Paramètres <small>Configuration</small></div>
      <button class="btn-primary" style="width:auto;padding:8px 20px" onclick="showToast('Paramètres sauvegardés','success')"><i class="fas fa-save"></i> Sauvegarder</button>
    </div>
    <div class="grid-2">
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-user"></i> Profil Utilisateur</div>
          <div class="form-field" style="margin-bottom:12px"><label>Nom Complet</label><input type="text" value="${currentRole==='superadmin'?'Équipe ARGOS':'Jean Mballa'}"></div>
          <div class="form-field" style="margin-bottom:12px"><label>Email</label><input type="email" value="${currentRole==='superadmin'?'admin@argos.io':'contact@transafrique.cm'}"></div>
          <div class="form-field" style="margin-bottom:12px"><label>Téléphone</label><input type="text" value="+237 6 90 00 00 00"></div>
          <div class="form-field" style="margin-bottom:12px"><label>Langue Interface</label>
            <select><option>Français</option><option>English</option></select>
          </div>
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-bell"></i> Notifications</div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Alertes SMS</div>
              <div class="settings-item-desc">Recevoir les alertes par SMS</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Alertes Email</div>
              <div class="settings-item-desc">Notifications par email</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Alertes WhatsApp</div>
              <div class="settings-item-desc">Notifications WhatsApp en temps réel</div>
            </div>
            <label class="toggle-switch"><input type="checkbox"><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Rapport Quotidien</div>
              <div class="settings-item-desc">Rapport PDF automatique chaque jour</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
        </div>
        <div class="card">
          <div class="settings-title"><i class="fas fa-shield-alt"></i> Sécurité</div>
          <div class="form-field" style="margin-bottom:12px"><label>Mot de Passe Actuel</label><input type="password" placeholder="••••••••"></div>
          <div class="form-field" style="margin-bottom:12px"><label>Nouveau Mot de Passe</label><input type="password" placeholder="••••••••"></div>
          <div class="form-field" style="margin-bottom:16px"><label>Confirmer</label><input type="password" placeholder="••••••••"></div>
          <button class="btn-secondary" onclick="showToast('Mot de passe mis à jour','success')">Changer le Mot de Passe</button>
        </div>
      </div>
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-desktop"></i> Monitoring</div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Fréquence d'actualisation</div>
              <div class="settings-item-desc">Mise à jour des données</div>
            </div>
            <select style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:4px 8px;color:var(--text);font-size:12px;outline:none">
              <option>5 secondes</option>
              <option>10 secondes</option>
              <option>30 secondes</option>
            </select>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Historique GPS</div>
              <div class="settings-item-desc">Afficher les traces de déplacement</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Mode Hors Ligne</div>
              <div class="settings-item-desc">Cache les données pour consultation hors ligne</div>
            </div>
            <label class="toggle-switch"><input type="checkbox"><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Enregistrement Audio</div>
              <div class="settings-item-desc">Enregistrer les voix/sons détectés</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Rapport Automatique</div>
              <div class="settings-item-desc">Génération automatique à chaque incident</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="settings-title"><i class="fas fa-map"></i> Carte & Affichage</div>
          <div class="form-field" style="margin-bottom:12px">
            <label>Fond de Carte</label>
            <select>
              <option>Satellite Sombre</option>
              <option>OpenStreetMap</option>
              <option>Terrain</option>
            </select>
          </div>
          <div class="form-field" style="margin-bottom:12px">
            <label>Unité Température</label>
            <select><option>Celsius (°C)</option><option>Fahrenheit (°F)</option></select>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Animations Carte</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
          <div class="settings-item">
            <div class="settings-item-info">
              <div class="settings-item-label">Marqueurs Pulsants</div>
            </div>
            <label class="toggle-switch"><input type="checkbox" checked><span class="toggle-slider"></span></label>
          </div>
        </div>
        <div class="card">
          <div class="settings-title"><i class="fas fa-info-circle"></i> À Propos</div>
          <div style="font-size:13px;color:var(--text2);line-height:1.8">
            <div>Plateforme ARGOS v2.4.0</div>
            <div style="color:var(--text3)">Surveillance de Boîtes Noires & Conteneurs</div>
            <div style="margin-top:8px">© 2025 Équipe ARGOS — Tous droits réservés</div>
          </div>
          <div style="margin-top:12px;display:flex;gap:8px">
            <button class="btn-icon" onclick="showToast('Déconnexion...','info');setTimeout(()=>{document.getElementById(\'app\').style.display=\'none\';document.getElementById(\'login-screen\').style.display=\'flex\'},1000)"><i class="fas fa-sign-out-alt"></i> Déconnexion</button>
            <button class="btn-icon" onclick="showToast('Support contacté','success')"><i class="fas fa-headset"></i> Support</button>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

// ===== MAP INIT =====
function initMap(mapId, role){
  const el = document.getElementById(mapId);
  if(!el) return;
  if(maps[mapId]){ maps[mapId].remove(); delete maps[mapId]; }
  const center = [5.0, 11.0];
  const map = L.map(mapId, {center, zoom: role==='client'?9:6, zoomControl:false});
  maps[mapId] = map;
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution:'&copy; Argos_Mick &copy; Argos',
    maxZoom:19
  }).addTo(map);
  const showContainers = currentRole==='client' ? [CONTAINERS[0]] : CONTAINERS;
  showContainers.forEach(c=>{
    if(c.status==='off' && currentRole!=='superadmin') return;
    const color = c.status==='ok'?'#00e676':c.status==='warning'?'#ffab00':c.status==='danger'?'#ff4444':'#5a7290';
    const markerHtml = `<div class="marker-pulse">
      <div class="marker-outer" style="border-color:${color}"></div>
      <div class="marker-inner" style="background:${color};box-shadow:0 0 8px ${color}"></div>
    </div>`;
    const icon = L.divIcon({html:markerHtml,className:'',iconSize:[24,24],iconAnchor:[12,12]});
    const marker = L.marker([c.lat, c.lng], {icon}).addTo(map);
    marker.bindPopup(`
      <div style="font-family:'Space Grotesk',sans-serif;min-width:200px">
        <div style="font-family:'Orbitron',sans-serif;font-size:16px;color:var(--cyan,#00d4ff);margin-bottom:8px">${c.id}</div>
        <div style="color:var(--text,#e2eaf6);font-size:13px;margin:4px 0"><i class="fas fa-map-marker-alt"></i> ${c.route}</div>
        <div style="color:var(--text,#e2eaf6);font-size:13px;margin:4px 0"><i class="fas fa-truck"></i> ${c.driver}</div>
        ${c.status!=='off'?`
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:10px">
          <div style="text-align:center;background:rgba(0,0,0,.3);padding:6px;border-radius:6px">
            <div style="font-size:18px;font-weight:700;color:${c.temp>32?'#ff4444':c.temp>28?'#ffab00':'#00e676'}">${c.temp}°C</div>
            <div style="font-size:10px;color:#8fa3bc">TEMP</div>
          </div>
          <div style="text-align:center;background:rgba(0,0,0,.3);padding:6px;border-radius:6px">
            <div style="font-size:18px;font-weight:700;color:#00d4ff">${c.speed}</div>
            <div style="font-size:10px;color:#8fa3bc">KM/H</div>
          </div>
        </div>
        <div style="margin-top:8px;font-size:12px;color:#8fa3bc">Mis à jour: ${c.lastUpdate}</div>
        `:'<div style="color:#5a7290;margin-top:8px">Boîte hors ligne</div>'}
      </div>`);
  });
  // Ajout des itinéraires via OSRM
  showContainers.filter(c=>c.status!=='off' && c.destinations && c.destinations.length>0).forEach(c=>{
    const waypoints = [ [c.lat, c.lng], ...c.destinations.map(d=>[d.lat, d.lng]) ];
    fetchOSRMRoute(waypoints, c.mode).then(route => {
      if(route) {
        L.polyline(route, {color: '#00d4ff', weight:3, opacity:0.8}).addTo(map);
      }
    });
  });
  if(role==='sell'){
    map.on('click', e=>{
      const coordEl = document.getElementById('map-sale-coords');
      if(coordEl) coordEl.innerHTML = `<i class="fas fa-map-marker-alt"></i> Lat: ${e.latlng.lat.toFixed(6)}, Lng: ${e.latlng.lng.toFixed(6)}`;
      map.eachLayer(l=>{ if(l._clickMarker) map.removeLayer(l); });
      const m = L.marker(e.latlng).addTo(map);
      m._clickMarker = true;
    });
  }
}

// ===== CHARTS =====
function initCharts(page){
  const labels24 = Array.from({length:24},(_,i)=>`${i}:00`);
  const randomData = (base,range,len=24)=>Array.from({length:len},()=>+(base+(Math.random()-.5)*range).toFixed(1));
  Chart.defaults.color='#8fa3bc';
  Chart.defaults.borderColor='rgba(30,45,66,0.6)';
  function createChart(id,type,labels,datasets,opts={}){
    const el=document.getElementById(id);
    if(!el) return;
    if(charts[id]) charts[id].destroy();
    charts[id]=new Chart(el,{type,data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:datasets.length>1,labels:{color:'#8fa3bc',boxWidth:12,font:{family:'Space Grotesk',size:11}}},...opts.plugins},scales:{x:{grid:{color:'rgba(30,45,66,.5)'},ticks:{font:{size:10},maxTicksLimit:8}},y:{grid:{color:'rgba(30,45,66,.5)'},ticks:{font:{size:10}},...(opts.y||{})}},animation:{duration:800},...opts}});
    return charts[id];
  }
  createChart('chart-temp','line',labels24,[{label:'BN-001',data:randomData(22,6),borderColor:'#00d4ff',backgroundColor:'rgba(0,212,255,.08)',borderWidth:2,fill:true,tension:.4,pointRadius:0},{label:'BN-002',data:randomData(30,8),borderColor:'#ff4444',backgroundColor:'rgba(255,68,68,.05)',borderWidth:2,fill:false,tension:.4,pointRadius:0}]);
  createChart('chart-hum','line',labels24,[{label:'Humidité %',data:randomData(62,15),borderColor:'#2979ff',backgroundColor:'rgba(41,121,255,.08)',borderWidth:2,fill:true,tension:.4,pointRadius:0}]);
  createChart('chart-shock','bar',['00h','04h','08h','12h','16h','20h'],
    [{label:'Chocs',data:[0,1,0,3,2,1],backgroundColor:['#00e676','#ffab00','#00e676','#ff4444','#ffab00','#00e676'],borderRadius:4}]);
  createChart('chart-press','line',labels24,[{label:'Pression hPa',data:randomData(1010,8),borderColor:'#b44dff',backgroundColor:'rgba(180,77,255,.08)',borderWidth:2,fill:true,tension:.4,pointRadius:0}]);
  createChart('chart-speed','line',labels24,[
    {label:'BN-001',data:randomData(65,20),borderColor:'#00d4ff',borderWidth:1.5,fill:false,tension:.4,pointRadius:0},
    {label:'BN-002',data:randomData(55,25),borderColor:'#00e676',borderWidth:1.5,fill:false,tension:.4,pointRadius:0},
    {label:'BN-004',data:randomData(50,20),borderColor:'#ffab00',borderWidth:1.5,fill:false,tension:.4,pointRadius:0},
  ]);
  createChart('chart-revenue','bar',['Jan','Fév','Mar','Avr','Mai','Jun'],[{label:'Recettes (CFA)',data:[380000,420000,395000,510000,480000,825000],backgroundColor:'rgba(0,212,255,.4)',borderColor:'#00d4ff',borderWidth:1,borderRadius:4}]);
  createChart('chart-subs','doughnut',['Choc','Température','Humidité','Vent','Pression'],[{data:[10,5,3,4,2],backgroundColor:['#ff4444','#ffab00','#2979ff','#00e676','#b44dff'],borderWidth:0,hoverOffset:6}],{y:{display:false}});
}

// ===== CONTAINER DETAIL MODAL =====
function showContainerDetail(id){
  const c = CONTAINERS.find(x=>x.id===id);
  if(!c) return;
  const statusIcon = c.status==='ok'?'fa-check-circle':c.status==='warning'?'fa-exclamation-triangle':c.status==='danger'?'fa-exclamation-circle':'fa-power-off';
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this) closeModal()">
      <div class="modal" style="max-width:700px">
        <div class="modal-header">
          <div>
            <div class="modal-title" style="font-family:var(--display);color:var(--cyan)">${c.id}</div>
            <div style="font-size:12px;color:var(--text3)">${c.company} • ${c.driver}</div>
          </div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
            <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}"><i class="fas ${statusIcon}"></i> ${c.status.toUpperCase()}</span>
            <span class="badge badge-${c.securityOn?'info':'off'}"><i class="fas ${c.securityOn?'fa-lock':'fa-unlock-alt'}"></i> ${c.securityOn?'Mode Sécurisé ON':'Mode Sécurisé OFF'}</span>
            <span style="font-size:12px;color:var(--text3)"><i class="fas fa-clock"></i> Mise à jour: ${c.lastUpdate}</span>
          </div>
          <div style="background:var(--bg3);border-radius:var(--radius2);padding:14px;margin-bottom:16px">
            <div style="font-size:12px;color:var(--text3);margin-bottom:4px"><i class="fas fa-map-marker-alt"></i> ROUTE</div>
            <div style="font-size:14px;font-weight:600">${c.route}</div>
            <div class="progress-bar" style="margin-top:8px">
              <div class="progress-fill" style="width:${c.progress}%;background:${c.status==='ok'?'var(--green)':c.status==='warning'?'var(--amber)':'var(--red)'}"></div>
            </div>
            <div style="text-align:right;font-size:11px;color:var(--text3);margin-top:4px">${c.progress}% complété</div>
          </div>
          ${c.status!=='off'?`
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">
            ${[['fa-thermometer-half','Température',c.temp+'°C',c.temp>32?'var(--red)':c.temp>28?'var(--amber)':'var(--green)'],
               ['fa-tint','Humidité',c.humidity+'%',c.humidity>75?'var(--red)':c.humidity>65?'var(--amber)':'var(--green)'],
               ['fa-compress-arrows-alt','Pression',c.pressure+' hPa','var(--cyan)'],
               ['fa-wave-square','Chocs',c.shock+' G',c.shock>5?'var(--red)':c.shock>0?'var(--amber)':'var(--green)'],
               ['fa-tachometer-alt','Vitesse',c.speed+' km/h','var(--text)'],
               ['fa-box','Cargo',c.cargo,'var(--text2)'],
               ['fa-money-bill-wave','Valeur',c.value.toLocaleString()+' CFA','var(--purple)'],
               ['fa-building','Entreprise',c.company,'var(--text2)']].map(([icon,label,val,color])=>`
            <div style="background:var(--card2);border:1px solid var(--border);border-radius:var(--radius);padding:12px;text-align:center">
              <div style="font-size:20px"><i class="fas ${icon}"></i></div>
              <div style="font-size:11px;color:var(--text3);margin:4px 0">${label}</div>
              <div style="font-size:13px;font-weight:700;color:${color}">${val}</div>
            </div>`).join('')}
          </div>
          <div style="margin-bottom:16px">
            <div style="font-size:12px;color:var(--text3);margin-bottom:8px"><i class="fas fa-shield-alt"></i> CONTRÔLE SÉCURITÉ</div>
            <div class="security-toggle">
              <div style="flex:1">
                <div style="font-size:13px;font-weight:600">Mode Sécurisé</div>
                <div style="font-size:11px;color:var(--text3)">Verrouille le conteneur et active les alarmes</div>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" ${c.securityOn?'checked':''} onchange="toggleSecurity('${c.id}',this.checked)">
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>`:'<div class="alert alert-warn"><i class="fas fa-power-off"></i> Boîte noire hors ligne — Dernier état connu affiché</div>'}
          <div style="margin-bottom:16px">
            <div style="font-size:12px;color:var(--text3);margin-bottom:8px">JOURNAL D'ÉVÉNEMENTS</div>
            ${EVENTS_LOG.filter(e=>e.container===c.id).length>0?
              EVENTS_LOG.filter(e=>e.container===c.id).map(e=>`
              <div class="timeline-item">
                <div class="timeline-dot" style="background:${e.severity==='danger'?'var(--red)':'var(--amber)'}"></div>
                <div class="timeline-content">
                  <div class="timeline-text">${e.msg}</div>
                  <div class="timeline-time">${e.time} • ${e.type}</div>
                </div>
              </div>`).join(''):
              '<div style="color:var(--text3);font-size:13px;padding:12px 0"><i class="fas fa-check"></i> Aucun événement — Tout nominal</div>'}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-primary" style="width:auto" onclick="viderContainer('${c.id}')"><i class="fas fa-dumpster"></i> Vider</button>
          <button class="btn-primary" style="width:auto" onclick="continuerContainer('${c.id}')"><i class="fas fa-forward"></i> Continuer</button>
          <button class="export-btn" onclick="openAIAssistant()"><i class="fas fa-file-pdf"></i> Générer Rapport</button>
          <button class="btn-primary" style="width:auto" onclick="closeModal();navigateTo('map')"><i class="fas fa-map-marker-alt"></i> Voir sur Carte</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

function showCompanyDetail(id){
  const e = COMPANIES.find(c=>c.id===id);
  if(!e) return;
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this) closeModal()">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">${e.name}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div class="grid-2" style="margin-bottom:16px">
            <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Boîtes Noires</div><div class="stat-value">${e.boxes}</div></div>
            <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Clients</div><div class="stat-value">${e.clients}</div></div>
          </div>
          <div style="margin-bottom:16px">
            <div class="settings-item"><div class="settings-item-label">Contact</div><span>${e.contact}</span></div>
            <div class="settings-item"><div class="settings-item-label">Téléphone</div><span>${e.phone}</span></div>
            <div class="settings-item"><div class="settings-item-label">Localisation</div><span><i class="fas fa-map-marker-alt"></i> ${e.location}</span></div>
            <div class="settings-item"><div class="settings-item-label">Statut</div><span class="badge badge-${e.status==='active'?'ok':'warn'}">${e.status}</span></div>
            <div class="settings-item"><div class="settings-item-label">Revenu Total</div><span style="font-family:var(--mono)">${e.revenue.toLocaleString()} CFA</span></div>
          </div>
          <div style="margin-bottom:16px">
            <div style="font-size:13px;font-weight:600;margin-bottom:10px;color:var(--text2)">Gestion Abonnement</div>
            <div class="form-row">
              <div class="form-field"><label>Prolonger (jours)</label><input type="number" placeholder="30"></div>
              <div class="form-field"><label>Action</label>
                <select><option>Prolonger</option><option>Réduire</option><option>Annuler</option></select>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-danger" onclick="showToast('Abonnement annulé','info');closeModal()">Annuler Abonnement</button>
          <button class="btn-primary" style="width:auto" onclick="showToast('Abonnement mis à jour','success');closeModal()">Sauvegarder</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

function showModal(type, param){
  if(type==='addContainer'){
    const html=`<div class="modal-overlay" onclick="if(event.target===this) closeModal()"><div class="modal"><div class="modal-header"><div class="modal-title"><i class="fas fa-box"></i> Nouveau Conteneur</div><button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div><div class="modal-body"><div class="form-field" style="margin-bottom:12px"><label>ID Boîte Noire</label><input type="text" placeholder="BN-XXX"></div><div class="form-field" style="margin-bottom:12px"><label>Chauffeur Assigné</label><select><option>Marc Essono</option><option>Samuel Biya</option><option>Pierre Ateba</option></select></div><div class="form-field" style="margin-bottom:12px"><label>Route</label><input type="text" placeholder="Départ → Destination"></div></div><div class="modal-footer"><button class="btn-secondary" onclick="closeModal()">Annuler</button><button class="btn-primary" style="width:auto" onclick="showToast('Conteneur ajouté','success');closeModal()"><i class="fas fa-check"></i> Ajouter</button></div></div></div>`;
    document.getElementById('modal-root').innerHTML=html;
  } else if(type==='addDriver'){
    const html=`<div class="modal-overlay" onclick="if(event.target===this) closeModal()"><div class="modal"><div class="modal-header"><div class="modal-title"><i class="fas fa-truck"></i> Nouveau Chauffeur</div><button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div><div class="modal-body"><div class="form-row"><div class="form-field"><label>Nom Complet</label><input type="text" placeholder="Nom chauffeur"></div><div class="form-field"><label>Téléphone</label><input type="text" placeholder="+237..."></div></div><div class="form-row"><div class="form-field"><label>Email</label><input type="email" placeholder="chauffeur@mail.com"></div><div class="form-field"><label>Conteneur(s)</label><select><option>BN-001</option><option>BN-002</option><option>BN-003</option></select></div></div><div class="form-field" style="margin-bottom:12px"><label>Mot de Passe Initial</label><input type="password" placeholder="••••••••"></div></div><div class="modal-footer"><button class="btn-secondary" onclick="closeModal()">Annuler</button><button class="btn-primary" style="width:auto" onclick="showToast('Compte chauffeur créé!','success');closeModal()"><i class="fas fa-check"></i> Créer le Compte</button></div></div></div>`;
    document.getElementById('modal-root').innerHTML=html;
  } else if(type==='settings'){
    navigateTo('settings');
  } else if(type==='addClient'){
    document.getElementById('modal-root').innerHTML='';
    navigateTo('clients-own');
  }
}

function closeModal(){ document.getElementById('modal-root').innerHTML=''; }

function toggleSecurity(id, state){
  const c = CONTAINERS.find(x=>x.id===id);
  if(c){ c.securityOn=state; }
  const lockIcon = state ? '<i class="fas fa-lock"></i>' : '<i class="fas fa-unlock-alt"></i>';
  showToast(`${id}: Mode sécurisé ${state?'ACTIVÉ '+lockIcon:'DÉSACTIVÉ '+lockIcon}`, state?'success':'info');
}

function calcSubPrice(sel){
  const prices={transit:'5 000 CFA',month:'15 000 CFA',year:'150 000 CFA'};
  const el=document.getElementById('sub-price-calc');
  if(el) el.value=prices[sel.value]||'5 000 CFA';
}

function selectPeriod(el, period){
  document.querySelectorAll('.sub-card').forEach(c=>c.classList.remove('selected'));
  el.classList.add('selected');
}

function submitSale(){
  const company = document.getElementById('sell-company')?.value;
  if(!company){showToast('<i class="fas fa-exclamation-triangle"></i> Veuillez remplir le nom de l\'entreprise','warn');return;}
  showToast(`<i class="fas fa-check"></i> Vente validée pour ${company}! Compte créé.`,'success');
}

function previewFile(input, previewId){
  const file=input.files[0];
  if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    const div=document.getElementById(previewId);
    if(div) div.innerHTML=`<img src="${e.target.result}" style="max-width:100%;max-height:120px;border-radius:var(--radius);margin-top:8px;border:1px solid var(--border)">`;
  };
  reader.readAsDataURL(file);
}

function setTab(el, group, val){
  el.parentElement.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
}

function filterContainers(val){
  document.querySelectorAll('#containers-grid > div').forEach(el=>{
    el.style.display=val===''||el.textContent.toLowerCase().includes(val.toLowerCase())?'block':'none';
  });
}

function filterContainersStatus(status, tabEl){
  if(tabEl){ tabEl.parentElement.querySelectorAll('.tab').forEach(t=>t.classList.remove('active')); tabEl.classList.add('active'); }
  document.querySelectorAll('#containers-grid > div').forEach(el=>{
    el.style.display=status==='all'||el.className.includes('status-'+status)?'block':'none';
  });
}

function filterContainersList(val){
  document.querySelectorAll('#containers-sidebar-list .container-item').forEach(el=>{
    el.style.display=val===''||el.textContent.toLowerCase().includes(val.toLowerCase())?'flex':'none';
  });
}

function focusContainer(id){
  const c=CONTAINERS.find(x=>x.id===id);
  if(!c||!maps['map-main']) return;
  maps['map-main'].flyTo([c.lat,c.lng],12,{animate:true,duration:1});
}

function showAllContainers(){
  if(!maps['map-main']) return;
  const bounds=L.latLngBounds(CONTAINERS.map(c=>[c.lat,c.lng]));
  maps['map-main'].fitBounds(bounds.pad(.2));
}

function toggleMapLayer(){
  showToast('<i class="fas fa-layer-group"></i> Fond de carte modifié','info');
}

function toggleTrails(){
  showToast('<i class="fas fa-route"></i> Traces GPS: affichage modifié','info');
}

function toggleHeatmap(){
  showToast('<i class="fas fa-fire"></i> Heatmap des alertes: activée','info');
}

function globalSearch(val){
  if(val.length<2) return;
  const results = CONTAINERS.filter(c=>c.id.toLowerCase().includes(val.toLowerCase())||c.company.toLowerCase().includes(val.toLowerCase()));
  if(results.length>0) showToast(`<i class="fas fa-search"></i> Trouvé: ${results[0].id} — ${results[0].route}`,'info');
}

function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('open');
}

function toggleNotif(){
  document.getElementById('notif-panel').classList.toggle('open');
}

function closeNotif(){
  document.getElementById('notif-panel').classList.remove('open');
}

function buildNotifications(){
  const notifs = [
    {id:1,text:'<i class="fas fa-exclamation-circle" style="color:var(--red)"></i> CRITIQUE: Choc détecté sur BN-003',sub:'Il y a 2 minutes',sev:'danger'},
    {id:2,text:'<i class="fas fa-thermometer-half" style="color:var(--amber)"></i> Température élevée sur BN-002',sub:'Il y a 5 minutes',sev:'warn'},
    {id:3,text:'<i class="fas fa-wind" style="color:var(--amber)"></i> Vent violent signalé — Axe Bafoussam',sub:'Il y a 12 minutes',sev:'warn'},
    {id:4,text:'<i class="fas fa-check-circle" style="color:var(--green)"></i> BN-001 en route — Tout nominal',sub:'Il y a 18 minutes',sev:'ok'},
  ];
  const html=notifs.map(n=>`
    <div class="notif-item" onclick="closeNotif()">
      <div style="font-size:13px;color:var(--text)">${n.text}</div>
      <div class="notif-time">${n.sub}</div>
    </div>`).join('');
  document.getElementById('notif-list').innerHTML=html;
  document.getElementById('notif-count').textContent=notifs.length;
}

function showToast(msg, type='info'){
  const panel=document.getElementById('alert-panel');
  const icons={info:'<i class="fas fa-info-circle"></i>',success:'<i class="fas fa-check-circle"></i>',warn:'<i class="fas fa-exclamation-triangle"></i>',danger:'<i class="fas fa-skull"></i>'};
  const toast=document.createElement('div');
  toast.className=`alert-toast alert-toast-${type}`;
  toast.innerHTML=`<span>${icons[type]||icons.info}</span><span>${msg}</span>`;
  panel.appendChild(toast);
  setTimeout(()=>{ toast.style.opacity='0'; toast.style.transition='opacity .3s'; setTimeout(()=>toast.remove(),300); }, 4000);
}

function startClock(){
  function update(){
    const now=new Date();
    const el=document.getElementById('live-time');
    if(el) el.innerHTML=`<i class="far fa-clock"></i> ${now.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}`;
  }
  update();
  if(liveInterval) clearInterval(liveInterval);
  liveInterval=setInterval(update,1000);
}

function startSensorSimulation(){
  if(sensorInterval) clearInterval(sensorInterval);
  sensorInterval=setInterval(()=>{
    CONTAINERS.forEach(c=>{
      if(c.status==='off') return;
      c.temp = +(c.temp + (Math.random()-.5)*0.3).toFixed(1);
      c.humidity = Math.min(95,Math.max(30,+(c.humidity+(Math.random()-.5)*0.5).toFixed(1)));
      c.pressure = +(c.pressure+(Math.random()-.5)*0.2).toFixed(1);
      if(c.speed>0) c.speed = Math.max(0,+(c.speed+(Math.random()-.5)*2).toFixed(0));
      c.lat += (Math.random()-.5)*0.003;
      c.lng += (Math.random()-.5)*0.003;
    });
    const t=document.getElementById('live-temp');if(t) t.textContent=CONTAINERS[0].temp;
    const h=document.getElementById('live-hum');if(h) h.textContent=CONTAINERS[0].humidity;
    const p=document.getElementById('live-press');if(p) p.textContent=CONTAINERS[0].pressure;
    const s=document.getElementById('live-speed');if(s) s.textContent=CONTAINERS[0].speed;
    const mt=document.getElementById('map-temp');if(mt) mt.textContent=CONTAINERS[0].temp;
    const dt=document.getElementById('drv-temp');if(dt) dt.textContent=CONTAINERS[0].temp+'°C';
    const dh=document.getElementById('drv-hum');if(dh) dh.textContent=CONTAINERS[0].humidity+'%';
    const ds=document.getElementById('drv-speed');if(ds) ds.textContent=CONTAINERS[0].speed+' km/h';
    if(Math.random()<.01 && CONTAINERS[0].temp>32) showToast(`<i class="fas fa-thermometer-half"></i> BN-001: Température haute ${CONTAINERS[0].temp}°C`,'warn');
    if(charts['chart-temp']&&charts['chart-temp'].data){
      const d=charts['chart-temp'].data.datasets[0].data;
      d.push(CONTAINERS[0].temp);d.shift();
      charts['chart-temp'].update('none');
    }
    Object.values(maps).forEach(map=>{
      map.eachLayer(l=>{
        if(l instanceof L.Marker){
          const ll=l.getLatLng();
          const c=CONTAINERS.find(c=>Math.abs(c.lat-ll.lat)<0.01&&c.speed>0);
          if(c){ l.setLatLng([c.lat,c.lng]); }
        }
      });
    });
  }, 3000);
}

// ===== NOUVELLES FONCTIONS =====

// Gestion type conteneur dans vente
function handleContainerTypeChange(){
  const type = document.getElementById('container-type').value;
  document.getElementById('container-volume-section').style.display = type ? 'block' : 'none';
  document.getElementById('open-top-note').style.display = type==='OpenTop' ? 'block' : 'none';
  document.getElementById('pouce-field').style.display = type==='DRY' ? 'block' : 'none';
  if(type==='HighCube'){
    document.getElementById('container-volume').value = '67';
    calcPerimeter();
  }
}

function calcPerimeter(){
  const vol = parseFloat(document.getElementById('container-volume').value) || 0;
  // Approx: périmètre = 2*(longueur+largeur), longueur≈6m, largeur≈2.4m pour 1 conteneur standard, volume ≈ L*l*h, h≈2.6m
  // Simplification: perimeter = 2 * ( (vol/(2.4*2.6)) + 2.4 ) => 2*(L+2.4), L=vol/(2.4*2.6)
  if(vol>0){
    const L = vol / (2.4 * 2.6);
    const perimeter = 2 * (L + 2.4);
    document.getElementById('container-perimeter').value = perimeter.toFixed(2) + ' m';
  }
}

function addNewClient(){
  const name = document.getElementById('new-client-name')?.value;
  if(!name){ showToast('Nom requis','warn'); return; }
  // Assigner automatiquement une boîte noire disponible (logique simplifiée)
  const availableBox = CONTAINERS.find(c=> c.status==='off' || (c.status==='ok' && c.cargo === 'Vide'));
  if(availableBox){
    availableBox.cargo = document.getElementById('new-client-cargo-name')?.value || 'Colis';
    availableBox.company = COMPANIES[0].name; // propriétaire courant
    availableBox.status = 'ok';
    CLIENTS.push({
      id:'C'+(CLIENTS.length+1),
      name: name,
      company: availableBox.company,
      container: availableBox.id,
      cargo: availableBox.cargo,
      phone: document.getElementById('new-client-phone')?.value || '',
      period: document.getElementById('new-client-period')?.value || 'transit',
      status: 'active',
      value: parseInt(document.getElementById('new-client-value')?.value) || 0,
      paid: false
    });
    showToast(`Client ${name} ajouté et assigné à ${availableBox.id}`,'success');
    // Redessiner la page
    navigateTo('clients-own');
  } else {
    showToast('Aucune boîte noire disponible pour le moment','warn');
  }
}

// Fonction Vider
function viderContainer(id){
  const c = CONTAINERS.find(x=>x.id===id);
  if(!c) return;
  closeModal();
  // Confirmation
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this) closeModal()">
      <div class="modal">
        <div class="modal-header"><div class="modal-title">Confirmation de vidage - ${c.id}</div><button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <p>Le conteneur va être vidé de toutes ses marchandises et détaché des clients. Une demande de validation sera envoyée aux parties prenantes.</p>
          <p><strong>Après validation, le conteneur passera en mode DOWN.</strong></p>
          <div class="form-field"><label>Motif</label><input type="text" id="vider-reason" placeholder="Raison du vidage"></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="executeVider('${id}')">Valider le vidage</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

function executeVider(id){
  closeModal();
  const c = CONTAINERS.find(x=>x.id===id);
  if(!c) return;
  // Envoyer notifications (simulé)
  showToast(`Demande de vidage envoyée pour ${id}. En attente de validation des parties.`,'info');
  // Pour l'instant, on simule la validation après 3s
  setTimeout(()=>{
    c.status = 'down';
    c.cargo = 'Vide';
    c.value = 0;
    c.securityOn = true; // sécurité active
    // Détacher des clients
    CLIENTS.forEach(cl=>{ if(cl.container===id) cl.container = ''; });
    showToast(`${id} vidé avec succès. Conteneur en mode DOWN.`,'success');
    // Rafraîchir l'interface
    navigateTo(currentPage);
  }, 3000);
}

// Fonction Continuer
function continuerContainer(id){
  const c = CONTAINERS.find(x=>x.id===id);
  if(!c) return;
  closeModal();
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this) closeModal()">
      <div class="modal" style="max-width:600px">
        <div class="modal-header"><div class="modal-title">Continuer le voyage - ${c.id}</div><button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-field"><label>Moyen de transport</label>
              <select id="cont-mode"><option value="driving">Camion</option><option value="ferry">Navire</option><option value="train">Train</option><option value="airplane">Avion</option></select>
            </div>
            <div class="form-field"><label>Destination</label><input type="text" id="cont-dest" placeholder="Ville"></div>
          </div>
          <div class="form-field"><label>Cargaison ajoutée ?</label>
            <input type="checkbox" id="cont-add-cargo" onchange="document.getElementById('extra-cargo').style.display=this.checked?'block':'none'">
          </div>
          <div id="extra-cargo" style="display:none">
            <div class="form-row">
              <div class="form-field"><label>Nom Colis</label><input type="text" id="cont-cargo-name"></div>
              <div class="form-field"><label>Poids (kg)</label><input type="number" id="cont-cargo-weight"></div>
            </div>
            <div class="form-row">
              <div class="form-field"><label>Valeur (CFA)</label><input type="number" id="cont-cargo-value"></div>
              <div class="form-field"><label>Température moyenne</label><input type="number" id="cont-cargo-temp"></div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="executeContinuer('${id}')">Valider et Lancer</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

function executeContinuer(id){
  const c = CONTAINERS.find(x=>x.id===id);
  if(!c) return;
  const mode = document.getElementById('cont-mode')?.value || 'driving';
  const dest = document.getElementById('cont-dest')?.value;
  if(!dest){ showToast('Destination requise','warn'); return; }
  const addCargo = document.getElementById('cont-add-cargo')?.checked;
  if(addCargo){
    const cargoName = document.getElementById('cont-cargo-name')?.value || 'Nouveau colis';
    c.cargo = cargoName;
  }
  // Ajouter destination
  if(!c.destinations) c.destinations = [];
  // Simulation coordonnées destination (approximative)
  const destLat = c.lat + (Math.random()-0.5)*1.5;
  const destLng = c.lng + (Math.random()-0.5)*1.5;
  c.destinations.push({lat:destLat, lng:destLng, name:dest});
  c.mode = mode;
  c.status = 'ok';
  c.route += ` → ${dest}`;
  closeModal();
  showToast(`${id}: voyage continué vers ${dest}. Itinéraire mis à jour.`,'success');
  // Mettre à jour la carte avec nouvel itinéraire
  if(maps['map-main']){
    const waypoints = [ [c.lat, c.lng], ...c.destinations.map(d=>[d.lat, d.lng]) ];
    fetchOSRMRoute(waypoints, mode).then(route => {
      if(route){
        L.polyline(route, {color: '#00d4ff', weight:3}).addTo(maps['map-main']);
      }
    });
  }
  navigateTo(currentPage);
}

// Appel API OSRM pour routage
async function fetchOSRMRoute(waypoints, mode='driving'){
  try {
    const coords = waypoints.map(p => `${p[1]},${p[0]}`).join(';');
    const url = `https://router.project-osrm.org/route/v1/${mode}/${coords}?overview=full&geometries=geojson`;
    const resp = await fetch(url);
    const data = await resp.json();
    if(data.code==='Ok' && data.routes.length>0){
      const geom = data.routes[0].geometry;
      return geom.coordinates.map(c=>[c[1], c[0]]);
    }
  } catch(e){
    console.log('OSRM error', e);
    // fallback ligne droite
    return waypoints;
  }
}

// Vérification proximité destination (toutes les 5s)
function startDestinationProximityCheck(){
  setInterval(()=>{
    CONTAINERS.forEach(c=>{
      if(c.status==='off'||!c.destinations||c.destinations.length===0) return;
      const nextDest = c.destinations[c.currentDest];
      if(!nextDest) return;
      const dist = getDistanceFromLatLonInM(c.lat, c.lng, nextDest.lat, nextDest.lng);
      if(dist < 100 && !nextDest.alerted){
        nextDest.alerted = true;
        showToast(`<i class="fas fa-bell"></i> ${c.id}: Approche de ${nextDest.name} (${Math.round(dist)}m).`,'info');
        // Activation automatique de continuer après 15min (900000ms)
        setTimeout(()=>{
          if(c.currentDest < c.destinations.length-1){
            c.currentDest++;
            showToast(`${c.id}: Arrêt à ${nextDest.name} terminé. Passage à la prochaine destination.`,'success');
          } else {
            // Fin du trajet
            showToast(`${c.id}: Arrivé à destination finale ${nextDest.name}. Veuillez vider le conteneur.`,'success');
          }
        }, 900000); // 15 min
      }
    });
  }, 5000);
}
// ==== fonction quickAIMessage

function quickAIMessage(type) {
  const messages = {
    incident: "Je souhaite déclarer un incident survenu sur un conteneur.",
    pertes: "J'ai besoin d'un rapport détaillé des pertes matérielles.",
    chronologie: "Aidez-moi à retracer la chronologie des événements du trajet.",
    excuse: "Rédigez une lettre d'excuse professionnelle pour cet incident."
  };
  const msg = messages[type] || '';
  if (msg) {
    document.getElementById('ai-chat-input').value = msg;
    sendAIMessage(); // envoi immédiat
  }
}

//  ======= fonction de l'assistant IA =======
function openAIAssistant() {
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this) closeModal()">
      <div class="modal" style="max-width:900px; max-height:85vh; display:flex; flex-direction:column;">
        <!-- En-tête -->
        <div class="modal-header" style="background: var(--bg2); border-bottom: 1px solid var(--border);">
          <div class="modal-title" style="font-family: var(--display); color: var(--cyan);">
            <i class="fa-solid fa-robot"></i> Assistant IA – Rédacteur de Rapports
          </div>
          <button class="modal-close" onclick="closeModal()"><i class="fa-solid fa-times"></i></button>
        </div>
        
        <!-- Corps : conteneur flex avec colonne de chat -->
        <div class="modal-body" style="flex:1; display:flex; flex-direction:column; padding:0; overflow:hidden;">
          <!-- Zone de messages -->
          <div id="ai-chat-messages" style="flex:1; overflow-y:auto; padding:16px;"></div>
          <!-- Boutons de rapport rapide -->

        <div style="padding:12px; background:var(--bg2); border-top:1px solid var(--border);">
          <!-- Bulles de suggestions -->
          <div id="ai-suggestions" style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
            <button class="ai-chip" onclick="quickAIMessage('incident')">🚨 Signaler un incident</button>
            <button class="ai-chip" onclick="quickAIMessage('pertes')">📦 Évaluer des pertes</button>
            <button class="ai-chip" onclick="quickAIMessage('chronologie')">⏱️ Reconstituer la chronologie</button>
            <button class="ai-chip" onclick="quickAIMessage('excuse')">📝 Rédiger une lettre d'excuse</button>
          </div>

          <!-- Barre de saisie -->
          <div style="padding:12px; background:var(--bg2); border-top:1px solid var(--border);">
            <div style="display:flex; gap:8px;">
              <input type="text" id="ai-chat-input" placeholder="Décrivez l'incident, les pertes ou demandez un rapport..." 
                     style="flex:1; background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); padding:8px 12px; color:var(--text); font-size:13px;" 
                     onkeydown="if(event.key==='Enter') sendAIMessage()">
              <button class="btn-primary" style="width:auto; padding:8px 16px;" onclick="sendAIMessage()">
                <i class="fa-solid fa-paper-plane"></i>
              </button>
            </div>
            <div style="display:flex; gap:8px; margin-top:8px; font-size:11px; color:var(--text3);">
              <span style="cursor:pointer" onclick="quickAIMessage('incident')"><i class="fa-solid fa-triangle-exclamation"></i> Incident</span>
              <span style="cursor:pointer" onclick="quickAIMessage('pertes')"><i class="fa-solid fa-box"></i> Pertes</span>
              <span style="cursor:pointer" onclick="quickAIMessage('excuse')"><i class="fa-solid fa-handshake"></i> Excuse</span>
              <span style="cursor:pointer" onclick="quickAIMessage('chronologie')"><i class="fa-solid fa-clock"></i> Chrono</span>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  
  document.getElementById('modal-root').innerHTML = html;
  // Initialiser le chat avec un message d'accueil
  setTimeout(() => {
    addAIMessage('Bonjour ! Je suis votre assistant de rédaction. Expliquez-moi la situation, le conteneur concerné, les dommages éventuels... Je vous aiderai à créer un rapport professionnel.<br><br>Vous pouvez aussi cliquer sur un type de rapport ci-dessous pour commencer.');
  }, 200);
}
// ================ fonciton pour afficher les messages dans le chat de l'assistant IA =================

function addAIMessage(content) {
  const container = document.getElementById('ai-chat-messages');
  if(!container) return;
  const div = document.createElement('div');
  div.className = 'ai-msg ai';
  div.innerHTML = `<div class="msg-bubble">${content}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addUserMessage(content) {
  const container = document.getElementById('ai-chat-messages');
  if(!container) return;
  const div = document.createElement('div');
  div.className = 'ai-msg user';
  div.innerHTML = `<div class="msg-bubble">${content}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// ===== envoie du message de l'utilisateur à l'assistant IA et réponse simulée et appel de IA Claude =================

const DEEPSEEK_API_KEY = 'VOTRE_CLE_API'; // À sécuriser côté serveur en production
const DEEPSEEK_MODEL = 'deepseek-chat';
aiState.conversation = [
  { role: "system", content: systemPrompt }
];
async function sendAIMessage() {
  const input = document.getElementById('ai-chat-input');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  addUserMessage(text);

  // Contexte des conteneurs actifs
  const containerContext = CONTAINERS.map(c => 
    `${c.id} (${c.company}), statut:${c.status}, route:${c.route}, chocs:${c.shock}, température:${c.temp}°C`
  ).join('\n');
  const systemPrompt = `tu es Osiris, assistant de rédaction de rapports pour l'application ARGOS de suivi de conteneurs.
Voici l'état actuel des conteneurs:
${containerContext}

Aide l'utilisateur à rédiger des rapports d'incident, de pertes, lettres d'excuse ou chronologies.
Pose des questions pour obtenir les détails manquants.
Quand l'utilisateur demande un rapport final, génère-le au format JSON entre ===RAPPORT_JSON=== et ===FIN_JSON===.`;

  try {
    aiState.conversation.push({ role: "user", content: text });
    const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${DEEPSEEK_API_KEY}`
      },
      body: JSON.stringify({
        model: DEEPSEEK_MODEL,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: text }
        ],
        temperature: 0.7,
        max_tokens: 2000
      })
    });
    const aiText = data.choices[0].message.content;
    aiState.conversation.push({ role: "assistant", content: aiText });
    const data = await response.json();
    if (data.error) throw new Error(data.error.message);
    const aiResponse = data.choices[0].message.content;
    processAIResponse(aiResponse);
  } catch (e) {
    addAIMessage(`<span style="color:var(--red)">Erreur : ${e.message}</span>`);
  }
}

// ====== traitement de la réponse de l'IA (extraction du JSON et affichage) ========

function processAIResponse(text) {
  // Extraction du rapport JSON
  const jsonMatch = text.match(/===RAPPORT_JSON===\s*([\s\S]*?)\s*===FIN_JSON===/);
  if (jsonMatch) {
    const report = JSON.parse(jsonMatch[1]);
    aiState.reportData = report;
    const cleanText = text.replace(jsonMatch[0], '').trim();
    if (cleanText) addAIMessage(cleanText.replace(/\n/g, '<br>'));
    // Afficher un résumé et proposer d'ouvrir le document
    addAIMessage(`Rapport <strong>${report.type}</strong> généré !<br>
      <button onclick="openGeneratedReport()" style="margin-top:8px;background:var(--accent);border:none;color:#fff;padding:6px 12px;border-radius:4px;cursor:pointer;">Voir le document</button>
      <button onclick="downloadAIReport()" style="margin-top:8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:4px;cursor:pointer;">Télécharger PDF</button>`);
    return;
  }
  function renderChoices(choices) {
    const container = document.getElementById('ai-suggestions');
    if (!container) return;
    container.innerHTML = '';
    choices.forEach(choice => {
      const chip = document.createElement('span');
      chip.className = 'ai-chip';
      chip.textContent = choice.label;
      chip.onclick = () => {
        document.getElementById('ai-chat-input').value = choice.value;
        sendAIMessage();
      };
      container.appendChild(chip);
    });
  }
  // Affichage normal
  addAIMessage(text.replace(/\n/g, '<br>'));
  renderChoices(parsedChoices)
}

// ======== fonction pour ouvrir le rapport généré dans une nouvelle fenêtre (simulé) ========

function getDistanceFromLatLonInM(lat1,lon1,lat2,lon2){
  const R = 6371000;
  const dLat = deg2rad(lat2-lat1);
  const dLon = deg2rad(lon2-lon1);
  const a = Math.sin(dLat/2)*Math.sin(dLat/2)+Math.cos(deg2rad(lat1))*Math.cos(deg2rad(lat2))*Math.sin(dLon/2)*Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}
function deg2rad(deg){ return deg * (Math.PI/180); }

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', e=>{
  if(e.key==='Escape') { closeModal(); closeNotif(); }
  if(e.ctrlKey&&e.key==='k'){ e.preventDefault(); document.getElementById('global-search')?.focus(); openAIAssistant(); }
});

// Auto-start
window.onload=()=>{
  document.getElementById('login-pass').value='••••••••';
};
