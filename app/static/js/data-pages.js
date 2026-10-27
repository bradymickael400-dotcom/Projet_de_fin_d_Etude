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

// Container loading is handled below to keep the UI state consistent across pages.
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
    if(document.getElementById('new-cont-non-bic')?.checked) return;
    
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
      ? `Chaîne valide — ${data.total_blocks} blocs vérifiés`
      : `<i class="fas fa-exclamation-circle"></i> ${data.errors.length} erreurs détectées !`, data.valid ? 'success' : 'danger');
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
    <div class="page-header dashboard-page-header">
      <div><div class="dashboard-eyebrow">CENTRE DE SUPERVISION</div><div class="page-title">Vue d’ensemble <small>Flux opérationnels ARGOS</small></div></div>
      <div class="dashboard-header-actions">
        <span class="dashboard-data-note"><span class="dashboard-live-dot"></span>Données issues des API ARGOS</span>
        <button class="btn-icon dashboard-refresh" onclick="manualRefresh()" aria-label="Actualiser les données">
            <i class="fas fa-sync-alt"></i><span>Actualiser</span>
        </button>
      </div>
    </div>
    <div class="grid-4 dashboard-kpis">
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
    <div class="dashboard-primary-grid">
      <div class="card dashboard-map-card">
        <div class="card-header"><span class="card-title">Carte des positions disponibles</span>
          <button class="btn-icon" onclick="navigateTo('map')"><span>Ouvrir la carte</span></button>
        </div>
        <div class="map-container" style="height:280px"><div id="map-main"></div></div>
      </div>
      <div class="card dashboard-alerts-card">
        <div class="card-header"><span class="card-title">Alertes Récentes (BD)</span></div>
        <div id="dash-alertes-list" style="max-height:280px;overflow-y:auto">
          <div style="padding:20px;text-align:center;color:var(--text3)"><i class="fas fa-spinner fa-spin"></i> Chargement…</div>
        </div>
      </div>
    </div>
    <div class="grid-3 dashboard-secondary-grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Top 5 Conteneurs Critiques</span></div>
        <div id="dash-crit-containers" class="zone-scrollable"><div class="dashboard-empty">Chargement des données…</div></div>
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
    <div class="responsive-map-resource-layout" style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:20px">
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
    <div class="grid-2 responsive-map-resource-layout" style="margin-bottom:20px">
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
          <div class="sensor-tile" style="--sensor-color:var(--cyan)">
            <div class="sensor-unit"><i class="fas fa-ruler"></i></div>
            <div class="sensor-val">${c.distance ?? '--'}</div>
            <div class="sensor-label">Distance cm</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:var(--amber)">
            <div class="sensor-unit"><i class="fas fa-sun"></i></div>
            <div class="sensor-val">${c.light ?? '--'}</div>
            <div class="sensor-label">Luminosité ADC</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:var(--blue)">
            <div class="sensor-unit"><i class="fas fa-microphone"></i></div>
            <div class="sensor-val">${c.sound ?? '--'}</div>
            <div class="sensor-label">Son ADC</div>
          </div>
          <div class="sensor-tile" style="--sensor-color:${c.security_alarm?'var(--red)':'var(--green)'}">
            <div class="sensor-unit"><i class="fas fa-shield-alt"></i></div>
            <div class="sensor-val">${c.security_alarm?'ALARME':'OK'}</div>
            <div class="sensor-label">Sécurité distance</div>
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
  MAP_FILTER='all';
  return `
  <div class="page active">
    <div class="page-header">
      <div><div class="page-title">Carte GPS <small>Positions vérifiées</small></div><div id="map-data-status" class="map-data-status" role="status" aria-live="polite">Chargement des positions consolidées…</div></div>
      <button class="btn-secondary map-refresh-action" type="button" onclick="loadMapPositions()" aria-label="Actualiser les positions GPS" title="Actualiser les positions GPS"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20 7v5h-5M4 17v-5h5M5.6 9A7 7 0 0 1 18 6.8L20 12M4 12l2 5.2A7 7 0 0 0 18.4 15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="sr-only">Actualiser</span></button>
    </div>
    <div class="monitoring-map-layout" style="display:grid;gap:16px;height:calc(100vh - 180px)">
      <div class="card monitoring-map-panel" style="padding:0;overflow:hidden;position:relative">
        <div id="map-main" style="height:100%"></div>
        <div id="map-empty-overlay" class="map-empty-overlay" role="status"><strong>En attente de positions GPS</strong><span>Les marqueurs s’afficheront dès la réception de coordonnées consolidées.</span></div>
        <div class="map-overlay">
          <div class="map-legend">
            <div style="font-weight:600;margin-bottom:6px;letter-spacing:1px">LÉGENDE</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--cyan)"></div>Position GPS reçue</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--amber)"></div>Alerte signalée par l’API</div>
          </div>
        </div>
        <div class="map-controls">
          <button class="map-btn" id="map-view-all" type="button" onclick="showAllContainers()" title="Vue globale" aria-label="Vue globale"><span aria-hidden="true">◎</span></button>
          <button class="map-btn" type="button" onclick="toggleMapLayer()" title="Changer fond de carte" aria-label="Changer le fond de carte"><span aria-hidden="true">▧</span></button>
          <button class="map-btn" type="button" onclick="toggleTrails()" title="Traces GPS" aria-label="Afficher ou masquer les traces GPS" id="btn-trails"><span aria-hidden="true">↝</span></button>
          <button class="map-btn" id="map-fit-all" type="button" onclick="fitAllMarkers()" title="Centrer sur tous" aria-label="Centrer la carte sur toutes les positions"><span aria-hidden="true">⌖</span></button>
        </div>
      </div>
      <div class="monitoring-resources-panel" style="display:flex;flex-direction:column;gap:12px;overflow-y:auto">
        <div class="card" style="padding:12px">
          <div class="card-title" id="map-containers-title" style="margin-bottom:8px">Positions GPS (${MAP_GPS_POSITIONS.length})</div>
          <div style="position:relative;margin-bottom:8px">
            <i class="fas fa-search" style="position:absolute;left:10px;top:8px;color:var(--text3);font-size:12px"></i>
            <input type="text" placeholder="Rechercher…" style="width:100%;padding:6px 10px 6px 28px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);color:var(--text);font-size:12px;outline:none" oninput="filterContainersList(this.value)">
          </div>
          <div class="map-filter-group" role="group" aria-label="Filtrer les positions">
            <button type="button" data-map-filter="all" aria-pressed="true" onclick="filterMapPositions('all',this)">Toutes</button>
            <button type="button" data-map-filter="live" aria-pressed="false" onclick="filterMapPositions('live',this)">Récentes</button>
            <button type="button" data-map-filter="alert" aria-pressed="false" onclick="filterMapPositions('alert',this)">Alertes</button>
            <button type="button" data-map-filter="stale" aria-pressed="false" onclick="filterMapPositions('stale',this)">Anciennes</button>
          </div>
          <div id="map-filter-count" class="map-data-status" aria-live="polite"></div>
          <div id="containers-sidebar-list" class="zone-scrollable" style="max-height:35vh"><div class="map-empty-state">Aucune position GPS chargée.</div></div>
        </div>
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:8px">Données Live</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div class="sensor-tile" style="--sensor-color:var(--cyan);padding:10px">
              <div class="sensor-unit" style="font-size:10px"><i class="fas fa-thermometer-half"></i></div>
              <div class="sensor-val" style="font-size:20px" id="map-temp">—</div>
              <div class="sensor-label" style="font-size:10px">Temp</div>
            </div>
            <div class="sensor-tile" style="--sensor-color:var(--amber);padding:10px">
              <div class="sensor-unit" style="font-size:10px"><i class="fas fa-wave-square"></i></div>
              <div class="sensor-val" style="font-size:20px" id="map-shock">—</div>
              <div class="sensor-label" style="font-size:10px">Choc G</div>
            </div>
          </div>
        </div>
        <div class="card" style="padding:12px">
          <div class="card-title" style="margin-bottom:8px">Alertes Actives (BD)</div>
          <div id="map-alerts-list" class="zone-scrollable" style="max-height: 25vh;">
            <div class="map-empty-state">Chargement des alertes consolidées…</div>
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
        ${(currentRole === 'superadmin' || currentRole === 'owner') ? `<button class="btn-primary" style="width:auto;padding:9px 14px" onclick="openAddContainerModal()"><i class="fas fa-plus"></i> Ajouter</button>` : ''}
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

async function openAddContainerModal(){
  const companyField = currentRole === 'superadmin'
    ? `<div class="form-field"><label>Entreprise (optionnelle)</label><select id="new-cont-company" onchange="loadNewContainerBoxes()"><option value="">Sans entreprise</option></select><div style="font-size:11px;color:var(--text3);margin-top:6px">Laissez “Sans entreprise” pour enregistrer le conteneur seul.</div></div>`
    : `<div class="form-field"><label>Entreprise</label><input readonly value="Votre entreprise"></div>`;

  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:760px;max-height:90vh;overflow:auto">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-box"></i> Ajouter un conteneur</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            ${companyField}
            <div class="form-field"><label>Type de conteneur</label>
              <select id="new-cont-type">
                <option value="DRY">DRY</option>
                <option value="REEFER">REEFER</option>
                <option value="OPEN_TOP">OPEN TOP</option>
                <option value="FLAT_RACK">FLAT RACK</option>
                <option value="TANK">TANK</option>
                <option value="HIGH_CUBE">HIGH CUBE</option>
                <option value="OTHER">Autre</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Identifiant du conteneur</label>
              <input id="new-cont-id" placeholder="MSCU1234566" onblur="validateNewContainerBic()">
              <label style="display:flex;gap:8px;align-items:center;margin-top:8px;font-weight:400">
                <input id="new-cont-non-bic" type="checkbox" onchange="toggleNewContainerBicMode()"> Pas du BIC
              </label>
              <div id="new-cont-bic-msg" style="font-size:12px;color:var(--text3);margin-top:6px">Saisissez le numéro puis quittez le champ pour vérifier BIC.</div>
            </div>
            <div class="form-field"><label>Boîte noire à assigner</label>
              <select id="new-cont-box"><option value="">Aucune assignation</option></select>
              <div style="font-size:11px;color:var(--text3);margin-top:6px">Sans entreprise, seules les boîtes sans entreprise sont proposées. Vous pouvez aussi enregistrer sans assignation.</div>
            </div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Dimensions / périmètre</label><input id="new-cont-dimensions" placeholder="20ft, 40ft, 40HC..."></div>
            <div class="form-field"><label>Poids brut max (kg)</label><input id="new-cont-max-gross" type="number" min="0" placeholder="30480"></div>
            <div class="form-field"><label>Tare (kg)</label><input id="new-cont-tare" type="number" min="0" placeholder="2200"></div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Volume (m³)</label><input id="new-cont-capacity" type="number" min="0" step="0.01" placeholder="33.2"></div>
            <div class="form-field"><label>Année fabrication</label><input id="new-cont-year" type="number" min="1900" max="2100" placeholder="2024"></div>
            <div class="form-field"><label>Notes techniques</label><input id="new-cont-notes" placeholder="Isolation, portes, état..."></div>
          </div>
          <div id="new-cont-local-wrap" style="display:none;background:rgba(245,158,11,.12);border:1px solid var(--amber);border-radius:8px;padding:12px;color:var(--amber)">
            <i class="fas fa-exclamation-triangle"></i> Ce conteneur ne sera pas pris en charge en cas de déplacement dans une ligne maritime.
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" style="width:auto" id="new-cont-save" onclick="saveNewContainer()"><i class="fas fa-save"></i> Sauvegarder</button>
        </div>
      </div>
    </div>`;

  if(currentRole === 'superadmin'){
    await loadCompaniesData();
    const select = document.getElementById('new-cont-company');
    if(select){
      select.innerHTML = DB_COMPANIES.length
        ? '<option value="">Sans entreprise</option>' + DB_COMPANIES.map(c=>`<option value="${c.id}">${escapeHTML(c.nom_agence || c.login || c.id)}</option>`).join('')
        : '<option value="">Sans entreprise</option>';
    }
  }
  await loadNewContainerBoxes();
}

async function loadNewContainerBoxes(){
  const companyId = document.getElementById('new-cont-company')?.value || '';
  const select = document.getElementById('new-cont-box');
  if(!select) return;
  select.innerHTML = '<option value="">Chargement...</option>';
  try{
    let url = '/api/black-boxes/available-for-assignment';
    if(companyId) url += `?company_id=${encodeURIComponent(companyId)}`;
    const res = await secureApiFetch(url);
    const boxes = res.ok ? await res.json() : [];
    select.innerHTML = '<option value="">Aucune assignation</option>' + (Array.isArray(boxes) ? boxes.map(box=>`
      <option value="${box.id_boite}">${escapeHTML(box.label || box.numero_serie || box.id_boite)}</option>
    `).join('') : '');
  }catch(err){
    console.error(err);
    select.innerHTML = '<option value="">Aucune assignation</option>';
  }
}

