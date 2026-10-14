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
      if (!data.access_token) {
        er.innerText = "Le serveur n'a pas fourni de session sécurisée.";
        return;
      }
      const qrUuid = pendingQrUuid || localStorage.getItem('pendingQrUuid');
      if (qrUuid && !['superadmin', 'owner'].includes(data.role)) {
        er.innerText = "Ce QR code n'est accessible qu'aux propriétaires et au superadmin.";
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('currentRole');
        localStorage.removeItem('currentUserId');
        return;
      }

      localStorage.setItem('currentRole', data.role);
      localStorage.setItem('currentUserId', data.user_id || '');
      localStorage.setItem('currentUserName', data.display_name || u);
      sessionStorage.setItem('argosAccessToken', data.access_token);
      localStorage.setItem('argosAccessToken', data.access_token);
      localStorage.setItem('isLoggedIn', 'true');
      currentRole   = data.role;
      currentUserId = data.user_id || null;
      document.getElementById('login-screen').style.display = 'none';
      document.getElementById('app').style.display = 'flex';
      if (data.requires_contract_acceptance) {
        await showPendingContractModal();
        return;
      }
      initApp();
      showToast(`Bienvenue ! Connecté en tant que ${currentRole}`, 'success');

      if (qrUuid) {
        localStorage.removeItem('pendingQrUuid');
        pendingQrUuid = null;
        await processQrLoginRedirect(qrUuid);
      } else await processArgosSetupIntent();
    } else {
      er.innerText = data.error || "Échec de l'authentification.";
    }
  } catch(e){ er.innerText = 'Erreur de connexion au serveur.'; }
}

async function processArgosSetupIntent() {
  const setupIntent = JSON.parse(sessionStorage.getItem('argosSetupIntent') || 'null');
  if (!setupIntent?.deviceUid) return;
  let registeredDevice = null;
  try {
    const response = await secureApiFetch(`/api/iot/devices/${encodeURIComponent(setupIntent.deviceUid)}/status`);
    if (response.ok) registeredDevice = await response.json();
  } catch (_) { /* la création signalera une éventuelle indisponibilité */ }
  if (registeredDevice?.blackBoxId) {
    sessionStorage.setItem('argosSetupIntent', JSON.stringify({...setupIntent, registered: true, blackBoxId: registeredDevice.blackBoxId}));
    navigateTo('my-boxes');
    showToast(`Cet ESP32 est déjà lié à la boîte #${registeredDevice.blackBoxId}. Utilisez « Configurer le réseau ESP32 » pour réparer sa configuration.`, 'warn');
  } else if (setupIntent.first && ['superadmin', 'owner'].includes(currentRole)) {
    setTimeout(() => openCreateBlackBoxModal({device_uid: setupIntent.deviceUid, access_point_url: setupIntent.espUrl}), 250);
  } else {
    navigateTo('my-boxes');
    showToast(`ESP32 ${setupIntent.deviceUid} détecté : choisissez sa boîte associée.`, 'info');
  }
}

