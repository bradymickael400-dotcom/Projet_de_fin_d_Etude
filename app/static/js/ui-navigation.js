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
    const res  = await secureApiFetch('/api/dashboard/superadmin');
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
    const res  = await secureApiFetch(`/api/dashboard/owner?owner_id=${currentUserId}`);
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
        if (!res.ok) {
            DB_CONTAINERS = [];
            updateContainerPageUI();
            updateMapPageUI();
            return;
        }
        const data = await res.json();
        DB_CONTAINERS = Array.isArray(data) ? data : [];
        MAP_BLACK_BOXES = [];
        if (currentRole === 'superadmin' || currentRole === 'owner') {
            const boxesResponse = await secureApiFetch('/api/black-boxes/my-boxes');
            const boxesData = await boxesResponse.json().catch(()=>({boxes:[]}));
            if (boxesResponse.ok) {
                MAP_BLACK_BOXES = (boxesData.boxes || []).filter(box=>!box.container_id && box.telemetry?.latitude != null && box.telemetry?.longitude != null).map(box=>({
                    id: `boite-${box.id_boite}`, id_boite: box.id_boite,
                    numero_serie: box.numero_serie, boite_label: box.numero_serie,
                    type_conteneurs: 'Boîte non affectée', type_boite: box.type,
                    status: box.telemetry?.security_alarm ? 'danger' : 'ok',
                    temp: box.telemetry?.temperature, humidity: box.telemetry?.humidity,
                    pressure: box.telemetry?.pressure, shock: box.telemetry?.shock,
                    sound: box.telemetry?.sound_level, speed: 0,
                    lat: Number(box.telemetry.latitude), lon: Number(box.telemetry.longitude),
                    device_uid: box.device_uid, sequence: box.telemetry?.sequence,
                    alerts: box.telemetry?.security_alarm ? ['Alarme de sécurité active'] : [],
                    lastUpdate: box.telemetry?.measured_at ? new Date(box.telemetry.measured_at).toLocaleTimeString('fr-FR') : '—'
                }));
            }
        }
        updateContainerPageUI();
        updateMapPageUI();
        if (typeof refreshMapMarkers === 'function' && maps['map-main']) {
            refreshMapMarkers();
        }
    } catch (e) {
        console.error('Erreur chargement conteneurs', e);
        DB_CONTAINERS = [];
        MAP_BLACK_BOXES = [];
        updateContainerPageUI();
        updateMapPageUI();
    }
}

// ══════════════════════════════════════════════════════
//  THRESHOLDS
// ══════════════════════════════════════════════════════
async function loadThresholds(id_boite){
  if(!id_boite) return;
  try {
    const res  = await secureApiFetch(`/api/config/thresholds/${id_boite}`);
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
    const res = await secureApiFetch('/api/config/thresholds', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        id_boite, temp_max:g('t-temp'), humi_max:g('t-hum'),
        choc_max:g('t-choc'), pression_min:g('t-press'),
        vitesse_max:g('t-vit'), angle_max:g('t-angle')
      })
    });
    const d = await res.json();
    if(res.ok) showToast('Seuils sauvegardés et scellés en blockchain <i class="fas fa-check-circle"></i>','success');
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
        const opts = list.map(c => `<option value="${escapeHTML(c.id_boite || c.id)}">${escapeHTML(boxLabel(c))}${c.type_conteneurs ? ' — ' + escapeHTML(c.type_conteneurs) : ''}</option>`).join('');
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