async function validateNewContainerBic(){
  const input = document.getElementById('new-cont-id');
  const msg = document.getElementById('new-cont-bic-msg');
  const localWrap = document.getElementById('new-cont-local-wrap');
  if(!input || !msg) return;
  const value = input.value.trim().toUpperCase().replace(/[\s-]/g, '');
  input.value = value;
  localWrap.style.display = 'none';
  if(document.getElementById('new-cont-non-bic')?.checked) return toggleNewContainerBicMode();
  if(!value){
    msg.textContent = 'Saisissez le numéro puis quittez le champ pour vérifier BIC.';
    msg.style.color = 'var(--text3)';
    return;
  }
  const local = validateContainerNumber(value);
  if(!local.valid){
    msg.textContent = local.msg;
    msg.style.color = 'var(--red)';
    return;
  }
  msg.textContent = 'Vérification BIC/BoxTech...';
  msg.style.color = 'var(--cyan)';
  try{
    const res = await secureApiFetch('/api/container/validate', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({container_number:value, fetch_bic:true})
    });
    const data = await res.json();
    if(data.bic_specs){
      msg.textContent = 'Conteneur reconnu dans la BIC/BoxTech.';
      msg.style.color = 'var(--green)';
      fillNewContainerFromBic(data.bic_specs);
    }else{
      msg.textContent = data.bic_warning || 'Conteneur valide ISO, mais non reconnu dans la BIC/BoxTech.';
      msg.style.color = 'var(--amber)';
    }
  }catch(err){
    msg.textContent = 'BIC indisponible. Cochez usage local pour enregistrer sans ligne maritime.';
    msg.style.color = 'var(--amber)';
  }
  updateNewContainerSaveState();
}

function toggleNewContainerBicMode(){
  const nonBic = !!document.getElementById('new-cont-non-bic')?.checked;
  const msg = document.getElementById('new-cont-bic-msg');
  const warning = document.getElementById('new-cont-local-wrap');
  if(warning) warning.style.display = nonBic ? 'block' : 'none';
  if(msg){
    msg.textContent = nonBic ? 'Identifiant libre : aucune vérification BIC ne sera effectuée.' : 'Saisissez le numéro puis quittez le champ pour vérifier BIC.';
    msg.style.color = nonBic ? 'var(--amber)' : 'var(--text3)';
  }
  if(!nonBic && document.getElementById('new-cont-id')?.value) validateNewContainerBic();
}

function fillNewContainerFromBic(specs){
  const set = (id, value) => { const el = document.getElementById(id); if(el && value !== null && value !== undefined) el.value = value; };
  set('new-cont-dimensions', specs.type_code);
  set('new-cont-max-gross', specs.max_gross_mass_kg);
  set('new-cont-tare', specs.tare_mass_kg);
  set('new-cont-capacity', specs.capacity_m3);
  set('new-cont-year', specs.manufacture_year);
  const code = String(specs.type_code || '').toUpperCase();
  const type = code.charAt(2) === 'R' ? 'REEFER' : (code.charAt(1) === '5' ? 'HIGH_CUBE' : 'DRY');
  set('new-cont-type', type);
}

function updateNewContainerSaveState(){
  const btn = document.getElementById('new-cont-save');
  if(btn) btn.disabled = false;
}

async function saveNewContainer(){
  const companyId = document.getElementById('new-cont-company')?.value || '';
  const containerId = document.getElementById('new-cont-id')?.value.trim().toUpperCase().replace(/[\s-]/g, '') || '';
  if(!containerId) return showToast('Numéro conteneur requis.', 'warn');
  if(containerId.length < 4) return showToast('L’identifiant doit contenir au moins 4 caractères.', 'warn');
  const payload = {
    id_conteneurs: containerId,
    id_proprietaire: companyId || null,
    type_conteneurs: document.getElementById('new-cont-type')?.value || 'DRY',
    id_boite: document.getElementById('new-cont-box')?.value || null,
    non_bic: !!document.getElementById('new-cont-non-bic')?.checked,
    is_non_bic: !!document.getElementById('new-cont-non-bic')?.checked,
    bic_classification: document.getElementById('new-cont-non-bic')?.checked ? 'HORS_BIC' : 'BIC',
    technical_info: {
      dimensions: document.getElementById('new-cont-dimensions')?.value || '',
      max_gross_mass_kg: document.getElementById('new-cont-max-gross')?.value || '',
      tare_mass_kg: document.getElementById('new-cont-tare')?.value || '',
      capacity_m3: document.getElementById('new-cont-capacity')?.value || '',
      manufacture_year: document.getElementById('new-cont-year')?.value || '',
      notes: document.getElementById('new-cont-notes')?.value || '',
    }
  };
  try{
    const res = await secureApiFetch('/api/containers/create', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    });
    const data = await res.json().catch(()=>({}));
    if(res.status === 409 && data.code === 'BIC_CONFIRM_REQUIRED'){
      const wrap = document.getElementById('new-cont-local-wrap');
      if(wrap) wrap.style.display = 'flex';
      updateNewContainerSaveState();
      showToast(data.error, 'warn');
      return;
    }
    if(!res.ok) return showToast(data.error || 'Création conteneur impossible.', 'danger');
    showToast(data.bic_classification === 'HORS_BIC' ? 'Conteneur enregistré et classé Hors BIC.' : 'Conteneur BIC ajouté avec succès.', 'success');
    closeModal();
    await loadContainerData();
    renderPage('containers');
  }catch(err){
    console.error(err);
    showToast('Erreur réseau création conteneur.', 'danger');
  }
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
        <span style="font-family:var(--display);font-size:16px;color:var(--cyan)">${boxLabel(c)}</span>
      </div>
      <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}">${c.status.toUpperCase()}</span>
    </div>
    ${c.local_only || c.bic_classification === 'HORS_BIC' ? `
      <div style="margin-bottom:8px">
        <span class="badge badge-danger" title="Ce conteneur n’est pas enregistré dans BIC/BoxTech"><i class="fas fa-times-circle"></i> HORS BIC</span>
      </div>` : ''}
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
    ${(currentRole === 'superadmin' || currentRole === 'owner') ? `
      <div style="display:flex;justify-content:flex-end;margin-top:10px">
        <button class="btn-icon" style="color:var(--red)" onclick="event.stopPropagation();deleteContainerAccount('${escapeHTML(c.id_conteneurs || c.id || c.id_boite)}')">
          <i class="fas fa-trash"></i> Supprimer
        </button>
      </div>` : ''}
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

function updateMapPageUI(){
  const hasPositions=MAP_GPS_POSITIONS.length>0;
  const emptyOverlay=document.getElementById('map-empty-overlay');
  if(emptyOverlay) emptyOverlay.hidden=hasPositions;
  ['map-view-all','map-fit-all','btn-trails'].forEach(id=>{
    const control=document.getElementById(id);
    if(control){
      control.disabled=!hasPositions;
      if(id==='btn-trails'){
        control.style.background=trailsOn?'var(--cyan)':'';
        control.setAttribute('aria-pressed',String(trailsOn));
      }
    }
  });
  if(currentPage !== 'map') return;
  const title = document.getElementById('map-containers-title');
  if(title) title.textContent = `Positions GPS (${MAP_GPS_POSITIONS.length})`;
  const status = document.getElementById('map-data-status');
  if(status && !status.dataset.error) status.textContent = MAP_GPS_POSITIONS.length
    ? `${MAP_GPS_POSITIONS.length} position(s) reçue(s) de l’API consolidée`
    : 'Aucune position GPS disponible dans les données consolidées.';

  const list = document.getElementById('containers-sidebar-list');
  if(list){
    list.innerHTML = MAP_GPS_POSITIONS.length ? MAP_GPS_POSITIONS.map(c=>{
      const id = escapeHTML(String(c.id_boite));
      const state = mapPositionState(c);
      const stateLabel = state==='alert' ? 'Alerte' : state==='stale' ? 'Position ancienne' : 'Position récente';
      return `<button class="map-position-item" type="button" onclick="focusContainerDB('${id}')">
        <span class="map-position-dot state-${state}" aria-hidden="true"></span>
        <div class="container-info">
          <span class="container-id">${escapeHTML(String(c.numero_serie || c.id_boite))}</span>
          <span class="map-position-meta">${stateLabel} · ${Number.isFinite(c.speed) ? `${c.speed} km/h` : 'Vitesse indisponible'} · ${escapeHTML(formatTime(c.ts))}</span>
        </div>
      </button>`;
    }).join('') : '<div style="color:var(--text3);font-size:12px">Aucune position GPS disponible.</div>';
    applyMapPositionFilters();
  }

  const temp = document.getElementById('map-temp');
  if(temp) temp.textContent = MAP_GPS_POSITIONS.find(c=>c.temp!=null)?.temp ?? '—';
  const shock = document.getElementById('map-shock');
  if(shock) shock.textContent = MAP_GPS_POSITIONS.find(c=>c.shock!=null)?.shock ?? '—';

  const alerts = document.getElementById('map-alerts-list');
  if(alerts){
    alerts.innerHTML = MAP_GPS_POSITIONS.filter(c=>c.alerts?.length).slice(0,8).map(c=>
      c.alerts.slice(0,2).map(a=>`
        <div class="timeline-item" style="padding:5px 0">
          <div class="timeline-dot" style="background:var(--amber)"></div>
          <div class="timeline-content">
            <div style="font-size:12px">${escapeHTML(String(c.id_boite))}: ${escapeHTML(String(a).substring(0,120))}</div>
            <div class="timeline-time">${escapeHTML(formatTime(c.ts))}</div>
          </div>
        </div>`).join('')
    ).join('') || '<div style="color:var(--text3);font-size:12px">Aucune alerte sur les dernières positions.</div>';
  }
  refreshMapMarkers();
}

function mapPositionState(position){
  if(position.alerts?.length) return 'alert';
  const stamp=Date.parse(position.ts || position.timestamp || '');
  const age=Date.now()-stamp;
  return Number.isFinite(stamp) && age>=0 && age<=15*60*1000 ? 'live' : 'stale';
}