async function showPendingContractModal(){
  const response = await secureApiFetch('/api/contracts/pending');
  const data = await response.json();
  if (!response.ok || !data.contract) {
    showToast(data.error || 'Contrat en attente introuvable', 'error');
    doLogout();
    return;
  }
  const contract = data.contract;
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay"><div class="modal" style="max-width:720px">
      <div class="modal-header"><div class="modal-title">Acceptation du contrat ARGOS</div></div>
      <div class="modal-body" style="max-height:65vh;overflow:auto">
        <div class="alert alert-info">Votre accès reste limité jusqu’à votre décision.</div>
        <div class="settings-item"><div class="settings-item-label">Référence</div><span>${escapeHTML(contract.contract_number)}</span></div>
        <div class="settings-item"><div class="settings-item-label">Période</div><span>${escapeHTML(contract.starts_on)} au ${escapeHTML(contract.ends_on)}</span></div>
        <div class="settings-item"><div class="settings-item-label">Boîtes attribuées</div><span>${(contract.box_ids || []).length}</span></div>
        <div style="margin:18px 0;padding:14px;border:1px solid var(--border);border-radius:10px;background:var(--bg3);line-height:1.55">
          <div style="font-weight:700;margin-bottom:8px">Points essentiels avant acceptation</div>
          <ul style="margin:0;padding-left:20px">
            <li>ARGOS fournit, installe et configure les dispositifs IoT de traçabilité et de sécurisation.</li>
            <li>Les dispositifs restent la propriété exclusive d’ARGOS. Toute perte, destruction ou dépose non autorisée peut entraîner une indemnité de 95 % de leur valeur.</li>
            <li>Le Client fournit les accès nécessaires, respecte les échéances de paiement et verse l’acompte prévu pour chaque trajet équipé.</li>
            <li>Les informations et données échangées restent confidentielles pendant le contrat et cinq années après son terme.</li>
            <li>Le contrat peut être résilié pour manquement grave non réparé dans les douze jours suivant une mise en demeure.</li>
          </ul>
        </div>
        <div class="form-field"><label>Nom complet du signataire</label><input id="contract-signer-name" required minlength="2" autocomplete="name" placeholder="Saisissez votre nom complet" oninput="updateContractAcceptanceState()"></div>
        <label style="display:flex;gap:10px;align-items:flex-start"><input type="checkbox" id="contract-terms-check" onchange="updateContractAcceptanceState()"> <span>J’ai lu et approuvé l’intégralité du contrat.</span></label>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="downloadProtectedDocument('/api/contracts/${contract.contract_uid}/document.pdf','contrat_${escapeHTML(contract.contract_number)}.pdf')">Télécharger le contrat</button>
        <button class="btn-secondary" onclick="submitContractDecision('${contract.contract_uid}','REJECT')">Refuser</button>
        <button class="btn-primary" id="contract-accept-button" disabled aria-disabled="true" onclick="submitContractDecision('${contract.contract_uid}','ACCEPT')">Accepter et continuer</button>
      </div>
    </div></div>`;
}

function updateContractAcceptanceState(){
  const signer = document.getElementById('contract-signer-name');
  const checked = !!document.getElementById('contract-terms-check')?.checked;
  const validName = !!signer && signer.value.trim().length >= 2;
  if(signer) signer.setCustomValidity(validName ? '' : 'Saisissez le nom complet du signataire.');
  const button = document.getElementById('contract-accept-button');
  if(button){
    button.disabled = !(validName && checked);
    button.setAttribute('aria-disabled', String(button.disabled));
  }
}

async function submitContractDecision(contractUid, decision){
  const signer = document.getElementById('contract-signer-name')?.value.trim() || '';
  const accepted = !!document.getElementById('contract-terms-check')?.checked;
  if (decision === 'ACCEPT' && (signer.length < 2 || !accepted)) {
    showToast('Le nom du signataire et l’acceptation des termes sont requis.', 'warn');
    return;
  }
  const response = await secureApiFetch(`/api/contracts/${encodeURIComponent(contractUid)}/decision`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({decision, signer_name:signer, accepted_terms:accepted})
  });
  const data = await response.json();
  if (!response.ok) return showToast(data.error || 'Décision impossible', 'error');
  if (decision === 'REJECT') {
    doLogout();
    return;
  }
  sessionStorage.setItem('argosAccessToken', data.access_token);
  localStorage.setItem('argosAccessToken', data.access_token);
  closeModal();
  initApp();
  showToast('Contrat accepté. Votre compte est maintenant actif.', 'success');
}

function initializeQrLoginFlow(){
  if (window.argosQrFlowInitialized) return;
  window.argosQrFlowInitialized = true;
  const params = new URLSearchParams(window.location.search);
  const qrUuid = params.get('qr') || params.get('uuid');
  if (params.get('argos_setup') === '1') {
    sessionStorage.setItem('argosSetupIntent', JSON.stringify({
      first: params.get('first') === '1',
      deviceUid: params.get('device_uid') || '',
      espUrl: params.get('esp_url') || 'http://192.168.4.1'
    }));
    const cleanUrl = new URL(window.location.href);
    ['argos_setup','first','device_uid','esp_url'].forEach(key => cleanUrl.searchParams.delete(key));
    window.history.replaceState({}, '', `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
  }
  if (qrUuid) {
    pendingQrUuid = qrUuid;
    localStorage.setItem('pendingQrUuid', qrUuid);
    const url = new URL(window.location.href);
    url.searchParams.delete('qr');
    url.searchParams.delete('uuid');
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
  }

  const loggedIn = localStorage.getItem('isLoggedIn') === 'true';
  if (loggedIn && pendingQrUuid) {
    processQrLoginRedirect(pendingQrUuid);
  }
  if (loggedIn && sessionStorage.getItem('argosSetupIntent')) {
    setTimeout(() => processArgosSetupIntent(), 400);
  }
}

window.addEventListener('DOMContentLoaded', initializeQrLoginFlow);