async function updateContainerIdFields(){
  const qty = parseInt(document.getElementById('sell-qty').value) || 0;
  const section = document.getElementById('container-ids-section');
  if(!section) return;
  section.innerHTML = '';
  if(qty>0){
    const lbl = document.createElement('label');
    lbl.textContent = 'Boîtes noires disponibles';
    lbl.style.cssText = 'display:block;margin-bottom:8px;font-size:12px;color:var(--text2)';
    section.appendChild(lbl);
    const res = await secureApiFetch('/api/black-boxes/available-for-assignment?target=company');
    const boxes = res.ok ? await res.json() : [];
    const available = boxes.filter(box => !box.archived);
    const select = document.createElement('select');
    select.id = 'sell-box-select';
    select.multiple = true;
    select.size = Math.min(8, Math.max(3, available.length));
    available.forEach(box => {
      const option = document.createElement('option');
      option.value = box.id_boite;
      option.textContent = box.label;
      select.appendChild(option);
    });
    section.appendChild(select);
    const info = document.createElement('small');
    info.textContent = `${available.length} boîte(s) sans entreprise en base. Sélection requise : ${qty}.`;
    info.style.cssText = `display:block;margin-top:6px;color:${available.length < qty ? 'var(--red)' : 'var(--text3)'}`;
    section.appendChild(info);
  }
  // Update summary
  const qs = parseInt(document.getElementById('sell-qty').value)||0;
  const company = document.getElementById('sell-company')?.value || '—';
  const sub = `${document.getElementById('sell-contract-months')?.value || 12} mois`;
  const summaryEl = document.getElementById('sale-summary');
  if(summaryEl) summaryEl.innerHTML = qs>0 ? `
    <div class="settings-item"><div class="settings-item-label">Entreprise</div><span>${company}</span></div>
    <div class="settings-item"><div class="settings-item-label">Nombre de BB</div><span>${qs}</span></div>
    <div class="settings-item"><div class="settings-item-label">Abonnement</div><span>${sub}</span></div>
  ` : '<div style="text-align:center;padding:20px;color:var(--text3)">Remplissez le formulaire</div>';
}
// On ajoute le paramètre optionnel forceUpdate = false
async function submitSale(forceUpdate = false) {
  const ids = Array.from(document.getElementById('sell-box-select')?.selectedOptions || []).map(o => Number(o.value));
  
  const nom_agence  = document.getElementById('sell-company')?.value.trim();
  const login       = document.getElementById('sell-login')?.value.trim();
  const password    = document.getElementById('sell-password')?.value;
  const email       = document.getElementById('sell-email')?.value.trim();
  const phone       = document.getElementById('sell-phone')?.value.trim();
  const niu         = email;
  const location    = document.getElementById('sell-location')?.value.trim();
  const contractMonths = Number(document.getElementById('sell-contract-months')?.value || 12);
  const contractStart = document.getElementById('sell-contract-start')?.value || new Date().toISOString().slice(0,10);

  // 1. Vérification des champs requis
  const requested = Number(document.getElementById('sell-qty')?.value || 0);
  if (!nom_agence || !login || !password || !email || ids.length !== requested) {
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
        nom_agence, login, password, email, phone, niu, location,
        boite_ids: ids,
        contract_months: contractMonths,
        contract_start: contractStart,
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
      const notif = d.notifications || {};
      const emailInfo = notif.email_sent ? 'Email envoyé' : (notif.email_configured ? 'Email non envoyé' : 'Email non configuré');
      showToast(`Entreprise enregistrée ! ${emailInfo} <i class="fas fa-check-circle"></i>`, 'success');
      
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
  formData.append('type_a', 'Transit');
  formData.append('destination', document.getElementById('new-client-destination')?.value || '');
  formData.append('cargo_type', document.getElementById('new-client-cargo-type')?.value || '');
  formData.append('cargo_name', document.getElementById('new-client-cargo-name')?.value || '');
  formData.append('description', document.getElementById('new-client-cargo-name')?.value || '');
  formData.append('cargo_value', document.getElementById('new-client-value')?.value || '');
  formData.append('temp_min', document.getElementById('new-th-temp-min')?.value || '');
  formData.append('temp_max', document.getElementById('new-th-temp-max')?.value || '');
  formData.append('humi_min', document.getElementById('new-th-humi-min')?.value || '');
  formData.append('humi_max', document.getElementById('new-th-humi-max')?.value || '');
  formData.append('choc_max', document.getElementById('new-th-shock-max')?.value || '');
  formData.append('pression_min', document.getElementById('new-th-pressure-min')?.value || '');
  formData.append('pression_max', document.getElementById('new-th-pressure-max')?.value || '');

  try {
    showToast('Enregistrement et affiliation du client...', 'info');
    
    // Utilisation du canal sécurisé pour l'envoi du formulaire
    const resp = await secureApiFetch('/api/register_user_file', { 
        method: 'POST', 
        body: formData 
    });
    const d = await resp.json();
    
    if (resp.ok) { 
        showToast(`Client ${name} créé avec succès et rattaché à la boîte ${id_boite} <i class="fas fa-check-circle"></i>`, 'success'); 
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


function toggleSidebar(){
  const sidebar = document.getElementById('sidebar');
  if(!sidebar) return;
  sidebar.classList.toggle('open');
  const isOpen = sidebar.classList.contains('open');
  document.querySelector('.mobile-menu-btn')?.setAttribute('aria-expanded', String(isOpen));
  sidebar.classList.remove('auto-collapsed');
  scheduleSidebarAutoCollapse();
  if(!isOpen){
    window.setTimeout(() => {
      Object.values(maps || {}).forEach(map => map?.invalidateSize?.());
    }, 0);
  }
}

function setupAutoSidebarCollapse(){
  const sidebar = document.getElementById('sidebar');
  if(!sidebar) return;

  if(!sidebarAutoCollapseBound){
    sidebar.addEventListener('mouseenter', () => {
      expandSidebarMenu();
      if(sidebarCollapseTimer) clearTimeout(sidebarCollapseTimer);
    });
    sidebar.addEventListener('mouseleave', scheduleSidebarAutoCollapse);
    window.addEventListener('resize', scheduleSidebarAutoCollapse);
    sidebarAutoCollapseBound = true;
  }

  scheduleSidebarAutoCollapse();
}

function isDesktopSidebarMode(){
  return window.matchMedia('(min-width: 901px)').matches;
}

function isPortraitMenuMode(){
  return window.matchMedia('(orientation: portrait), (max-width: 700px)').matches;
}

function expandSidebarMenu(){
  const sidebar = document.getElementById('sidebar');
  if(sidebar) sidebar.classList.remove('auto-collapsed');
}

function collapseSidebarMenu(){
  const sidebar = document.getElementById('sidebar');
  if(!sidebar || !isDesktopSidebarMode() || sidebar.matches(':hover')) return;
  sidebar.classList.add('auto-collapsed');
}

function scheduleSidebarAutoCollapse(){
  const sidebar = document.getElementById('sidebar');
  if(sidebarCollapseTimer) clearTimeout(sidebarCollapseTimer);
  if(!sidebar) return;

  if(!isDesktopSidebarMode()){
    sidebar.classList.remove('auto-collapsed');
    return;
  }

  if(sidebar.matches(':hover')){
    sidebar.classList.remove('auto-collapsed');
    return;
  }

  sidebarCollapseTimer = setTimeout(collapseSidebarMenu, 10000);
}

function closeSidebarAfterNavigation(){
  const sidebar = document.getElementById('sidebar');
  if(!sidebar) return;
  if(isPortraitMenuMode()) {
    sidebar.classList.remove('open');
    document.querySelector('.mobile-menu-btn')?.setAttribute('aria-expanded', 'false');
    sidebar.classList.remove('auto-collapsed');
    window.setTimeout(() => {
      Object.values(maps || {}).forEach(map => map?.invalidateSize?.());
    }, 0);
  }
}
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
          <button class="btn-primary" onclick="confirmViderContainer('${id}')">Valider</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
}

async function confirmViderContainer(id_boite) {
  const motif = document.getElementById('vider-reason')?.value?.trim();
  if (!motif) {
    return showToast('Veuillez indiquer le motif du vidage.', 'warn');
  }
  try {
    const res = await fetch('/api/container/vider/confirmer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_boite, motif, user_id: currentUserId, role: currentRole })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Demande de vidage envoyée.', 'success');
      closeModal();
    } else {
      showToast(data.error || 'Erreur lors de la demande de vidage.', 'danger');
    }
  } catch (e) {
    showToast('Erreur réseau lors de la demande de vidage.', 'danger');
  }
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
    if(route && typeof L !== 'undefined') L.polyline(route, {color:'#00d4ff', weight:3, opacity:.8}).addTo(maps['map-main']);
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
let AI_CHAT_BLACK_BOX_ID = null;
let AI_PENDING_MESSAGE = null;

function openAIAssistant(containerId=null){
  AI_CHAT_BLACK_BOX_ID = containerId ? String(containerId) : null;
  mountGlobalAIAssistant();
  const panel=document.getElementById('argos-ai-panel');
  const toggle=document.getElementById('argos-ai-toggle');
  if(!panel || !toggle) return;
  panel.hidden=false;
  panel.classList.add('is-open');
  toggle.setAttribute('aria-expanded','true');
  toggle.setAttribute('aria-label','Fermer l’assistant IA ARGOS');
  if(!document.getElementById('ai-chat-messages').childElementCount){
    addAIMessage('Bonjour. Je peux consulter les agents ARGOS et leurs données autorisées pour répondre à votre demande.');
  }
  if(containerId && !panel.dataset.initializedFor){
    panel.dataset.initializedFor=String(containerId);
    addAIMessage(`Boîte ${formatAIReply(containerId)} sélectionnée. Posez votre question pour lancer l’analyse.`);
  }
  setTimeout(()=>document.getElementById('ai-chat-input')?.focus(),0);
}

function mountGlobalAIAssistant(){
  if(document.getElementById('argos-ai-widget')) return;
  const root=document.createElement('aside');
  root.id='argos-ai-widget';
  root.className='argos-ai-widget';
  root.innerHTML=`<button id="argos-ai-toggle" class="argos-ai-toggle" type="button" aria-expanded="false" aria-controls="argos-ai-panel" aria-label="Ouvrir l’assistant IA ARGOS" onclick="toggleGlobalAIAssistant()"><svg class="argos-ai-toggle-logo" aria-hidden="true" viewBox="0 0 82 40"><path d="M4 34 17 5h7l13 29h-8l-3-8H15l-3 8Zm14-14h5l-2.5-8Z" fill="#75e8f5"/><path d="M44 9h7v24h-7zM40 5h15v4H40zM40 33h15v4H40z" fill="#41b9cc"/><path d="M62 11h14a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4h-5l-5 4v-4h-4a4 4 0 0 1-4-4V15a4 4 0 0 1 4-4Z" fill="none" stroke="#f1f5f9" stroke-width="2"/><circle cx="66" cy="20" r="1.5" fill="#f1f5f9"/><circle cx="71" cy="20" r="1.5" fill="#f1f5f9"/><circle cx="76" cy="20" r="1.5" fill="#f1f5f9"/></svg><span class="sr-only">Ouvrir ARGOS IA</span></button>
    <section id="argos-ai-panel" class="argos-ai-panel" role="dialog" aria-labelledby="argos-ai-title" aria-modal="false" hidden>
      <header class="argos-ai-header"><div class="argos-ai-brand"><div class="argos-ai-hero-mark" aria-hidden="true"><svg viewBox="0 0 72 76"><path d="M8 67 29 8h10l21 59H44l-4-13H28l-5 13Z" fill="#175b73" transform="translate(8 5)"/><path d="M8 67 29 8h10l21 59H44l-4-13H28l-5 13Z" fill="#58c7d9"/><path d="m29 43 5-15 5 15Z" fill="#11182a"/></svg></div><div><strong id="argos-ai-title">Assistant ARGOS</strong><span>Orchestrateur multi-agents · Logistique & transport</span></div></div><button class="argos-ai-close" type="button" aria-label="Fermer l’assistant" onclick="toggleGlobalAIAssistant(false)">×</button></header>
      <div id="ai-chat-messages" class="argos-ai-messages" role="log" aria-live="polite" aria-relevant="additions"></div>
      <nav class="argos-ai-suggestions" aria-label="Exemples de questions à poser à l’assistant">
        <span>Essayez une question</span>
        <button type="button" onclick="quickAIMessage('incidents')">Incidents et chocs</button>
        <button type="button" onclick="quickAIMessage('risk')">Risques à venir</button>
        <button type="button" onclick="quickAIMessage('route')">Trajet et zones</button>
        <button type="button" onclick="quickAIMessage('regulation')">Sources réglementaires</button>
        <button type="button" onclick="quickAIMessage('report')">Préparer un rapport</button>
      </nav>
      <form class="argos-ai-form" onsubmit="event.preventDefault();sendAIMessage()"><label class="sr-only" for="ai-chat-input">Votre question à l’assistant ARGOS</label><textarea id="ai-chat-input" rows="2" maxlength="4000" placeholder="Posez une question aux agents ARGOS…" required></textarea><button id="ai-chat-send" class="argos-ai-send" type="submit" aria-label="Envoyer la question"><i class="fas fa-paper-plane" aria-hidden="true"></i></button></form>
    </section>`;
  document.body.appendChild(root);
}

function toggleGlobalAIAssistant(force){
  mountGlobalAIAssistant();
  const panel=document.getElementById('argos-ai-panel');
  const toggle=document.getElementById('argos-ai-toggle');
  const open=typeof force==='boolean'?force:panel.hidden;
  panel.hidden=!open;
  panel.classList.toggle('is-open',open);
  toggle.setAttribute('aria-expanded',String(open));
  toggle.setAttribute('aria-label',open?'Fermer l’assistant IA ARGOS':'Ouvrir l’assistant IA ARGOS');
  if(open){
    if(!document.getElementById('ai-chat-messages').childElementCount){
      addAIMessage('Bonjour. Posez une question et l’orchestrateur consultera les agents ARGOS autorisés pour cette session.');
    }
    setTimeout(()=>document.getElementById('ai-chat-input')?.focus(),0);
  }
  else toggle.focus();
}

document.addEventListener('keydown',event=>{
  if(event.key==='Escape' && !document.getElementById('argos-ai-panel')?.hidden) toggleGlobalAIAssistant(false);
});

function quickAIMessage(type){
  const msgs = {
    incidents:'Analyse les derniers chocs, ouvertures de porte et alertes. Indique les mesures observées, leur heure et les recommandations prudentes.',
    risk:'À partir des dernières mesures, estime les risques observables à court terme et explique les données et seuils utilisés.',
    route:'Résume le trajet récent, les zones traversées, les arrêts inhabituels et la fraîcheur des positions.',
    regulation:'Quelles sources réglementaires peuvent concerner ce trajet ? Indique ce qui reste à vérifier selon la juridiction, le mode et la cargaison.',
    report:'Prépare une synthèse chronologique des événements et recommandations du dossier sélectionné.'
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

async function sendAIMessage(msgText=null, selectedBoxIds=null, alreadyDisplayed=false){
  const input = document.getElementById('ai-chat-input');
  if(!input) return;
  const text = msgText || input.value.trim();
  if(!text) return;
  
  if(!alreadyDisplayed) addUserMessage(text);
  if(!msgText) input.value = '';
  input.disabled = true;
  const loading = addAIMessage(`<em>${AI_CHAT_PROVIDER} consulte l’orchestrateur…</em>`);
  const send=document.getElementById('ai-chat-send');
  if(send) send.disabled=true;
  
  try {
    const res = await secureApiFetch(AI_CHAT_ENDPOINT, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
          message: text,
          black_box_ids: selectedBoxIds || (AI_CHAT_BLACK_BOX_ID ? [AI_CHAT_BLACK_BOX_ID] : [])
      })
    });
    
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || `Serveur IA erreur ${res.status}`);
    
    if(data.status==='needs_container_selection'){
      if(loading) loading.remove();
      AI_PENDING_MESSAGE=text;
      addAIMessage(formatAIReply(data.reply || 'Choisissez les conteneurs à analyser.'));
      renderAIContainerSelection(data.available_containers || []);
      return;
    }

    // gère plusieurs formats de réponse
    const resp = data.reply || data.provider_response?.choices?.[0]?.message?.content || data.provider_response?.choices?.[0]?.text || JSON.stringify(data);
    if(loading) loading.remove();
    if(data.status==='out_of_scope'){
      addAIMessage(formatAIReply(resp));
      AI_CHAT_BLACK_BOX_ID=null;
      return;
    }
    AI_PENDING_MESSAGE=null;
    const answer=addAIMessage(formatAIReply(resp));
    const metadata=document.createElement('div');
    metadata.className='argos-ai-metadata';
    const agents=Array.isArray(data.agents_consulted)?data.agents_consulted:[];
    const sources=Array.isArray(data.sources)?data.sources:[];
    const agentResults=Array.isArray(data.agent_results)?data.agent_results:[];
    const agentLine=document.createElement('div');
    agentLine.textContent=agents.length?`Agents consultés : ${agents.map(a=>typeof a==='string'?a:(a.name||a.id||'agent')).join(' · ')}`:'Aucun agent déclaré par l’orchestrateur.';
    metadata.appendChild(agentLine);
    if(agentResults.length){
      const outcomes=document.createElement('div');
      outcomes.textContent=`Résultats transmis : ${agentResults.map(result=>`${result.agent_id || 'agent'} (${result.status || 'statut inconnu'})`).join(' · ')}`;
      metadata.appendChild(outcomes);
      const exchanged=[];
      const collectExchanges=(result)=>{
        for(const child of result?.data?.consumed_results || []){
          exchanged.push(child.agent_id || 'agent');
          collectExchanges(child);
        }
      };
      agentResults.forEach(collectExchanges);
      if(exchanged.length){
        const exchangeLine=document.createElement('div');
        exchangeLine.textContent=`Résultats inter-agents consommés : ${[...new Set(exchanged)].join(' → ')}`;
        metadata.appendChild(exchangeLine);
      }
    }
    if(sources.length){
      const sourceLine=document.createElement('div');
      sourceLine.appendChild(document.createTextNode('Références : '));
      sources.forEach((source,index)=>{
        if(index)sourceLine.appendChild(document.createTextNode(' · '));
        if(typeof source==='string'){sourceLine.appendChild(document.createTextNode(source));return;}
        const label=source.title||source.source||source.path||source.id||source.source_key||'source';
        const url=String(source.official_url||'');
        if(url.startsWith('https://')){
          const link=document.createElement('a');link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=label;sourceLine.appendChild(link);
        }else sourceLine.appendChild(document.createTextNode(label));
        const status=[source.jurisdiction,source.legal_status,source.applicability_status||'applicabilité à vérifier'].filter(Boolean).join(' · ');
        if(status)sourceLine.appendChild(document.createTextNode(` [${status}]`));
      });
      metadata.appendChild(sourceLine);
    }
    if(data.trace_id){const trace=document.createElement('div');trace.textContent=`Trace : ${data.trace_id}`;metadata.appendChild(trace);}
    answer?.appendChild(metadata);
  } catch(e){
    if(loading) loading.remove();
    addAIMessage(`<span style="color:var(--red)">Erreur IA : ${formatAIReply(e.message)}</span>`);
  } finally {
    input.disabled = false;
    if(send) send.disabled=false;
    AI_CHAT_BLACK_BOX_ID=null;
    input.focus();
  }
}

function renderAIContainerSelection(containers){
  const messages=document.getElementById('ai-chat-messages');
  if(!messages) return;
  const block=document.createElement('div');
  block.className='argos-ai-selection';
  if(!containers.length){
    block.textContent='Aucun conteneur autorisé n’est disponible pour cette session.';
    messages.appendChild(block);
    return;
  }
  const options=containers.map(item=>{
    const id=String(item.black_box_id);
    const label=String(item.label || item.container_id || `Boîte ${id}`);
    const safeId=formatAIReply(id), safeLabel=formatAIReply(label);
    const checked=AI_CHAT_BLACK_BOX_ID && String(AI_CHAT_BLACK_BOX_ID)===id ? ' checked' : '';
    return `<label class="argos-ai-container-option"><input type="checkbox" name="ai-container" value="${safeId}"${checked}><span><strong>${safeLabel}</strong><small>Boîte ARGOS ${safeId}</small></span></label>`;
  }).join('');
  block.innerHTML=`<form onsubmit="event.preventDefault();submitAIContainerSelection(this)"><strong>Choisissez le périmètre d’analyse</strong><div class="argos-ai-container-options">${options}</div><button class="argos-ai-scope-submit" type="submit">Analyser les conteneurs sélectionnés</button></form>`;
  messages.appendChild(block);
  messages.scrollTop=messages.scrollHeight;
}

function submitAIContainerSelection(form){
  const selected=Array.from(form.querySelectorAll('input[name="ai-container"]:checked')).map(input=>input.value);
  if(!selected.length){
    showToast('Sélectionnez au moins un conteneur.','warn');
    return;
  }
  if(!AI_PENDING_MESSAGE) return;
  form.querySelectorAll('input,button').forEach(control=>control.disabled=true);
  return sendAIMessage(AI_PENDING_MESSAGE,selected,true);
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