function filterMapPositions(status,button){
  MAP_FILTER=status;
  document.querySelectorAll('[data-map-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
  applyMapPositionFilters();
  refreshMapMarkers();
  syncMapTrails();
}

function applyMapPositionFilters(){
  const search=document.querySelector('#containers-sidebar-list')?.parentElement?.querySelector('input')?.value?.toLowerCase() || '';
  let visible=0;
  document.querySelectorAll('#containers-sidebar-list .map-position-item').forEach(item=>{
    const state=item.querySelector('.map-position-dot')?.className || '';
    const matchesState=MAP_FILTER==='all' || state.includes(`state-${MAP_FILTER}`);
    const matchesSearch=!search || item.textContent.toLowerCase().includes(search);
    item.hidden=!(matchesState && matchesSearch);
    if(!item.hidden) visible++;
  });
  const count=document.getElementById('map-filter-count');
  if(count) count.textContent=`${visible} position(s) affichée(s) sur ${MAP_GPS_POSITIONS.length}`;
}

// +++++++++++++++++++++++++++++ vide le conteneurs

async function showContainerDetailDB(id){
  const c = DB_CONTAINERS.find(x=>String(x.id_boite)===String(id) || String(x.id)===String(id));
  if(!c){ showToast('Conteneur introuvable','warn'); return; }

  // Charger seuils depuis BD
  let seuils = {};
  try {
    const sr = await secureApiFetch(`/api/config/thresholds/${c.id_boite||c.id}`);
    seuils = await sr.json();
  } catch(e){}

  // Historique events
  let evts = [];
  try {
    const er = await secureApiFetch(`/api/events?container=${c.id_boite||c.id}&limit=10`);
    evts = await er.json();
  } catch(e){}

  const hasData = c.temp !== null && c.temp !== undefined;
  const containerId = c.id_conteneurs || c.id || c.id_boite || '';
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:920px; width:50vw;max-height:90vh;overflow-y:auto">
        <div class="modal-header">
          <div>
            <div class="modal-title" style="font-family:var(--display);color:var(--cyan)">${boxLabel(c)}</div>
            <div style="font-size:12px;color:var(--text3)">${c.type_conteneurs||'—'} • ${c.type_boite||'—'} • v${c.versions||'?'}</div>
          </div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
            <span class="badge badge-${c.status==='ok'?'ok':c.status==='warning'?'warn':c.status==='danger'?'danger':'off'}">${c.status.toUpperCase()}</span>
            ${c.local_only || c.bic_classification === 'HORS_BIC' ? '<span class="badge badge-danger"><i class="fas fa-times-circle"></i> HORS BIC</span>' : '<span class="badge badge-ok"><i class="fas fa-check-circle"></i> BIC</span>'}
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
              ['fa-ruler','Distance',(c.distance??'--')+' cm',c.security_alarm?'var(--red)':'var(--green)'],
              ['fa-sun','Luminosité',c.light??'--','var(--amber)'],
              ['fa-microphone','Niveau sonore',c.sound??'--','var(--blue)'],
              ['fa-fire','Flamme',c.flame_detected?'DÉTECTÉE':'Non',c.flame_detected?'var(--red)':'var(--green)'],
              ['fa-door-open','Ouverture',c.door_open?'OUVERTE':'Fermée',c.door_open?'var(--red)':'var(--green)'],
              ['fa-arrows-alt','Accélération',
                c.acceleration_x==null?'—':`${Number(c.acceleration_x).toFixed(1)} / ${Number(c.acceleration_y).toFixed(1)} / ${Number(c.acceleration_z).toFixed(1)}`,
                'var(--cyan)'],
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
          ${c.id_boite ? `
            <div style="margin-top:12px;padding:12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--card2)">
              <div style="font-size:12px;color:var(--text3);margin-bottom:8px">Contrôle ESP32</div>
              <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
                ${[
                  ['security','Sécurité','fa-shield-alt'],
                  ['listening','Écoute','fa-headphones'],
                  ['flame-detection','Détection de flammes','fa-fire']
                ].map(([command,label,icon])=>`
                  <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg3)">
                    <div>
                      <div style="font-size:12px;font-weight:600"><i class="fas ${icon}"></i> ${label}</div>
                      <div style="font-size:11px;color:var(--text3)">Activer / désactiver</div>
                    </div>
                    <label class="toggle-switch">
                      <input type="checkbox"
                        ${(command==='security' && !['superadmin','owner','company'].includes(currentRole)) ? 'disabled title="Réservé aux gestionnaires"' : ''}
                        onchange="sendContainerCommand('${c.id_boite}', '${command}', this.checked)">
                      <span class="toggle-slider"></span>
                    </label>
                  </div>`).join('')}
              </div>
            </div>` : ''}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          <button class="btn-primary" style="background:var(--red)" onclick="viderContainer('${c.id_boite}')">
              <i class="fas fa-trash-alt"></i> Destockage
          </button>
          <button class="btn-secondary" onclick="downloadProtectedDocument('/api/containers/${encodeURIComponent(containerId)}/report','rapport_${escapeHTML(containerId)}.pdf')"><i class="fas fa-file-pdf"></i> Export PDF</button>
          <button class="btn-primary" style="width:auto" onclick="closeModal();navigateTo('map')"><i class="fas fa-map-marker-alt"></i> Voir Carte</button>
          <button class="btn-primary" style="width:auto" onclick="openEventsForContainer('${escapeHTML(c.id_boite||c.id)}')"><i class="fas fa-list"></i> Événements</button>
          <button class="btn-secondary" style="width:auto" onclick="showRegulatoryHistory('${escapeHTML(c.id_boite||c.id)}')"><i class="fas fa-scale-balanced"></i> Dossier & références</button>
          <button class="export-btn" onclick="openAIAssistant('${c.id_boite||c.id}')"><i class="fas fa-robot"></i> Rapport IA</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

async function showRegulatoryHistory(boxId){
  const root=document.getElementById('modal-root');
  if(!root)return;
  root.innerHTML='<div class="modal-overlay"><div class="modal" style="max-width:900px"><div class="modal-body">Chargement de l’historique sourcé…</div></div></div>';
  try{
    const response=await secureApiFetch(`/api/regulatory/history?box_id=${encodeURIComponent(boxId)}`);
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Historique indisponible');
    const history=Array.isArray(data.history)?data.history:[];
    root.innerHTML=`<div class="modal-overlay" onclick="if(event.target===this)closeModal()"><div class="modal" style="max-width:900px;width:min(900px,94vw);max-height:90vh;overflow:auto">
      <div class="modal-header"><div><div class="modal-title">Dossier de décisions · Boîte ${escapeHTML(boxId)}</div><div style="font-size:12px;color:var(--text3)">Actions, réactions IA et références documentaires</div></div><button class="modal-close" onclick="closeModal()">×</button></div>
      <div class="modal-body">${history.length?history.map(item=>{
        const sources=(item.sources||[]).map(source=>{
          const url=String(source.official_url||'');
          const safeUrl=url.startsWith('https://')?url:null;
          return `<div style="padding:10px;margin-top:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg3)"><strong>${escapeHTML(source.title||source.source_key)}</strong><div style="font-size:11px;color:var(--text3);margin:4px 0">${escapeHTML(source.authority||'')} · ${escapeHTML(source.jurisdiction||'')} · ${escapeHTML(source.legal_status||'')}</div><div style="font-size:12px">${escapeHTML(source.applicability_conditions||source.summary||'')}</div>${safeUrl?`<a href="${escapeHTML(safeUrl)}" target="_blank" rel="noopener noreferrer">Source officielle ↗</a>`:'<span style="color:var(--text3)">Règle interne ARGOS; aucune loi externe citée.</span>'}<div style="font-size:11px;color:var(--amber);margin-top:4px">Applicabilité dans ce dossier : ${escapeHTML(item.applicability_status||'À vérifier')}</div></div>`;
        }).join('');
        const remarks=item.ai_remarks&&Object.keys(item.ai_remarks).length?`<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--cyan)">Remarques et éléments de décision</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;color:var(--text3);padding:8px;background:var(--bg3);border-radius:6px">${escapeHTML(JSON.stringify(item.ai_remarks,null,2))}</pre></details>`:'';
        return `<article style="padding:14px 0;border-bottom:1px solid var(--border)"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><strong>${escapeHTML(item.action||item.event_type)}</strong><time style="font-size:11px;color:var(--text3)">${item.created_at?new Date(item.created_at).toLocaleString('fr-FR'):'—'}</time></div><div style="margin-top:7px"><b>Réaction / résultat :</b> ${escapeHTML(item.reaction||'—')}</div><div style="margin-top:5px;font-size:12px;color:var(--text3)">Acteur ${escapeHTML(item.actor_role||'—')} · ${escapeHTML(item.actor_id||'—')} · ${escapeHTML(item.event_type||'')}</div>${item.trace_id?`<div style="font-size:11px;color:var(--text3)">Trace IA ${escapeHTML(item.trace_id)}</div>`:''}${remarks}<div style="margin-top:10px"><b>Références :</b>${sources||'<div style="color:var(--amber);margin-top:4px">Aucune source liée à cette entrée.</div>'}</div></article>`;
      }).join(''):'<div style="padding:20px;color:var(--text3)">Aucune action historisée pour cette boîte.</div>'}</div>
      <div class="modal-footer"><span style="font-size:11px;color:var(--text3)">Une référence n’implique pas que la règle soit applicable. Vérification humaine requise selon juridiction et opération.</span><button class="btn-secondary" onclick="closeModal()">Fermer</button></div>
    </div></div>`;
  }catch(error){root.innerHTML=`<div class="modal-overlay" onclick="if(event.target===this)closeModal()"><div class="modal"><div class="modal-body"><div class="alert alert-warn">${escapeHTML(error.message)}</div><button class="btn-secondary" onclick="closeModal()">Fermer</button></div></div></div>`;}
}

async function downloadProtectedDocument(url, filename){
  const response = await secureApiFetch(url);
  if(!response.ok){
    const data = await response.json().catch(()=>({}));
    return showToast(data.error || 'Téléchargement impossible','error');
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl; link.download = filename || 'document.pdf';
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);
}

function openDeleteConfirmModal({title, message, details='', confirmLabel='Supprimer', onConfirm}) {
  const action = typeof onConfirm === 'string' ? onConfirm : '';
  const safeAction = escapeHTML(action);
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:520px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-triangle-exclamation" style="color:var(--red)"></i> ${escapeHTML(title)}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <p style="color:var(--text2);line-height:1.5;margin-bottom:14px">${escapeHTML(message)}</p>
          ${details ? `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px;color:var(--text3);font-size:12px;line-height:1.5">${details}</div>` : ''}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-danger" onclick="${safeAction}">
            <i class="fas fa-trash"></i> ${escapeHTML(confirmLabel)}
          </button>
        </div>
      </div>
    </div>`;
}

function buildDocumentsPage(){
  setTimeout(loadDocumentsPage,0);
  return `<div class="page active">
    <div class="page-header"><div class="page-title">Dossiers <small>Documents autorisés</small></div></div>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Contrats</div><div class="stat-value" id="docs-contracts">0</div></div>
      <div class="stat-card"><div class="stat-label">Inventaires</div><div class="stat-value" id="docs-inventories">0</div></div>
      <div class="stat-card"><div class="stat-label">Rapports</div><div class="stat-value" id="docs-reports">0</div></div>
    </div>
    <br>
    <br>
    <div class="card"><div class="card-header"><span class="card-title">Documents disponibles</span></div>
      <div class="table-wrap"><table><thead><tr><th>Catégorie</th><th>Référence</th><th>Titre</th><th>État</th><th>Date</th><th>Action</th></tr></thead>
      <tbody id="documents-tbody"><tr><td colspan="6">Chargement…</td></tr></tbody></table></div>
    </div></div>`;
}

async function loadDocumentsPage(){
  const response = await secureApiFetch('/api/documents');
  const data = await response.json().catch(()=>[]);
  const tbody = document.getElementById('documents-tbody');
  if(!response.ok){ tbody.innerHTML=`<tr><td colspan="6">${escapeHTML(data.error||'Erreur')}</td></tr>`; return; }
  const counts={CONTRACT:0,INVENTORY:0,REPORT:0}; data.forEach(d=>counts[d.category]=(counts[d.category]||0)+1);
  document.getElementById('docs-contracts').textContent=counts.CONTRACT||0;
  document.getElementById('docs-inventories').textContent=counts.INVENTORY||0;
  document.getElementById('docs-reports').textContent=counts.REPORT||0;
  tbody.innerHTML=data.length?data.map(d=>`<tr><td>${escapeHTML(d.category)}</td><td>${escapeHTML(d.reference)}</td>
    <td>${escapeHTML(d.title)}</td><td>${escapeHTML(d.status)}</td><td>${new Date(d.created_at).toLocaleDateString('fr-FR')}</td>
    <td><button class="btn-icon" onclick="downloadProtectedDocument('${d.download_url}','${escapeHTML(d.reference)}.pdf')">Télécharger</button></td></tr>`).join(''):
    '<tr><td colspan="6">Aucun document disponible</td></tr>';
}

async function sendContainerCommand(idBoite, command, enabled) {
  try {
    const body = command === 'request-position' ? {} : { enabled };
    // La géolocalisation vient du téléphone/ordinateur avec consentement.
    // Elle sert uniquement de secours quand le GPS ESP32 publie 0,0.
    if (['security','listening','recording'].includes(command) && typeof argosDirectGrantedPosition === 'function') {
      const position = await argosDirectGrantedPosition();
      if (position) Object.assign(body, position);
    }
    if (command === 'listening' && enabled) body.durationSeconds = 300;
    if (command === 'recording' && enabled) body.durationSeconds = 300;
    const res = await secureApiFetch(`/api/black-boxes/${encodeURIComponent(idBoite)}/commands/${command}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) return showToast(data.error || 'Commande refusée', 'error');
    showToast(`Commande ${data.command?.status || 'envoyée'}: ${data.command?.commandUid || ''}`, 'success');
    if (command === 'listening') {
      const bridge = window.argosDirectBridge;
      const directSessionActive = bridge?.running && String(bridge.boxId) === String(idBoite);
      if (enabled && directSessionActive && bridge.audioRecorder?.state !== 'recording') {
        await startArgosDirectAudioRecording(Number(idBoite));
      } else if (!enabled && bridge?.audioRecorder?.state === 'recording') {
        stopArgosDirectAudioRecording();
      } else if (enabled && !directSessionActive) {
        showToast('Écoute activée. Pour créer un fichier sonore, démarrez la connexion Wi-Fi directe : le microphone actuel détecte seulement un seuil et ne fournit pas de flux audio.', 'warn');
      }
    }
  } catch (e) {
    showToast('Erreur commande: ' + e.message, 'error');
  }
}