async function processQrLoginRedirect(qrUuid) {
  try {
    const res = await secureApiFetch('/api/black-boxes/resolve-qr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qr_uuid: qrUuid })
    });
    const data = await res.json();

    if (!res.ok) {
      showToast('<i class="fas fa-times-circle"></i> ' + (data.error || 'Accès QR refusé'), 'error');
      return;
    }

    if (data.action === 'create') {
      openCreateBlackBoxModal(data.context || {});
      showToast('<i class="fas fa-plus-circle"></i> Nouveau parcours de boîte noire à finaliser', 'info');
      return;
    }

    if (data.action === 'archived') {
      showBlackBoxQrDecisionModal({ action: 'archived', box: data.box });
      return;
    }

    if (data.action === 'assign') {
      showAssignBoxModal(data);
      return;
    }

    openEditBlackBoxModal(data.box);
    showToast('<i class="fas fa-edit"></i> Édition de boîte noire via QR', 'info');
  } catch (e) {
    showToast('<i class="fas fa-times-circle"></i> Erreur QR: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════
//  INIT APP
// ══════════════════════════════════════════════════════
// 1. Initialiser la variable avec la valeur sauvegardée (ou 10 secondes par défaut)


// 2. La fonction appelée quand on change le select dans les paramètres
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
  setupAutoSidebarCollapse();
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
  const initialPage = (NAV[currentRole] || [])[0]?.id;
  if (initialPage) {
      navigateTo(initialPage);
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
  const navContainer = document.getElementById('nav-container');
  if (navContainer) navContainer.innerHTML = html;
}

function navigateTo(page){
  if(currentPage === page) {
    closeSidebarAfterNavigation();
    return;
  }
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));
  const navEl = document.getElementById('nav-'+page);
  if(navEl) navEl.classList.add('active');
  if(page === 'ai'){
    openAIAssistant();
    closeSidebarAfterNavigation();
    return;
  }
  currentPage = page;
  renderPage(page);
  closeSidebarAfterNavigation();
  scheduleSidebarAutoCollapse();
}

// Alias simplifié
function goToPage(page) {
  navigateTo(page);
}

function renderPage(page){
  const c = document.getElementById('pages-container');
  if (!c) {
    console.warn('pages-container introuvable pour la page', page);
    return;
  }
  const builders = {
    dashboard:   ()=> buildDashboard(),
    map:         ()=> buildMapPage(),
    containers:  ()=> buildContainersPage(),
    'my-boxes':  ()=> buildMyBlackBoxesPage(),
    'nouvelle-bn':()=> {openNewBoiteNoireModal(); return buildContainersPage();},
    sell:        ()=> buildSellPage(),
    companies:   ()=> buildCompaniesPage(),
    'clients-sa':()=> buildClientsPage(),
    'clients-own':()=> buildClientsPage(),
    drivers:     ()=> buildDriversPage(),
    stats:       ()=> buildStatsPage(),
    events:      ()=> buildEventsPage(),
    blockchain:  ()=> buildBlockchainPage(),
    blog:        ()=> buildBlogPage(),
    documents:   ()=> buildDocumentsPage(),
    archive:     ()=> showArchivePage(),
    settings:    ()=> buildSettingsPage(),
  };
  
  const result = (builders[page] || builders.dashboard)();
  
  // Handle async results (Promises)
  if (result && typeof result.then === 'function') {
    result.then(content => {
      c.innerHTML = content;
      populateContainerSelect('container-select');
      setTimeout(()=> initPageScripts(page), 60);
    }).catch(e => {
      console.error('Erreur rendu page:', e);
      c.innerHTML = `<div class="page active"><div class="card" style="color:red">Erreur: ${e.message}</div></div>`;
    });
  } else {
    c.innerHTML = result;
    populateContainerSelect('container-select');
    setTimeout(()=> initPageScripts(page), 60);
  }
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

    if (shouldSkipAutoRefresh()) return;

    if (currentPage === 'dashboard') {
        if (currentRole === 'superadmin' && typeof loadSADashboardData === 'function') {
            loadSADashboardData();
        } else if (currentRole === 'owner' && typeof loadOwnerDashboardData === 'function') {
            loadOwnerDashboardData();
        } else if (typeof refreshMapMarkers === 'function' && maps['map-main']) {
            refreshMapMarkers();
        }
        return;
    }

    if (currentPage === 'containers' && typeof updateContainerPageUI === 'function') {
        updateContainerPageUI();
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
    if (shouldDelayAutoRefreshRequest()) return true;
    if (hasStartedForm()) return true;
    return false;
}

function shouldDelayAutoRefreshRequest() {
    if (userInteractionActive) return true;
    const active = document.activeElement;
    if (active && ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName)) return true;
    if (document.querySelector('.modal-overlay')) return true;
    return false;
}

function hasStartedForm() {
    const page = document.querySelector('#pages-container .page.active');
    if (!page) return false;
    const fields = page.querySelectorAll('input, textarea, select');
    return Array.from(fields).some((field) => {
        if (field.disabled || field.readOnly) return false;
        const type = (field.type || '').toLowerCase();
        if (['button', 'submit', 'reset', 'hidden'].includes(type)) return false;
        if (field.closest('.topbar-search')) return false;
        const id = field.id || '';
        if (/search|filter/i.test(id) || field.placeholder === 'Rechercher…') return false;
        if (type === 'file') return field.files && field.files.length > 0;
        if (type === 'checkbox' || type === 'radio') return field.checked;
        return String(field.value || '').trim() !== '';
    });
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
        if (shouldDelayAutoRefreshRequest()) {
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