function openEventsForContainer(containerOrBoxId) {
  window.argosPreselectedContainer = containerOrBoxId;
  closeModal();
  navigateTo('events');
  setTimeout(() => {
    const selects = document.querySelectorAll('select');
    selects.forEach(sel => {
      const opt = Array.from(sel.options || []).find(o => String(o.value) === String(containerOrBoxId));
      if (opt) {
        sel.value = opt.value;
        sel.dispatchEvent(new Event('change'));
      }
    });
  }, 200);
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
    <div class="sell-layout" style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="sell-form-panel">
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
            <div class="form-field"><label>Durée du contrat (mois)</label>
              <input type="number" id="sell-contract-months" min="1" value="12">
            </div>
          </div>
          <div class="form-row">
            <div class="form-field"><label>Début du contrat</label><input type="date" id="sell-contract-start"></div>
            <div class="form-field"><label>Fin calculée</label><input type="text" id="sell-contract-end" readonly></div>
          </div>
          <div class="alert alert-info">Le contrat ARGOS sera généré automatiquement et devra être accepté par l’entreprise.</div>
          <button class="btn-primary" onclick="submitSale()"><i class="fas fa-check"></i> Valider la Vente & Créer le Compte</button>
        </div>
      </div>
      <div class="sell-map-panel">
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
    <td>
      <button class="btn-icon" onclick="showCompanyDetailDB(${e.id})">Profil</button>
      <button class="btn-icon" onclick="showCompanyDocuments(${e.id})"><i class="fas fa-file-alt"></i> Documents</button>
      <button class="btn-icon" style="color:var(--red)" onclick="deleteCompanyAccount(${e.id})"><i class="fas fa-trash"></i> Supprimer compte</button>
    </td>
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
    <div class="docs-stats-row" style="margin-bottom:16px">
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
          <button class="btn-secondary" onclick="showCompanyDocuments(${e.id})"><i class="fas fa-file-alt"></i> Documents</button>
          <button class="btn-secondary" onclick="openEditCompanyModal(${e.id})"><i class="fas fa-edit"></i> Modifier</button>
          <button class="btn-secondary" style="color:var(--red)" onclick="deleteCompanyAccount(${e.id})"><i class="fas fa-trash"></i> Supprimer compte</button>
          <button class="btn-primary" style="width:auto" onclick="navigateTo('blockchain');closeModal()"><i class="fas fa-link"></i> Données Scellées</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

async function showCompanyDocuments(id){
  const e = DB_COMPANIES.find(c=>c.id===id);
  try{
    const res = await secureApiFetch(`/api/companies/${encodeURIComponent(id)}/documents`);
    const docs = res.ok ? await res.json() : [];
    const rows = docs.length ? docs.map(doc=>`
      <tr>
        <td>${escapeHTML(doc.title||'Document')}</td>
        <td>${escapeHTML(doc.reference||'—')}</td>
        <td><span class="badge badge-info">${escapeHTML(doc.status||'—')}</span></td>
        <td>${doc.created_at ? new Date(doc.created_at).toLocaleDateString('fr-FR') : '—'}</td>
        <td><button class="btn-icon" onclick="downloadProtectedDocument('${escapeHTML(doc.download_url)}','${escapeHTML(doc.reference||doc.uid||'document')}.pdf')"><i class="fas fa-download"></i> Télécharger</button></td>
      </tr>`).join('') : '<tr><td colspan="5" style="text-align:center;color:var(--text3)">Aucun document lié</td></tr>';
    document.getElementById('modal-root').innerHTML = `
      <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
        <div class="modal" style="max-width:760px">
          <div class="modal-header"><div class="modal-title">Documents - ${escapeHTML(e?.nom_agence||'Entreprise')}</div>
            <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button></div>
          <div class="modal-body">
            <table class="data-table">
              <thead><tr><th>Titre</th><th>Référence</th><th>Statut</th><th>Date</th><th>Action</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" onclick="showCompanyDetailDB(${id})">Retour profil</button>
            <button class="btn-primary" style="width:auto" onclick="closeModal()">Fermer</button>
          </div>
        </div>
      </div>`;
  }catch(err){
    console.error(err);
    showToast('Impossible de charger les documents','danger');
  }
}

async function deleteCompanyAccount(id){
  const e = DB_COMPANIES.find(c=>String(c.id)===String(id));
  const name = e?.nom_agence || `entreprise #${id}`;
  openDeleteConfirmModal({
    title: 'Supprimer compte entreprise',
    message: `Supprimer le compte ${name} ? Cette action désactive ses abonnements actifs et libère toutes les boîtes liées.`,
    details: '<i class="fas fa-link"></i> La suppression sera enregistrée dans la blockchain ARGOS.',
    confirmLabel: 'Supprimer le compte',
    onConfirm: `confirmDeleteCompanyAccount(${JSON.stringify(String(id))})`
  });
}

async function confirmDeleteCompanyAccount(id){
  try{
    const res = await secureApiFetch(`/api/companies/${encodeURIComponent(id)}`, {
      method:'DELETE',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({reason:'Suppression depuis gestion entreprises'})
    });
    const d = await res.json().catch(()=>({}));
    if(!res.ok){
      showToast(d.error || 'Erreur lors de la suppression du compte', 'danger');
      return;
    }
    const count = Array.isArray(d.boites_liberees) ? d.boites_liberees.length : 0;
    showToast(`Compte supprimé. ${count} boîte(s) libérée(s).`, 'success');
    closeModal();
    await loadCompaniesData();
    renderCompaniesTable();
    if(typeof loadContainerData === 'function') loadContainerData();
  }catch(err){
    console.error(err);
    showToast('Erreur réseau lors de la suppression', 'danger');
  }
}

async function deleteContainerAccount(id){
  openDeleteConfirmModal({
    title: 'Supprimer conteneur',
    message: `Supprimer le conteneur ${id} ? Le conteneur passera hors ligne et les boîtes liées seront libérées.`,
    details: '<i class="fas fa-link"></i> Un événement de suppression sera scellé dans la blockchain.',
    confirmLabel: 'Supprimer le conteneur',
    onConfirm: `confirmDeleteContainerAccount(${JSON.stringify(String(id))})`
  });
}

async function confirmDeleteContainerAccount(id){
  try{
    const res = await secureApiFetch(`/api/containers/${encodeURIComponent(id)}`, { method:'DELETE' });
    const d = await res.json().catch(()=>({}));
    if(!res.ok){
      showToast(d.error || 'Erreur lors de la suppression du conteneur', 'danger');
      return;
    }
    showToast(d.message || 'Conteneur supprimé.', 'success');
    closeModal();
    await loadContainerData();
    renderPage('containers');
  }catch(err){
    console.error(err);
    showToast('Erreur réseau lors de la suppression du conteneur', 'danger');
  }
}

async function deleteClientAccount(id){
  const c = DB_CLIENTS.find(x=>String(x.id_cni)===String(id));
  const name = c ? `${c.nom || ''} ${c.prenom || ''}`.trim() || id : id;
  openDeleteConfirmModal({
    title: 'Supprimer compte client',
    message: `Supprimer le compte client ${name} ? Ses abonnements actifs seront désactivés.`,
    details: '<i class="fas fa-link"></i> Cette suppression sera enregistrée dans la blockchain ARGOS.',
    confirmLabel: 'Supprimer le client',
    onConfirm: `confirmDeleteClientAccount(${JSON.stringify(String(id))})`
  });
}

async function confirmDeleteClientAccount(id){
  try{
    const res = await secureApiFetch(`/api/clients/${encodeURIComponent(id)}`, {
      method:'DELETE',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({reason:'Suppression depuis gestion clients'})
    });
    const d = await res.json().catch(()=>({}));
    if(!res.ok){
      showToast(d.error || 'Erreur lors de la suppression du client', 'danger');
      return;
    }
    showToast(d.message || 'Compte client supprimé.', 'success');
    closeModal();
    await loadClientsData();
    renderClientsTable();
  }catch(err){
    console.error(err);
    showToast('Erreur réseau lors de la suppression du client', 'danger');
  }
}

async function deleteDriverAccount(id){
  const d = DB_DRIVERS.find(x=>String(x.id_cni)===String(id));
  const name = d ? `${d.nom || ''} ${d.prenom || ''}`.trim() || id : id;
  openDeleteConfirmModal({
    title: 'Supprimer compte chauffeur',
    message: `Supprimer le compte chauffeur ${name} ? Ses liaisons aux conteneurs seront retirées.`,
    details: '<i class="fas fa-link"></i> Cette suppression sera enregistrée dans la blockchain ARGOS.',
    confirmLabel: 'Supprimer le chauffeur',
    onConfirm: `confirmDeleteDriverAccount(${JSON.stringify(String(id))})`
  });
}

async function confirmDeleteDriverAccount(id){
  try{
    const res = await secureApiFetch(`/api/drivers/${encodeURIComponent(id)}`, {
      method:'DELETE',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({reason:'Suppression depuis gestion chauffeurs'})
    });
    const data = await res.json().catch(()=>({}));
    if(!res.ok){
      showToast(data.error || 'Erreur lors de la suppression du chauffeur', 'danger');
      return;
    }
    showToast(data.message || 'Compte chauffeur supprimé.', 'success');
    closeModal();
    await loadDriversData();
    renderDriversTable();
  }catch(err){
    console.error(err);
    showToast('Erreur réseau lors de la suppression du chauffeur', 'danger');
  }
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
          <thead><tr><th>Client</th><th>Login</th><th>Conteneur/Boîte</th><th>Marchandises</th><th>Destination</th><th>Valeur colis</th><th>Action</th></tr></thead>
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
      <div class="card" style="margin-bottom:16px">
        <div class="card-header"><span class="card-title">Seuils souhaités</span></div>
        <div class="form-row">
          <div class="form-field"><label>Température min.</label><input type="number" step="0.1" id="new-th-temp-min" value="-10"></div>
          <div class="form-field"><label>Température max.</label><input type="number" step="0.1" id="new-th-temp-max" value="32"></div>
          <div class="form-field"><label>Humidité min.</label><input type="number" step="0.1" id="new-th-humi-min" value="20"></div>
          <div class="form-field"><label>Humidité max.</label><input type="number" step="0.1" id="new-th-humi-max" value="75"></div>
        </div><div class="form-row">
          <div class="form-field"><label>Choc max. (G)</label><input type="number" step="0.1" id="new-th-shock-max" value="5"></div>
          <div class="form-field"><label>Pression min.</label><input type="number" step="0.1" id="new-th-pressure-min" value="995"></div>
          <div class="form-field"><label>Pression max.</label><input type="number" step="0.1" id="new-th-pressure-max" value="1050"></div>
        </div>
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
      <td><span class="tag">${escapeHTML((c.cargo_names||[]).join(', ')||'—')}</span></td>
      <td>${escapeHTML((c.destinations||[]).join(', ')||'—')}</td>
      <td style="font-family:var(--mono);font-size:12px">${Number(c.cargo_value||0).toLocaleString()} CFA</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn-icon" onclick="showClientDetailDB('${c.id_cni}')">Profil</button>
          ${(currentRole === 'superadmin' || currentRole === 'owner') ? `<button class="btn-icon" style="color:var(--red)" onclick="deleteClientAccount('${escapeHTML(c.id_cni)}')"><i class="fas fa-trash"></i></button>` : ''}
        </div>
      </td>
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
          ${(currentRole === 'superadmin' || currentRole === 'owner') ? `<button class="btn-danger" onclick="deleteClientAccount('${escapeHTML(c.id_cni)}')"><i class="fas fa-trash"></i> Supprimer</button>` : ''}
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
    tbody.innerHTML = DB_DRIVERS.map(d=>{
      const boites = (() => {
        if (Array.isArray(d.boites)) return d.boites;
        if (typeof d.boites === 'string' && d.boites.trim()) return [d.boites.trim()];
        if (typeof d.id_boites === 'string' && d.id_boites.trim()) {
          try {
            const parsed = JSON.parse(d.id_boites);
            if (Array.isArray(parsed)) return parsed;
          } catch(e) {}
        }
        return d.id_boite ? [d.id_boite] : [];
      })().filter(Boolean);
      return `<tr>
      <td><div style="font-weight:600">${d.nom_chauffeurs || (d.nom ? `${d.nom} ${d.prenom||''}`.trim() : '—')}</div></td>
      <td style="font-size:12px">${d.id_cni||'—'}</td>
      <td style="font-size:12px">${d.login||'—'}</td>
      <td style="font-size:12px">${boites.length ? boites.map(escapeHTML).join(', ') : 'Aucun'}</td>
      <td style="font-size:12px">${d.blocked ? '<span class="badge badge-danger">Bloqué</span>' : (d.moyen_transport||'—')}</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn-icon" onclick="openDriverProfileModal('${d.id_cni}')"><i class="fas fa-user"></i></button>
          <button class="btn-icon" onclick="openDriverMessageModal('${d.id_cni}')"><i class="fas fa-envelope"></i></button>
          <button class="btn-icon" onclick="openDriverManageModal('${d.id_cni}')"><i class="fas fa-cogs"></i></button>
          ${(currentRole === 'superadmin' || currentRole === 'owner') ? `<button class="btn-icon" style="color:var(--red)" onclick="deleteDriverAccount('${escapeHTML(d.id_cni)}')"><i class="fas fa-trash"></i></button>` : ''}
          <button class="btn-icon" onclick="navigateTo('containers')">Détails</button>
        </div>
      </td>
    </tr>`;
    }).join('');
  }

  const totalEl = document.getElementById('drv-total');
  if(totalEl) totalEl.textContent = DB_DRIVERS.length + ' Enregistrés';
}

// ══════════════════════════════════════════════════════
//  STATS PAGE
// ══════════════════════════════════════════════════════
let statsRequestId = 0;
let statsLiveRequestId = 0;
let statsDeviceSummaries = [];
let statsLatestTelemetry = [];
let statsLiveRefreshTimer = null;

function buildStatsPage(){
  return `
  <div class="page active">
    <div class="page-header">
      <div class="page-title">Statistiques & Analytiques <small>Temps Réel</small></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <select id="stats-boite-select" aria-label="Filtrer par boîte" onchange="onStatsBoxChange()"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Toutes les boîtes</option>
        </select>
        <select id="stats-device-select" aria-label="Filtrer la télémétrie par appareil" onchange="loadStatsLiveTelemetry()" disabled
          title="Ce filtre s'applique aux dernières mesures ESP32"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="">Tous les appareils</option>
        </select>
        <select id="stats-period-select" aria-label="Choisir la période" onchange="loadDynamicStats(this.value)"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="5h">5 dernières heures</option>
          <option value="24h">24 dernières heures</option>
          <option value="7d" selected>7 derniers jours</option>
          <option value="30d">30 derniers jours</option>
          <option value="3m">3 derniers mois</option>
          <option value="all">Tous</option>
        </select>
        <select id="stats-live-sort" aria-label="Trier les dernières mesures" onchange="loadStatsLiveTelemetry()"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:6px 10px;color:var(--text);font-size:13px;outline:none">
          <option value="timestamp_desc">Plus récentes</option>
          <option value="timestamp_asc">Plus anciennes</option>
          <option value="box_asc">Boîte (A–Z)</option>
          <option value="device_asc">Device UID (A–Z)</option>
          <option value="sequence_desc">Séquence décroissante</option>
          <option value="temperature_desc">Température décroissante</option>
          <option value="shock_desc">Choc décroissant</option>
          <option value="battery_asc">Batterie croissante</option>
          <option value="alerts_desc">Alertes décroissantes</option>
        </select>
        <button class="btn-icon" onclick="loadDynamicStats(document.getElementById('stats-period-select')?.value || '7d')" title="Actualiser les statistiques"><i class="fas fa-sync-alt"></i></button>
        <button class="export-btn" onclick="openAIAssistant()"><i class="fas fa-robot"></i> Rapport IA</button>
      </div>
    </div>
    ${typeof buildArgosDirectStatsPanel === 'function' ? buildArgosDirectStatsPanel() : ''}
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:var(--cyan)"><div class="stat-label">Temp. Moy</div><div class="stat-value" id="dyn-stat-temp">--°C</div><div class="stat-sub" id="dyn-sub-temp">Chargement…</div></div>
      <div class="stat-card" style="--accent:var(--amber)"><div class="stat-label">Alertes</div><div class="stat-value" id="dyn-stat-alerts">--</div><div class="stat-sub" id="dyn-sub-alerts">Chargement…</div></div>
      <div class="stat-card" style="--accent:var(--red)"><div class="stat-label">Chocs</div><div class="stat-value" id="dyn-stat-shocks">--</div><div class="stat-sub" id="dyn-sub-shocks">Chargement…</div></div>
      <div class="stat-card" style="--accent:var(--green)"><div class="stat-label">Fiabilité</div><div class="stat-value" id="dyn-stat-fiability">--%</div><div class="stat-sub" id="dyn-sub-fiability">Chargement…</div></div>
    </div>
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card" style="--accent:#2979ff"><div class="stat-label">Humidité Moy.</div><div class="stat-value" id="dyn-stat-hum">--%</div><div class="stat-sub">Capteur ESP32</div></div>
      <div class="stat-card" style="--accent:#b44dff"><div class="stat-label">Pression Moy.</div><div class="stat-value" id="dyn-stat-press">--</div><div class="stat-sub">hPa</div></div>
      <div class="stat-card" style="--accent:#00e676"><div class="stat-label">Vitesse Moy.</div><div class="stat-value" id="dyn-stat-speed">--</div><div class="stat-sub">km/h · GPS</div></div>
      <div class="stat-card" style="--accent:#7cdbff"><div class="stat-label">Batterie Moy.</div><div class="stat-value" id="dyn-stat-battery">--%</div><div class="stat-sub">Niveau ESP32</div></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">Couverture & amplitudes</span><span class="badge badge-info" id="stats-period-badge">7 jours</span></div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;font-size:12px">
        <div><div style="color:var(--text3);margin-bottom:4px">MESURES / APPAREILS</div><strong id="dyn-detail-events">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">COUVERTURE GPS</div><strong id="dyn-detail-gps">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">IDENTITÉ / SÉQUENCE</div><strong id="dyn-detail-identity">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">CHOC MOY. / MAX</div><strong id="dyn-detail-shock">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">ACCÉLÉRATION MOY. X / Y / Z</div><strong id="dyn-detail-accel">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">ACCÉLÉRATION |A| MAX</div><strong id="dyn-detail-magnitude">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">PLAGES T° / H% / PRESSION / VITESSE</div><strong id="dyn-detail-ranges">—</strong></div>
        <div><div style="color:var(--text3);margin-bottom:4px">PREMIÈRE / DERNIÈRE MESURE</div><strong id="dyn-detail-window">—</strong></div>
      </div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header">
        <span class="card-title">Dernières télémétries ESP32</span>
        <span id="stats-live-meta" style="font-size:11px;color:var(--text3)">Chargement…</span>
      </div>
      <div class="data-table-wrap">
        <table class="data-table" style="min-width:1900px">
          <thead><tr>
            <th>État & sécurité</th><th>Date / heure</th><th>Boîte / conteneur</th><th>Device UID / séquence</th>
            <th>Température</th><th>Humidité</th><th>Pression</th><th>Choc</th><th>Accélérations X / Y / Z / |A|</th>
            <th>Batterie</th><th>GPS lat. / lon. / vitesse</th><th>Capteurs annexes</th><th>Alertes</th>
          </tr></thead>
          <tbody id="stats-live-tbody"><tr><td colspan="13" style="text-align:center;color:var(--text3)">Chargement des mesures…</td></tr></tbody>
        </table>
      </div>
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
      <div class="card"><div class="card-header"><span class="card-title">Batterie</span></div>
        <div class="chart-wrap" style="height:200px"><canvas id="chart-battery"></canvas></div></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">Accélérations X / Y / Z & magnitude</span></div>
      <div class="chart-wrap" style="height:220px"><canvas id="chart-accel"></canvas></div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card"><div class="card-header"><span class="card-title">Position GPS chronologique</span></div>
        <div class="chart-wrap" style="height:210px"><canvas id="chart-gps"></canvas></div></div>
      <div class="card"><div class="card-header"><span class="card-title">Mesures & alertes chronologiques</span></div>
        <div class="chart-wrap" style="height:210px"><canvas id="chart-activity"></canvas></div></div>
    </div>
    <div class="charts-row" style="margin-bottom:16px">
      <div class="card"><div class="card-header"><span class="card-title">Répartition Alertes</span></div>
        <div class="chart-wrap" style="height:200px"><canvas id="chart-subs"></canvas></div></div>
      <div class="card"><div class="card-header"><span class="card-title">Abonnements actifs mensuels</span><button class="export-btn" onclick="showToast('Export CSV','info')"><i class="fas fa-file-csv"></i> CSV</button></div>
        <div class="chart-wrap" style="height:200px"><canvas id="chart-revenue"></canvas></div></div>
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════
//  STATS PAGE (Sécurisé par rôle)
// ══════════════════════════════════════════════════════
function formatStatsNumber(value, digits=1){
  if(value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  if(!Number.isFinite(number)) return '—';
  return number.toLocaleString('fr-FR', {maximumFractionDigits:digits});
}

function formatStatsDateTime(value){
  if(!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('fr-FR');
}

function setStatsText(id, value){
  const element = document.getElementById(id);
  if(element) element.textContent = value;
}

function setStatsUnavailable(message='Données indisponibles'){
  [
    'dyn-stat-temp','dyn-stat-alerts','dyn-stat-shocks','dyn-stat-fiability',
    'dyn-stat-hum','dyn-stat-press','dyn-stat-speed','dyn-stat-battery',
    'dyn-detail-events','dyn-detail-gps','dyn-detail-identity','dyn-detail-shock',
    'dyn-detail-accel','dyn-detail-magnitude','dyn-detail-ranges','dyn-detail-window'
  ].forEach(id=>setStatsText(id, '—'));
  ['temp','alerts','shocks','fiability'].forEach(key=>setStatsText(`dyn-sub-${key}`, message));
  ['chart-temp','chart-hum','chart-press','chart-speed','chart-shock','chart-battery','chart-accel','chart-gps','chart-activity'].forEach(id=>{
    const chart = charts[id];
    if(!chart) return;
    chart.data.labels = [];
    chart.data.datasets.forEach(dataset=>{ dataset.data = []; });
    chart.update();
  });
}

function updateStatsChart(id, labels, series){
  const chart = charts[id];
  if(!chart) return;
  chart.data.labels = Array.isArray(labels) ? labels : [];
  series.forEach((values, index)=>{
    if(chart.data.datasets[index]) chart.data.datasets[index].data = Array.isArray(values) ? values : [];
  });
  chart.update();
}

function populateStatsDeviceSelect(devices=statsDeviceSummaries){
  const select = document.getElementById('stats-device-select');
  if(!select) return;
  const current = select.value;
  const byUid = new Map();
  (Array.isArray(devices) ? devices : []).forEach(device=>{
    const uid = String(device?.deviceUid || '').trim();
    if(!uid) return;
    const box = device?.blackBoxId;
    if(!byUid.has(uid)) byUid.set(uid, new Set());
    if(box !== null && box !== undefined && box !== '') byUid.get(uid).add(String(box));
  });
  const options = Array.from(byUid.entries()).sort(([a],[b])=>a.localeCompare(b, undefined, {numeric:true, sensitivity:'base'}));
  select.innerHTML = '<option value="">Tous les appareils</option>' + options.map(([uid, boxes])=>{
    const suffix = boxes.size ? ` · boîte ${Array.from(boxes).join(', ')}` : '';
    return `<option value="${escapeHTML(uid)}">${escapeHTML(uid + suffix)}</option>`;
  }).join('');
  select.disabled = options.length === 0;
  select.value = byUid.has(current) ? current : '';
}

function onStatsBoxChange(){
  const deviceSelect = document.getElementById('stats-device-select');
  if(deviceSelect) deviceSelect.value = '';
  statsDeviceSummaries = [];
  statsLatestTelemetry = [];
  populateStatsDeviceSelect([]);
  loadDynamicStats(document.getElementById('stats-period-select')?.value || '7d');
}

async function loadDynamicStats(period='7d'){
  const boite = document.getElementById('stats-boite-select')?.value || '';
  const params = new URLSearchParams({period});
  if(boite) params.set('boite', boite);
  const requestId = ++statsRequestId;
  
  try {
    const res  = await secureApiFetch(`/api/stats?${params.toString()}`);
    const data = await res.json();
    if(requestId !== statsRequestId) return;
    if(!res.ok || data.status !== 'success') {
      setStatsUnavailable(data.message || data.error || 'Accès restreint');
      return;
    }
    
    const kpi = data.kpi || {};
    const ranges = data.ranges || {};
    const labels = {'5h':'Sur 5 heures','24h':'Sur 24h','7d':'Sur 7 jours','30d':'Ce mois','3m':'Ce trimestre','all':'Depuis toujours'};
    const lbl = labels[period] || period;
    setStatsText('stats-period-badge', lbl);
    setStatsText('dyn-stat-temp', `${formatStatsNumber(kpi.avg_temp)} °C`);
    setStatsText('dyn-stat-alerts', formatStatsNumber(kpi.total_alertes, 0));
    setStatsText('dyn-stat-shocks', formatStatsNumber(kpi.total_shocks, 0));
    setStatsText('dyn-stat-fiability', `${formatStatsNumber(kpi.fiabilite)} %`);
    setStatsText('dyn-stat-hum', `${formatStatsNumber(kpi.avg_hum)} %`);
    setStatsText('dyn-stat-press', formatStatsNumber(kpi.avg_press));
    setStatsText('dyn-stat-speed', formatStatsNumber(kpi.avg_speed));
    setStatsText('dyn-stat-battery', `${formatStatsNumber(kpi.avg_battery)} %`);
    setStatsText('dyn-detail-events', `${formatStatsNumber(kpi.total_events, 0)} mesures · ${formatStatsNumber(kpi.devices, 0)} appareils`);
    setStatsText('dyn-detail-gps', `${formatStatsNumber(kpi.gps_coverage)} % des mesures`);
    setStatsText('dyn-detail-identity', `UID ${formatStatsNumber(kpi.identity_coverage)} % · séq. ${formatStatsNumber(kpi.sequence_coverage)} %`);
    setStatsText('dyn-detail-shock', `${formatStatsNumber(kpi.avg_shock, 3)} / ${formatStatsNumber(kpi.max_shock, 3)} G`);
    setStatsText('dyn-detail-accel', `${formatStatsNumber(kpi.avg_acceleration_x, 3)} / ${formatStatsNumber(kpi.avg_acceleration_y, 3)} / ${formatStatsNumber(kpi.avg_acceleration_z, 3)}`);
    setStatsText('dyn-detail-magnitude', formatStatsNumber(kpi.max_acceleration_magnitude, 3));
    setStatsText('dyn-detail-ranges', `${formatStatsNumber(ranges.temperature?.min)}–${formatStatsNumber(ranges.temperature?.max)} °C · ${formatStatsNumber(ranges.humidity?.min)}–${formatStatsNumber(ranges.humidity?.max)} % · ${formatStatsNumber(ranges.pressure?.min)}–${formatStatsNumber(ranges.pressure?.max)} hPa · max ${formatStatsNumber(ranges.speed?.max)} km/h`);
    setStatsText('dyn-detail-window', `${formatStatsDateTime(ranges.first_at)} / ${formatStatsDateTime(ranges.last_at)}`);
    
    ['temp','alerts','shocks','fiability'].forEach(k=>{
      const el = document.getElementById(`dyn-sub-${k}`);
      if(el) el.textContent = lbl;
    });
    setStatsText('dyn-sub-alerts', `${lbl} · ${formatStatsNumber(kpi.total_notifications, 0)} notifications`);
    
    const cd = data.charts || {};
    const accelerationX = Array.isArray(cd.acceleration_x) ? cd.acceleration_x : [];
    const accelerationY = Array.isArray(cd.acceleration_y) ? cd.acceleration_y : [];
    const accelerationZ = Array.isArray(cd.acceleration_z) ? cd.acceleration_z : [];
    const accelerationMagnitude = Array.from({length:Math.max(accelerationX.length, accelerationY.length, accelerationZ.length)}, (_, index)=>{
      const values = [accelerationX[index], accelerationY[index], accelerationZ[index]].map(Number);
      return values.every(Number.isFinite) ? Math.sqrt(values.reduce((sum, value)=>sum + value * value, 0)) : null;
    });
    updateStatsChart('chart-temp', cd.labels, [cd.temp]);
    updateStatsChart('chart-hum', cd.labels, [cd.hum]);
    updateStatsChart('chart-press', cd.labels, [cd.press]);
    updateStatsChart('chart-speed', cd.labels, [cd.speed]);
    updateStatsChart('chart-shock', cd.labels, [cd.shocks]);
    updateStatsChart('chart-battery', cd.labels, [cd.battery]);
    updateStatsChart('chart-accel', cd.labels, [accelerationX, accelerationY, accelerationZ, accelerationMagnitude]);
    updateStatsChart('chart-gps', cd.labels, [cd.gps_lat, cd.gps_lon]);
    updateStatsChart('chart-activity', cd.labels, [cd.samples, cd.alerts]);
    if(charts['chart-subs']){
      charts['chart-subs'].data.datasets[0].data = Array.isArray(cd.alerts_dist) ? cd.alerts_dist : [0,0,0,0,0];
      charts['chart-subs'].update();
    }
    if(charts['chart-revenue'] && cd.abonnements){
      charts['chart-revenue'].data.labels = cd.abonnements.labels || [];
      charts['chart-revenue'].data.datasets[0].data = cd.abonnements.data || [];
      charts['chart-revenue'].update();
    }
    statsDeviceSummaries = Array.isArray(data.devices) ? data.devices : [];
    populateStatsDeviceSelect(statsDeviceSummaries.concat(statsLatestTelemetry));
  } catch(e){
      if(requestId !== statsRequestId) return;
      console.warn('Accès aux statistiques restreint ou erreur réseau.', e);
      setStatsUnavailable('Erreur de chargement');
  } finally {
      if(requestId === statsRequestId) loadStatsLiveTelemetry();
  }
}

function statsBoolean(value){
  return value === true || value === 1 || value === '1' || String(value).toLowerCase() === 'true';
}

function statsAlerts(row){
  if(Array.isArray(row?.alerts)) return row.alerts;
  return row?.alerts ? [row.alerts] : [];
}

function statsAlertText(alert){
  if(alert && typeof alert === 'object') return alert.message || alert.type || alert.code || JSON.stringify(alert);
  return String(alert || '');
}

function statsAccelerationMagnitude(sensors){
  const rawValues = [sensors.accelerationX, sensors.accelerationY, sensors.accelerationZ];
  if(rawValues.some(value=>value === null || value === undefined || value === '')) return null;
  const values = rawValues.map(Number);
  return values.every(Number.isFinite) ? Math.sqrt(values.reduce((sum, value)=>sum + value * value, 0)) : null;
}

function statsQualitySensors(row){
  const sensors = row?.sensors && typeof row.sensors === 'object' ? {...row.sensors} : {};
  const quality = row?.quality && typeof row.quality === 'object' ? row.quality : {};
  if(quality.dhtValid === false){ sensors.temperature = null; sensors.humidity = null; }
  if(quality.mpuValid === false){
    sensors.shock = null;
    sensors.accelerationX = null;
    sensors.accelerationY = null;
    sensors.accelerationZ = null;
  }
  if(quality.distanceValid === false) sensors.distanceCm = null;
  if(quality.pressureMeasured === false) sensors.pressure = null;
  if(quality.batteryMeasured === false) sensors.batteryLevel = null;
  return sensors;
}

function statsQualityLabel(row){
  const quality = row?.quality && typeof row.quality === 'object' ? row.quality : {};
  const states = [];
  if(quality.dhtValid === false) states.push('DHT22 invalide');
  if(quality.mpuValid === false) states.push('MPU6050 invalide');
  if(quality.distanceValid === false) states.push('Distance invalide');
  if(quality.pressureMeasured === false) states.push('Pression estimée');
  if(quality.batteryMeasured === false) states.push('Batterie estimée');
  return states.join(' · ');
}

function sortStatsTelemetry(rows, sort){
  const specifications = {
    timestamp_desc: [row=>row.timestamp ? new Date(row.timestamp).getTime() : null, -1],
    timestamp_asc: [row=>row.timestamp ? new Date(row.timestamp).getTime() : null, 1],
    box_asc: [row=>String(row.blackBoxId ?? ''), 1],
    device_asc: [row=>String(row.deviceUid ?? ''), 1],
    sequence_desc: [row=>row.sequence === null || row.sequence === undefined ? null : Number(row.sequence), -1],
    temperature_desc: [row=>{ const value=statsQualitySensors(row).temperature; return value === null || value === undefined ? null : Number(value); }, -1],
    shock_desc: [row=>{ const value=statsQualitySensors(row).shock; return value === null || value === undefined ? null : Number(value); }, -1],
    battery_asc: [row=>{ const value=statsQualitySensors(row).batteryLevel; return value === null || value === undefined ? null : Number(value); }, 1],
    alerts_desc: [row=>statsAlerts(row).length, -1]
  };
  const [getter, direction] = specifications[sort] || specifications.timestamp_desc;
  return [...rows].sort((left, right)=>{
    const a = getter(left);
    const b = getter(right);
    const aMissing = a === '' || a === null || a === undefined || (typeof a === 'number' && !Number.isFinite(a));
    const bMissing = b === '' || b === null || b === undefined || (typeof b === 'number' && !Number.isFinite(b));
    if(aMissing !== bMissing) return aMissing ? 1 : -1;
    if(typeof a === 'string' || typeof b === 'string') return String(a).localeCompare(String(b), undefined, {numeric:true, sensitivity:'base'}) * direction;
    return (a - b) * direction;
  });
}

function renderStatsLiveTelemetry(rows){
  const tbody = document.getElementById('stats-live-tbody');
  if(!tbody) return;
  const sorted = sortStatsTelemetry(rows, document.getElementById('stats-live-sort')?.value || 'timestamp_desc');
  if(!sorted.length){
    tbody.innerHTML = '<tr><td colspan="13" style="text-align:center;color:var(--text3)">Aucune télémétrie pour ces filtres.</td></tr>';
    return;
  }
  tbody.innerHTML = sorted.map(row=>{
    const sensors = statsQualitySensors(row);
    const position = row?.position && typeof row.position === 'object' ? row.position : {};
    const modes = row?.modes && typeof row.modes === 'object' ? row.modes : {};
    const alerts = statsAlerts(row).map(statsAlertText).filter(Boolean);
    const qualityLabel = statsQualityLabel(row);
    const online = statsBoolean(row.online);
    const securityAlarm = statsBoolean(sensors.securityAlarm);
    const securityEnabled = statsBoolean(modes.securityEnabled);
    const audioRecording = statsBoolean(modes.audioRecordingEnabled);
    const audioListening = statsBoolean(modes.audioListeningEnabled);
    const flameDetection = statsBoolean(modes.flameDetectionEnabled);
    const flame = statsBoolean(sensors.flameDetected);
    const door = statsBoolean(sensors.doorOpen);
    const magnitude = statsAccelerationMagnitude(sensors);
    const battery = sensors.batteryLevel === null || sensors.batteryLevel === undefined || sensors.batteryLevel === '' ? null : Number(sensors.batteryLevel);
    const batteryColor = !Number.isFinite(battery) ? 'var(--text3)' : (battery <= 20 ? 'var(--red)' : 'var(--green)');
    const dateTime = formatStatsDateTime(row.timestamp || [row.date, row.time].filter(Boolean).join('T'));
    const freshnessValue = row.freshnessSeconds === null || row.freshnessSeconds === undefined || row.freshnessSeconds === '' ? null : Number(row.freshnessSeconds);
    const freshness = Number.isFinite(freshnessValue) ? `${formatStatsNumber(freshnessValue, 0)} s` : '—';
    const securityClass = securityAlarm ? 'badge-danger' : (securityEnabled ? 'badge-ok' : 'badge-info');
    const securityLabel = securityAlarm ? 'ALARME' : (securityEnabled ? 'Sécurité active' : 'Sécurité inactive');
    const alertsHtml = alerts.length
      ? alerts.map(alert=>`<span class="badge badge-danger" style="margin:2px;white-space:normal">${escapeHTML(alert)}</span>`).join('')
      : '<span style="color:var(--green)">Aucune</span>';
    return `<tr>
      <td style="min-width:175px"><span class="badge ${online ? 'badge-ok' : 'badge-danger'}">${online ? 'En ligne' : 'Hors ligne'}</span><div style="margin-top:5px"><span class="badge ${securityClass}">${securityLabel}</span></div><div style="font-size:10px;color:var(--text3);margin-top:5px">Porte ${door ? 'ouverte' : 'fermée'} · Flamme ${flame ? 'oui' : 'non'}</div><div style="font-size:10px;color:var(--text3)">Audio enr. ${audioRecording ? 'on' : 'off'} · écoute ${audioListening ? 'on' : 'off'} · détection flamme ${flameDetection ? 'on' : 'off'}</div></td>
      <td style="font-family:var(--mono);font-size:11px;min-width:145px">${escapeHTML(dateTime)}<div style="color:var(--text3);margin-top:4px">Fraîcheur ${escapeHTML(freshness)}</div></td>
      <td><span class="badge badge-info">${escapeHTML(String(row.blackBoxId ?? '—'))}</span><div style="font-size:10px;color:var(--text3);margin-top:4px">Cont. ${escapeHTML(String(row.containerId ?? '—'))}</div></td>
      <td style="font-family:var(--mono);font-size:11px;max-width:190px;overflow-wrap:anywhere">${escapeHTML(String(row.deviceUid || '—'))}<div style="color:var(--text3);margin-top:4px">Séq. ${escapeHTML(String(row.sequence ?? '—'))}</div></td>
      <td><strong>${formatStatsNumber(sensors.temperature, 2)}</strong> °C</td>
      <td><strong>${formatStatsNumber(sensors.humidity, 2)}</strong> %</td>
      <td><strong>${formatStatsNumber(sensors.pressure, 2)}</strong> hPa</td>
      <td><strong>${formatStatsNumber(sensors.shock, 3)}</strong> G</td>
      <td style="font-family:var(--mono);font-size:11px;min-width:190px">${formatStatsNumber(sensors.accelerationX, 3)} / ${formatStatsNumber(sensors.accelerationY, 3)} / ${formatStatsNumber(sensors.accelerationZ, 3)}<div style="color:var(--cyan);margin-top:4px">|A| ${formatStatsNumber(magnitude, 3)}</div></td>
      <td><strong style="color:${batteryColor}">${formatStatsNumber(sensors.batteryLevel, 1)} %</strong></td>
      <td style="font-family:var(--mono);font-size:11px;min-width:210px">${formatStatsNumber(position.latitude, 6)}, ${formatStatsNumber(position.longitude, 6)}<div style="color:var(--text3);margin-top:4px">${formatStatsNumber(position.speed, 2)} km/h · ±${formatStatsNumber(position.accuracy, 1)} m · cap ${formatStatsNumber(position.heading, 1)}°</div><div style="color:var(--text3)">${escapeHTML(position.source || '—')}</div></td>
      <td style="font-size:11px;min-width:150px">Lumière ${formatStatsNumber(sensors.lightLevel, 2)}<br>Son ${formatStatsNumber(sensors.soundLevel, 2)}<br>Distance ${formatStatsNumber(sensors.distanceCm, 2)} cm${qualityLabel ? `<div style="color:var(--amber);margin-top:4px">${escapeHTML(qualityLabel)}</div>` : ''}</td>
      <td style="font-size:11px;min-width:180px;max-width:260px">${alertsHtml}</td>
    </tr>`;
  }).join('');
}

async function loadStatsLiveTelemetry(){
  if((typeof currentPage !== 'undefined' && currentPage !== 'stats') || localStorage.getItem('isLoggedIn') !== 'true') return;
  const tbody = document.getElementById('stats-live-tbody');
  if(!tbody) return;
  if(statsLiveRefreshTimer){
    clearTimeout(statsLiveRefreshTimer);
    statsLiveRefreshTimer = null;
  }
  const boite = document.getElementById('stats-boite-select')?.value || '';
  const deviceUid = document.getElementById('stats-device-select')?.value || '';
  const sort = document.getElementById('stats-live-sort')?.value || 'timestamp_desc';
  const params = new URLSearchParams({limit:'100', sort:sort === 'timestamp_asc' ? 'asc' : 'desc'});
  if(boite) params.set('boite', boite);
  if(deviceUid) params.set('device_uid', deviceUid);
  const requestId = ++statsLiveRequestId;
  tbody.innerHTML = '<tr><td colspan="13" style="text-align:center;color:var(--text3)">Chargement des mesures…</td></tr>';
  setStatsText('stats-live-meta', 'Actualisation…');
  try {
    const response = await secureApiFetch(`/api/stats/live?${params.toString()}`);
    const data = await response.json();
    if(requestId !== statsLiveRequestId) return;
    if(!response.ok || data.status !== 'success') throw new Error(data.message || data.error || 'Télémétrie indisponible');
    statsLatestTelemetry = Array.isArray(data.telemetry) ? data.telemetry : (data.latest ? [data.latest] : []);
    populateStatsDeviceSelect(statsDeviceSummaries.concat(statsLatestTelemetry));
    renderStatsLiveTelemetry(statsLatestTelemetry);
    const generated = data.generatedAt ? ` · ${formatStatsDateTime(data.generatedAt)}` : '';
    setStatsText('stats-live-meta', `${formatStatsNumber(data.count ?? statsLatestTelemetry.length, 0)} mesure(s) · ${data.source || 'source inconnue'}${generated}`);
  } catch(error){
    if(requestId !== statsLiveRequestId) return;
    console.warn('Chargement de la télémétrie ESP32 impossible.', error);
    tbody.innerHTML = `<tr><td colspan="13" style="text-align:center;color:var(--red)">${escapeHTML(error.message || 'Erreur de chargement')}</td></tr>`;
    setStatsText('stats-live-meta', 'Indisponible');
  } finally {
    if(requestId === statsLiveRequestId && currentPage === 'stats' && localStorage.getItem('isLoggedIn') === 'true' && document.getElementById('stats-live-tbody')){
      statsLiveRefreshTimer = setTimeout(loadStatsLiveTelemetry, 15000);
    }
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
    if(!res.ok || !Array.isArray(data)) throw new Error(data?.error || 'Liste des boîtes indisponible');
    const boxes = data
      .filter(c=>c.id_boite)
      .map(c=>({value: String(c.id_boite).trim(), label: String(boxLabel(c))}))
      .filter(c=>c.value);
    const seen = new Set();
    const unique = boxes.filter(c=>{
      if(seen.has(c.value)) return false;
      seen.add(c.value);
      return true;
    });
    unique.sort((a,b)=>a.label.localeCompare(b.label, undefined, {numeric:true, sensitivity:'base'}));
    sel.innerHTML = '<option value="">Toutes les boîtes</option>' +
      unique.map(c=>`<option value="${escapeHTML(c.value)}">${escapeHTML(c.label)}</option>`).join('');
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
        <button class="btn-secondary" onclick="showRegulatorySourceCatalog()"><i class="fas fa-scale-balanced"></i> Référentiel des sources</button>
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

async function showRegulatorySourceCatalog(){
  const root=document.getElementById('modal-root');if(!root)return;
  root.innerHTML='<div class="modal-overlay"><div class="modal"><div class="modal-body">Chargement du registre…</div></div></div>';
  try{
    const response=await secureApiFetch('/api/regulatory/sources');const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Registre indisponible');
    const sources=data.sources||[];
    root.innerHTML=`<div class="modal-overlay" onclick="if(event.target===this)closeModal()"><div class="modal" style="max-width:1000px;width:min(1000px,94vw);max-height:90vh;overflow:auto"><div class="modal-header"><div><div class="modal-title">Référentiel juridique & normatif</div><div style="font-size:12px;color:var(--text3)">Sources officielles repérées · Applicabilité à évaluer par dossier</div></div><button class="modal-close" onclick="closeModal()">×</button></div><div class="modal-body"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px">${sources.map(source=>{const url=String(source.official_url||'');const link=url.startsWith('https://')?`<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Ouvrir la source officielle ↗</a>`:'';return `<article style="padding:13px;border:1px solid var(--border);border-radius:10px;background:var(--bg3)"><strong>${escapeHTML(source.title)}</strong><div style="font-size:11px;color:var(--text3);margin:5px 0">${escapeHTML(source.authority)} · ${escapeHTML(source.jurisdiction)} · ${escapeHTML((source.transport_modes||[]).join(', '))}</div><span class="badge badge-warn">${escapeHTML(source.legal_status)}</span><p style="font-size:12px;line-height:1.45">${escapeHTML(source.applicability_conditions||source.summary)}</p><small style="color:var(--text3)">Statut de la source : ${escapeHTML(source.verified_at?'référence consultée':'à vérifier')} · statut d’applicabilité dans un dossier : non établi par le registre.</small><div style="margin-top:8px">${link}</div></article>`;}).join('')}</div></div><div class="modal-footer"><span style="font-size:11px;color:var(--text3)">L’inscription d’une source ne vaut ni avis juridique ni constat de conformité.</span><button class="btn-secondary" onclick="closeModal()">Fermer</button></div></div></div>`;
  }catch(error){root.innerHTML=`<div class="modal-overlay" onclick="if(event.target===this)closeModal()"><div class="modal"><div class="modal-body"><div class="alert alert-warn">${escapeHTML(error.message)}</div><button class="btn-secondary" onclick="closeModal()">Fermer</button></div></div></div>`;}
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
      const recordingUid = e.recording_uid || '';
      const audio = recordingUid
        ? `<button class="btn-icon" onclick="playProtectedEventAudio('${escapeHTML(recordingUid)}',this)"><i class="fas fa-play"></i> Lire</button>`
        : '<span style="color:var(--text3);font-size:11px">—</span>';
      const eventQuality = statsQualityLabel({quality:e.quality});
      const sensorStr = `UID:${e.device_uid ?? '—'} #${e.sequence ?? '—'} · T:${e.temperature ?? '—'}°C H:${e.humidite ?? '—'}% P:${e.pressions ?? '—'} hPa V:${e.vitesse ?? '—'} km/h G:${e.chocs ?? '—'} · A:${e.acceleration_x ?? '—'}/${e.acceleration_y ?? '—'}/${e.acceleration_z ?? '—'} · GPS:${e.lat ?? '—'},${e.lon ?? '—'} · Batterie:${e.battery_level ?? '—'}%${eventQuality ? ` · Qualité:${eventQuality}` : ''}`;
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
        <td><button class="btn-icon" onclick="showContainerDetailDB('${escapeHTML(e.id_boite || e.id || '')}')"><i class="fas fa-box"></i> Ouvrir</button> <button class="btn-icon" onclick="showRegulatoryHistory('${escapeHTML(e.id_boite || e.id || '')}')"><i class="fas fa-scale-balanced"></i> Dossier</button></td>
      </tr>`;
    }).join('');
  } catch(e){
    console.error('refreshEventTable', e);
    const tbody = document.getElementById('events-tbody');
    if(tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Erreur de chargement des événements</td></tr>';
  }
}

let protectedEventAudioUrl = null;
async function playProtectedEventAudio(recordingUid, button) {
  if (!recordingUid || !button) return;
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Chargement';
  try {
    const response = await secureApiFetch(`/api/audio/${encodeURIComponent(recordingUid)}`);
    if (!response.ok) throw new Error('Lecture audio refusée');
    if (protectedEventAudioUrl) URL.revokeObjectURL(protectedEventAudioUrl);
    protectedEventAudioUrl = URL.createObjectURL(await response.blob());
    const player = document.createElement('audio');
    player.controls = true;
    player.autoplay = true;
    player.src = protectedEventAudioUrl;
    player.style.cssText = 'height:32px;width:180px;max-width:100%';
    button.replaceWith(player);
    await player.play().catch(() => {});
  } catch (error) {
    button.disabled = false;
    button.innerHTML = original;
    showToast(error.message, 'error');
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
          <div class="settings-title"><i class="fas fa-wifi"></i> Connexion WiFi</div>
          <p style="font-size:12px;color:var(--text2);margin-bottom:12px">Configurez les paramètres de connexion WiFi pour vos modules IoT.</p>
          <button class="btn-primary" onclick="openWiFiSettingsModalNew()"><i class="fas fa-wifi"></i> Configurer WiFi</button>
        </div>
        ${typeof buildArgosDirectSettingsCard === 'function' ? buildArgosDirectSettingsCard() : ''}
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

async function changePassword(){
  const c = document.getElementById('pw-current')?.value;
  const n = document.getElementById('pw-new')?.value;
  const f = document.getElementById('pw-confirm')?.value;
  if(!c||!n||!f){ showToast('Remplissez tous les champs','warn'); return; }
  if(n !== f){ showToast('Les mots de passe ne correspondent pas','warn'); return; }
  if(n.length<8){ showToast('Le nouveau mot de passe doit contenir au moins 8 caractères','warn'); return; }
  const response=await secureApiFetch('/api/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({current_password:c,new_password:n})});
  const data=await response.json().catch(()=>({}));
  if(!response.ok){ showToast(data.error||'Changement impossible','error'); return; }
  showToast('Mot de passe mis à jour. Reconnexion requise.','success');
  setTimeout(doLogout,800);
}

function openSupportChat(){
  const phone = '237620102907'; // Numéro de support WhatsApp
  const text = encodeURIComponent('Bonjour ARGOS, je souhaite une assistance technique.');
  window.open(`https://wa.me/${phone}?text=${text}`,'_blank');
  showToast('Ouverture du support WhatsApp…','info');
}


function doLogout() {
  document.getElementById('argos-ai-widget')?.setAttribute('hidden','');
  if (typeof stopArgosDirectBridge === 'function') stopArgosDirectBridge(true);
  sessionStorage.removeItem('argosAccessToken');
  // Affichage du toast de déconnexion
  if (typeof notifsEnabled !== 'undefined' && notifsEnabled) {
      showToast('Déconnexion…', 'info');
  } else {
      // Si tu veux l'afficher même quand notifsEnabled est faux/indéfini
      showToast('Déconnexion…', 'info'); 
  }

  // Nettoyage du localStorage
  localStorage.removeItem('currentRole');
  localStorage.removeItem('currentUserId');
  localStorage.removeItem('isLoggedIn');

  // Délai d'une seconde pour laisser le temps au toast de s'afficher
  setTimeout(() => {
    // Redirection vers la plateforme externe
    window.location.href = '/presentations';
  }, 1000);
}

// ══════════════════════════════════════════════════════
//  MAP INIT & CONTROLS
// ══════════════════════════════════════════════════════
let tileLayerRef = null;

function initMap(mapId, role){
  const el = document.getElementById(mapId);
  if(!el) return;
  if (typeof L === 'undefined') {
    el.innerHTML = `
      <div style="height:100%;display:flex;align-items:center;justify-content:center;text-align:center;padding:20px;color:var(--text3);background:var(--bg3);border-radius:var(--radius);">
        Carte indisponible : la librairie Leaflet n'a pas ete chargee.
      </div>`;
    return;
  }
  if(maps[mapId]){ maps[mapId].remove(); delete maps[mapId]; }
  const map = L.map(mapId, {center:[5.0, 11.0], zoom: role==='client'?9:6, zoomControl:false});
  maps[mapId] = map;
  L.control.zoom({position:'bottomright'}).addTo(map);
  tileLayerRef = L.tileLayer(MAP_LAYERS[mapLayerIdx].url, {attribution:MAP_LAYERS[mapLayerIdx].attribution, maxZoom:19}).addTo(map);
  if(mapId === 'map-main') loadMapPositions();
  else placeDBMarkersOnMap(map, role);
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

async function loadMapPositions(){
  const status = document.getElementById('map-data-status');
  if(status){ status.dataset.error=''; status.textContent='Chargement des positions consolidées…'; }
  try {
    const response = await secureApiFetch('/api/containers/positions');
    const data = await response.json();
    if(!response.ok) throw new Error(data.error || `API GPS indisponible (${response.status})`);
    if(!Array.isArray(data)) throw new Error('Réponse GPS invalide.');
    MAP_GPS_POSITIONS = normalizeMapPositions(data, DB_CONTAINERS);
    if(status) status.textContent=MAP_GPS_POSITIONS.length
      ? `${MAP_GPS_POSITIONS.length} position(s) reçue(s) de l’API consolidée`
      : 'Aucune position GPS exploitable dans les données consolidées.';
    updateMapPageUI();
    syncMapTrails();
    if(currentPage !== 'map') refreshMapMarkers();
  } catch(error){
    MAP_GPS_POSITIONS=[];
    if(status){ status.dataset.error='true'; status.textContent=`Positions indisponibles : ${error.message}`; }
    const title=document.getElementById('map-containers-title');
    if(title) title.textContent='Positions GPS indisponibles';
    const list=document.getElementById('containers-sidebar-list');
    if(list) list.innerHTML=`<div class="map-empty-state" role="status">${escapeHTML(error.message)}. Réessayez avec Actualiser.</div>`;
    for(const id of ['map-temp','map-shock']){
      const value=document.getElementById(id);
      if(value) value.textContent='—';
    }
    const alerts=document.getElementById('map-alerts-list');
    if(alerts) alerts.innerHTML='<div class="map-empty-state">Alertes indisponibles avec la position GPS.</div>';
    refreshMapMarkers();
    syncMapTrails();
  }
}

function normalizeMapPositions(rows, containers=[]){
  if(!Array.isArray(rows)) return [];
  const byId=new Map(containers.map(item=>[String(item.id_boite || item.id),item]));
  return rows.filter(item=>{
    const lat=Number(item?.lat), lon=Number(item?.lon);
    return item?.id_boite!=null && item.lat!=null && item.lon!=null && Number.isFinite(lat) && Number.isFinite(lon) && lat>=-90 && lat<=90 && lon>=-180 && lon<=180;
  }).map(item=>{
    const meta=byId.get(String(item.id_boite)) || {};
    const numeric=(value)=>value==null || value==='' || !Number.isFinite(Number(value)) ? null : Number(value);
    return {...meta,...item,lat:Number(item.lat),lon:Number(item.lon),speed:numeric(item.speed),temp:numeric(item.temp),shock:numeric(item.shock),alerts:Array.isArray(item.alerts)?item.alerts.map(value=>String(value)):[]};
  });
}

function placeDBMarkersOnMap(map, role){
  const containers = map.getContainer()?.id === 'map-main'
    ? MAP_GPS_POSITIONS.filter(c=>MAP_FILTER==='all' || mapPositionState(c)===MAP_FILTER) : [];
  containers.forEach(c=>{
    const lat=Number(c.lat), lon=Number(c.lon);
    if(!Number.isFinite(lat)||!Number.isFinite(lon)) return;
    const color = c.alerts.length ? '#ffab00' : '#00d4ff';
    const markerHtml = `<div class="marker-pulse">
      <div class="marker-outer" style="border-color:${color}"></div>
      <div class="marker-inner" style="background:${color};box-shadow:0 0 8px ${color}"></div>
    </div>`;
    const icon = L.divIcon({html:markerHtml, className:'', iconSize:[24,24], iconAnchor:[12,12]});
    const marker = L.marker([c.lat, c.lon], {icon}).addTo(map);
    marker._containerId = c.id_boite;
    const alertsHtml = c.alerts.length ? c.alerts.slice(0,2).map(a=>`<div style="color:#ff4444;font-size:11px"><i class="fas fa-exclamation-triangle"></i> ${escapeHTML(String(a).substring(0,120))}</div>`).join('') : '<div style="color:#8fa3bc;font-size:11px">Aucune alerte signalée par l’API</div>';
    marker.bindPopup(`
      <div style="font-family:'Space Grotesk',sans-serif;min-width:200px">
        <div style="font-family:monospace;font-size:15px;color:#00d4ff;margin-bottom:6px">${escapeHTML(String(c.numero_serie || c.id_boite))}</div>
        <div style="font-size:12px;color:#ccc">Boîte ${escapeHTML(String(c.id_boite))}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:8px">
          <div style="text-align:center;background:rgba(0,0,0,.3);padding:5px;border-radius:4px">
            <div style="font-size:15px;font-weight:700;color:#00d4ff">${c.temp??'—'}°C</div>
            <div style="font-size:9px;color:#8fa3bc">TEMP</div>
          </div>
          <div style="text-align:center;background:rgba(0,0,0,.3);padding:5px;border-radius:4px">
            <div style="font-size:15px;font-weight:700;color:#00d4ff">${c.speed??'—'}</div>
            <div style="font-size:9px;color:#8fa3bc">KM/H</div>
          </div>
        </div>
        <div style="margin-top:6px">${alertsHtml}</div>
        <div style="font-size:12px;color:#8fa3bc">${lat.toFixed(6)}, ${lon.toFixed(6)}</div>
        <div style="margin-top:6px;font-size:11px;color:#8fa3bc">Mesurée : ${escapeHTML(formatTime(c.ts))}</div>
      </div>`);
  });
}

async function fetchAndDrawTrail(map, id_boite, requestVersion=MAP_TRAIL_VERSION){
  try {
    if(!/^\d+$/.test(String(id_boite))) return;
    const res=await secureApiFetch(`/api/black-boxes/${encodeURIComponent(id_boite)}/history?limit=1200`);
    const data=await res.json();
    if(!res.ok) throw new Error(data.error || 'Historique GPS indisponible');
    if(requestVersion!==MAP_TRAIL_VERSION || !trailsOn) return;
    const pts=(data.points || []).filter(p=>p.latitude!=null&&p.longitude!=null).map(p=>[Number(p.latitude),Number(p.longitude)]).filter(p=>Number.isFinite(p[0])&&Number.isFinite(p[1])&&p[0]>=-90&&p[0]<=90&&p[1]>=-180&&p[1]<=180);
    if(pts.length>1){
      const line = L.polyline(pts, {color:'#00d4ff', weight:2, opacity:.5, dashArray:'4,4'}).addTo(map);
      trailLayers.push(line);
    }
  } catch(e){}
}

function refreshMapMarkers(){
  const map = maps['map-main'];
  if(!map || typeof L === 'undefined') return;
  // Remove old markers
  map.eachLayer(l=>{ if(l instanceof L.Marker && l._containerId) map.removeLayer(l); });
  // Re-place from the consolidated positions only.
  placeDBMarkersOnMap(map, currentRole);
}

function syncMapTrails(){
  const map=maps['map-main'];
  MAP_TRAIL_VERSION++;
  trailLayers.forEach(layer=>map?.removeLayer(layer));
  trailLayers=[];
  if(!trailsOn || !map) return;
  const version=MAP_TRAIL_VERSION;
  MAP_GPS_POSITIONS.filter(c=>MAP_FILTER==='all' || mapPositionState(c)===MAP_FILTER)
    .forEach(c=>{if(c.id_boite) fetchAndDrawTrail(map,c.id_boite,version);});
}

function showAllContainers(){
  const map = maps['map-main'];
  if(!map || typeof L === 'undefined') return;
  const pts = MAP_GPS_POSITIONS.filter(c=>MAP_FILTER==='all' || mapPositionState(c)===MAP_FILTER).map(c=>[c.lat,c.lon]);
  if(pts.length) map.fitBounds(L.latLngBounds(pts).pad(.2));
}

function fitAllMarkers(){ showAllContainers(); }

function toggleMapLayer(){
  const map = maps['map-main'];
  if(!map || typeof L === 'undefined') return;
  mapLayerIdx = (mapLayerIdx + 1) % MAP_LAYERS.length;
  if(tileLayerRef) map.removeLayer(tileLayerRef);
  tileLayerRef = L.tileLayer(MAP_LAYERS[mapLayerIdx].url, {attribution:MAP_LAYERS[mapLayerIdx].attribution, maxZoom:19}).addTo(map);
  showToast(`Fond de carte: ${MAP_LAYERS[mapLayerIdx].name}`, 'info');
}

function toggleTrails(){
  const map = maps['map-main'];
  if(!map) return;
  trailsOn = !trailsOn;
  if(!trailsOn){
    syncMapTrails();
    showToast('Traces GPS désactivées','info');
  } else {
    syncMapTrails();
    showToast('Traces GPS activées','success');
  }
  const btn = document.getElementById('btn-trails');
  if(btn){ btn.style.background = trailsOn ? 'var(--cyan)' : '';btn.setAttribute('aria-pressed',String(trailsOn)); }
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
  const c = MAP_GPS_POSITIONS.find(x=>String(x.id_boite)===String(id));
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
  if (typeof Chart === 'undefined') {
    document.querySelectorAll('.chart-wrap').forEach(wrap => {
      wrap.innerHTML = '<div style="height:100%;display:flex;align-items:center;justify-content:center;text-align:center;padding:16px;color:var(--text3);background:var(--bg3);border-radius:var(--radius);">Graphique indisponible : Chart.js non charge.</div>';
    });
    return;
  }
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
  mkChart('chart-battery', 'line', [], [{label:'Batterie (%)', data:[], borderColor:'#7cdbff', backgroundColor:'rgba(124,219,255,.1)', borderWidth:2, fill:true, tension:.35, pointRadius:2}], {y:{beginAtZero:true,max:100}});
  mkChart('chart-accel', 'line', [], [
    {label:'Axe X', data:[], borderColor:'#00d4ff', borderWidth:2, fill:false, tension:.3, pointRadius:1},
    {label:'Axe Y', data:[], borderColor:'#ffab00', borderWidth:2, fill:false, tension:.3, pointRadius:1},
    {label:'Axe Z', data:[], borderColor:'#b44dff', borderWidth:2, fill:false, tension:.3, pointRadius:1},
    {label:'Magnitude |A|', data:[], borderColor:'#ff5252', borderWidth:2, borderDash:[5,4], fill:false, tension:.3, pointRadius:1}
  ]);
  mkChart('chart-gps', 'line', [], [
    {label:'Latitude', data:[], borderColor:'#00e676', borderWidth:2, fill:false, tension:.25, pointRadius:2},
    {label:'Longitude', data:[], borderColor:'#2979ff', borderWidth:2, fill:false, tension:.25, pointRadius:2}
  ]);
  mkChart('chart-activity', 'line', [], [
    {label:'Mesures', data:[], borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,.08)', borderWidth:2, fill:true, tension:.3, pointRadius:2},
    {label:'Alertes', data:[], borderColor:'#ff5252', backgroundColor:'rgba(255,82,82,.08)', borderWidth:2, fill:false, tension:.3, pointRadius:2}
  ], {y:{beginAtZero:true}});
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
