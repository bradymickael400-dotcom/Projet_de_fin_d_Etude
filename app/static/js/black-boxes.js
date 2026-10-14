//  NOUVELLES BOÎTES NOIRES - MANAGEMENT
// ══════════════════════════════════════════════════════

/**
 * Ouvre le modal pour créer une nouvelle boîte noire
 */
function openNewBoiteNoireModal() {
  const html = `
    <div class="modal-header">
      <h2><i class="fas fa-cube"></i> Créer une Nouvelle Boîte Noire</h2>
      <button class="close-btn" onclick="closeModal()"><i class="fas fa-times"></i></button>
    </div>
    <div class="modal-content">
      <form id="form-nouvelle-bn" onsubmit="handleCreateBoiteNoire(event)">
        
        <div class="form-group">
          <label>Numéro de Conteneur ISO 6346 *</label>
          <input type="text" id="bn-container" placeholder="Ex: MSCU1234566" required 
                 onchange="updateIsoFeedback(this, 'iso-feedback')">
          <div id="iso-feedback" class="small-hint"></div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Propriétaire/Entreprise (optionnel)</label>
            <select id="bn-proprietaire"></select>
          </div>
          <div class="form-group">
            <label>Type de Boîte *</label>
            <select id="bn-type-boite" required>
              <option value="monthly">Mensuelle</option>
              <option value="weekly">Hebdomadaire</option>
              <option value="daily">Quotidienne</option>
              <option value="hourly">Horaire</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>Identifiant unique ESP32</label>
          <input type="text" id="bn-device-uid" placeholder="Détection du boîtier…" readonly required>
          <div id="bn-device-status" class="small-hint">Connexion au point d’accès ARGOS en cours…</div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Version du Firmware</label>
            <input type="text" id="bn-versions" value="v2.1" placeholder="v2.1">
          </div>
          <div class="form-group">
            <label>Température Max (°C)</label>
            <input type="number" id="bn-temp-max" value="32" step="0.1">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Température Min (°C)</label>
            <input type="number" id="bn-temp-min" value="-10" step="0.1">
          </div>
          <div class="form-group">
            <label>Humidité Max (%)</label>
            <input type="number" id="bn-humi-max" value="75" min="0" max="100">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Choc Max (G)</label>
            <input type="number" id="bn-choc-max" value="5" step="0.1">
          </div>
          <div class="form-group">
            <label>Pression Min (hPa)</label>
            <input type="number" id="bn-pression-min" value="995" step="0.1">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Vitesse Max (km/h)</label>
            <input type="number" id="bn-vitesse-max" value="90">
          </div>
          <div class="form-group">
            <label>Angle Max (°)</label>
            <input type="number" id="bn-angle-max" value="30">
          </div>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Créer Boîte Noire</button>
          <button type="button" class="btn btn-secondary" onclick="closeModal()"><i class="fas fa-times"></i> Annuler</button>
        </div>
      </form>
    </div>
  `;
  
  showModal(html, '600px');
  loadProprietairesForBN();
  discoverArgosDevice();
}

/** Récupère l’identifiant gravé dans le firmware via le portail captif. */
async function discoverArgosDevice() {
  const input = document.getElementById('bn-device-uid');
  const status = document.getElementById('bn-device-status');
  if (!input) return;
  const endpoints = ['/api/device/info', 'http://192.168.4.1/api/device/info', 'http://192.168.4.1/device/info'];
  for (const endpoint of endpoints) {
    try {
      const res = await fetch(endpoint, {headers: {
        'Accept': 'application/json',
        ...(endpoint.startsWith('http:') ? {
          'X-ARGOS-Setup-Key': 'ARGOS-PROVISION-2026',
          'X-ARGOS-Client-Timestamp': new Date().toISOString()
        } : {})
      }, mode: endpoint.startsWith('http:') ? 'cors' : 'same-origin'});
      if (!res.ok) continue;
      const info = await res.json();
      const uid = info.device_uid || info.deviceId || info.black_box_id || info.id_boite;
      if (uid) {
        input.value = String(uid);
        status.textContent = 'Boîtier détecté et prêt à être enregistré.';
        status.style.color = '#22c55e';
        return;
      }
    } catch (_) { /* point d’accès non joignable, essayer l’URL suivante */ }
  }
  status.textContent = 'Aucun boîtier détecté. Connectez-vous au Wi‑Fi ARGOS-SETUP puis actualisez.';
  status.style.color = '#f59e0b';
}

/**
 * Charge les propriétaires pour le dropdown
 */
async function loadProprietairesForBN() {
  try {
    const res = await secureApiFetch('/api/companies');
    const companies = await res.json();
    const select = document.getElementById('bn-proprietaire');
    if (!Array.isArray(companies)) return;
    select.innerHTML = '<option value="">Sans entreprise</option>';
    
    companies.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.nom_agence;
      select.appendChild(opt);
    });
  } catch(e) {
    console.error('Erreur chargement propriétaires:', e);
  }
}

/**
 * Handle création boîte noire
 */
async function handleCreateBoiteNoire(event) {
  event.preventDefault();
  const ownerValue = document.getElementById('bn-proprietaire').value;
  
  const data = {
    id_conteneurs: document.getElementById('bn-container').value.trim().toUpperCase(),
    id_proprietaire: ownerValue ? parseInt(ownerValue) : null,
    type_boite: document.getElementById('bn-type-boite').value,
    versions: document.getElementById('bn-versions').value,
    temp_max: parseFloat(document.getElementById('bn-temp-max').value),
    temp_min: parseFloat(document.getElementById('bn-temp-min').value),
    humi_max: parseFloat(document.getElementById('bn-humi-max').value),
    choc_max: parseFloat(document.getElementById('bn-choc-max').value),
    pression_min: parseFloat(document.getElementById('bn-pression-min').value),
    vitesse_max: parseFloat(document.getElementById('bn-vitesse-max').value),
    angle_max: parseFloat(document.getElementById('bn-angle-max').value),
    device_uid: document.getElementById('bn-device-uid')?.value.trim() || null,
  };
  
  try {
    const res = await secureApiFetch('/api/boites-noires/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await res.json();
    
    if (!res.ok) {
      alert('<i class="fas fa-times-circle"></i> Erreur: ' + (result.error || 'Création échouée'));
      return;
    }
    
    const cmd = result.assignment_command;
    showToast('Boîte noire créée. ID: ' + result.id_boite +
      (cmd?.status === 'published' ? ' — identifiant transmis au prototype' : ''),
      cmd?.status === 'pending_device_enrollment' ? 'warn' : 'success');
    
    // Afficher le QR code
    setTimeout(() => {
      showQRCodeModal(result.id_boite, result.numero_serie);
    }, 500);
    
    closeModal();
  } catch(e) {
    console.error('Erreur création BN:', e);
    alert('<i class="fas fa-times-circle"></i> Erreur: ' + e.message);
  }
}

/**
 * Affiche le modal du QR code
 */
function showQRCodeModal(idBoite, numeroSerie) {
  const html = `
    <div class="modal-header">
      <h2>QR Code Généré</h2>
      <button class="close-btn" onclick="closeModal()">< i class="fas fa-times"></i></button>
    </div>
    <div class="modal-content" style="text-align: center;">
      <div style="background: white; padding: 20px; border-radius: 8px; display: inline-block;">
        <img id="qr-image" src="/api/boites-noires/${idBoite}/generate-qr" 
             alt="QR Code" style="width: 300px; height: 300px;">
      </div>
      <p style="margin-top: 20px; font-size: 18px; font-weight: bold;">
        Numéro de série: <code>${numeroSerie}</code>
      </p>
      <p style="color: var(--text-secondary); margin-bottom: 20px;">
        Scannez ce QR code pour attribuer un conteneur
      </p>
      <div class="form-actions">
        <button class="btn btn-primary" onclick="downloadQRCode(${idBoite}, '${numeroSerie}')">
          <i class="fas fa-download"></i> Télécharger QR Code
        </button>
        <button class="btn btn-secondary" onclick="closeModal()">Fermer</button>
      </div>
    </div>
  `;
  showModal(html, '500px');
}

/**
 * Télécharge le QR code
 */
function downloadQRCode(idBoite, numeroSerie) {
  const link = document.createElement('a');
  link.href = `/api/boites-noires/${idBoite}/generate-qr`;
  link.download = `qrcode_${numeroSerie}.png`;
  link.click();
}

/**
 * Scan QR code - redirige vers interface d'attribution
 */
function openScanQRCodeModal() {
  const html = `
    <div class="modal-header">
      <h2>Scanner QR Code</h2>
      <button class="close-btn" onclick="closeModal()">< i class="fas fa-times"></i></button>
    </div>
    <div class="modal-content">
      <div style="text-align: center; padding: 30px;">
        <p>Entrez l'UUID du QR code ou accédez à:</p>
        <input type="text" id="scan-uuid" placeholder="Collez l'UUID ici" 
               style="width: 100%; padding: 10px; margin: 20px 0; font-family: monospace;">
        <div class="form-actions">
          <button class="btn btn-primary" onclick="processScanQR()">Scan</button>
          <button class="btn btn-secondary" onclick="closeModal()">Annuler</button>
        </div>
      </div>
    </div>
  `;
  showModal(html, '500px');
}

/**
 * Traite le scan du QR code
 */
async function processScanQR() {
  const uuid = document.getElementById('scan-uuid').value.trim();
  if (!uuid) {
    alert('UUID requis');
    return;
  }
  
  try {
    const res = await secureApiFetch(`/api/boites-noires/scan/${uuid}`);
    const data = await res.json();
    
    if (!res.ok) {
      alert('<i class="fas fa-times-circle"></i> QR Code invalide: ' + (data.error || 'Non trouvé'));
      return;
    }
    
    // Rediriger vers interface d'attribution
    closeModal();
    currentPage = 'attribution-boite';
    showAttributionInterface(data);
    
  } catch(e) {
    alert('Erreur scan: ' + e.message);
  }
}

/**
 * Affiche l'interface d'attribution de conteneur à boîte
 */
function showAttributionInterface(scanData) {
  const boite = scanData.boite;
  const isSuperadmin = currentRole === 'superadmin';
  
  let html = `
    <div style="max-width: 800px; margin: 0 auto;">
      <div class="card">
        <h2><i class="fas fa-cube"></i> Attribution de Conteneur</h2>
        <p style="color: var(--text-secondary);">Boîte: <strong>${boite.numero_serie}</strong> (ID: ${boite.id_boite})</p>
        
        <form id="form-attribution" onsubmit="handleAttributionSubmit(event, ${boite.id_boite})">
  `;
  
  if (isSuperadmin && scanData.companies.length > 0) {
    html += `
      <div class="form-group">
        <label>Choisir Entreprise *</label>
        <select id="attr-company" required onchange="updateContainerFilterByCompany(event)">
          <option value="">-- Sélectionnez une entreprise --</option>
    `;
    scanData.companies.forEach(c => {
      html += `<option value="${c.id}">${c.nom_agence}</option>`;
    });
    html += `</select></div>`;
  }
  
  html += `
      <div class="form-group">
        <label>Choisir Conteneur * (Libres uniquement)</label>
        <select id="attr-container" required>
          <option value="">-- Sélectionnez un conteneur --</option>
  `;
  
  scanData.containers.forEach(c => {
    html += `<option value="${c.id_conteneurs}">${c.id_conteneurs} (${c.taile_perimetre})</option>`;
  });
  
  html += `
        </select>
      </div>
      
      <div class="form-actions">
        <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Attribuer Conteneur</button>
        <button type="button" class="btn btn-secondary" onclick="goToPage('containers')">Retour</button>
      </div>
    </form>
      </div>
    </div>
  `;
  
  const target = document.getElementById('pages-container') || document.getElementById('main-content');
  if (!target) {
    console.warn('Aucun conteneur de page disponible pour afficher l’attribution.');
    return;
  }
  target.innerHTML = html;
  
  // Stocker les données pour le traitement
  window.currentAttributionData = scanData;
}

/**
 * Mettre à jour les conteneurs filtrés par entreprise
 */
function updateContainerFilterByCompany(event) {
  const companyId = event.target.value;
  // Dans une vraie application, vous refiltreriez les conteneurs
  // Pour cette démo, on garde les mêmes
}

/**
 * Handle soumission attribution
 */
async function handleAttributionSubmit(event, idBoite) {
  event.preventDefault();
  
  const idConteneur = document.getElementById('attr-container').value;
  const idProprietaire = document.getElementById('attr-company')?.value || null;
  
  if (!idConteneur) {
    alert('Veuillez sélectionner un conteneur');
    return;
  }
  
  try {
    const res = await secureApiFetch(`/api/boites-noires/${idBoite}/assign-container`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_conteneurs: idConteneur,
        id_proprietaire: idProprietaire ? parseInt(idProprietaire) : undefined
      })
    });
    
    const result = await res.json();
    
    if (!res.ok) {
      alert('<i class="fas fa-times-circle"></i> Erreur: ' + (result.error || 'Attribution échouée'));
      return;
    }
    
    showToast('<i class="fas fa-check-circle"></i> Conteneur attribué avec succès!');
    goToPage('containers');
    
  } catch(e) {
    alert('Erreur: ' + e.message);
  }
}

// ══════════════════════════════════════════════════════
//  WIFI SETTINGS
// ══════════════════════════════════════════════════════

/**
 * Ouvre le modal de configuration WiFi
 */
function openWiFiSettingsModal() {
  const html = `
    <div class="modal-header">
      <h2>📶 Configuration WiFi</h2>
      <button class="close-btn" onclick="closeModal()">< i class="fas fa-times"></i></button>
    </div>
    <div class="modal-content">
      <form id="form-wifi" onsubmit="handleWiFiUpdate(event)">
        <div class="form-group">
          <label>Nom du WiFi (SSID) *</label>
          <input type="text" id="wifi-name" placeholder="Ex: MyNetwork" required>
        </div>
        
        <div class="form-group">
          <label>Mot de passe WiFi *</label>
          <input type="password" id="wifi-password" placeholder="Mot de passe" required>
          <small style="color: var(--text-secondary); display: block; margin-top: 5px;">
            Chiffré et stocké en toute sécurité
          </small>
        </div>
        
        <div class="form-actions">
          <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <button type="button" class="btn btn-secondary" onclick="closeModal()">Annuler</button>
        </div>
      </form>
    </div>
  `;
  
  showModal(html, '400px');
}

/**
 * Met à jour les paramètres WiFi
 */
async function handleWiFiUpdate(event) {
  event.preventDefault();
  
  const data = {
    wifi_name: document.getElementById('wifi-name').value.trim(),
    wifi_password: document.getElementById('wifi-password').value
  };
  
  if (!data.wifi_name || !data.wifi_password) {
    alert('Tous les champs WiFi sont requis');
    return;
  }
  
  try {
    const res = await secureApiFetch('/api/wifi/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await res.json();
    
    if (!res.ok) {
      alert('<i class="fas fa-times-circle"></i> Erreur: ' + (result.error || 'Mise à jour échouée'));
      return;
    }
    
    showToast('<i class="fas fa-check-circle"></i> Paramètres WiFi enregistrés');
    closeModal();
    
  } catch(e) {
    alert('Erreur: ' + e.message);
  }
}

// ══════════════════════════════════════════════════════
//  ARCHIVE
// ══════════════════════════════════════════════════════

/**
 * Affiche la page d'archive
 */
async function showArchivePage() {
  currentPage = 'archive';

  const html = `
    <div style="max-width: 1000px; margin: 0 auto;">
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h2><i class="fas fa-archive"></i> Archives des éléments retirés</h2>
          <button class="btn btn-secondary" onclick="goToPage('containers')"><i class="fas fa-arrow-left"></i> Retour</button>
        </div>

        <p style="color: var(--text-secondary); margin-bottom: 20px;">
          Boîtes et conteneurs actuellement en état <strong>off</strong>
        </p>

        <div id="archive-list" style="min-height: 300px;">
          <div class="loading">Chargement des éléments archivés...</div>
        </div>
      </div>
    </div>
  `;

  setTimeout(() => loadArchivedContainers(), 0);
  return html;
}

/**
 * Charge et affiche les conteneurs archivés
 */
async function loadArchivedContainers() {
  try {
    const listDiv = document.getElementById('archive-list');
    if (!listDiv) {
      console.error('Élément archive-list non trouvé');
      return;
    }

    const boxesRes = await secureApiFetch('/api/black-boxes/archived');
    const boxesData = await boxesRes.json();
    const boxesOff = Array.isArray(boxesData?.boxes)
      ? boxesData.boxes
      : [];

    const containersRes = await secureApiFetch('/api/containers/archived');
    const containers = await containersRes.json();
    const containersOff = Array.isArray(containers)
      ? containers
      : [];

    const items = [
      ...boxesOff.map(b => ({ type: 'box', id: b.id_boite, label: b.numero_serie || b.container_id || 'Boîte retirée', subtitle: b.container_id || b.proprietaire || 'Boîte noire', status: b.status || 'off', count: 0 })),
      ...containersOff.map(c => ({ type: 'container', id: c.id_conteneurs, label: c.id_conteneurs, subtitle: `${c.taile_perimetre || '—'} • ${c.type_conteneurs || '—'}`, status: c.status || 'off', count: c.in_boites || 0 }))
    ];

    if (items.length === 0) {
      listDiv.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">Aucun élément en état off</p>';
      return;
    }

    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">';

    items.forEach(item => {
      const isBox = item.type === 'box';
      html += `
        <div class="card" style="background: var(--bg-secondary); border-left: 4px solid var(--amber);">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
            <div>
              <strong>${escapeHTML(item.label)}</strong>
              <div style="font-size: 12px; color: var(--text-secondary);">
                ${escapeHTML(item.subtitle)}
              </div>
            </div>
            <span style="background: var(--amber); color: black; padding: 2px 8px; border-radius: 4px; font-size: 11px;">
              ${(item.status || 'off').toUpperCase()}
            </span>
          </div>

          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 10px;">
            Type: <code>${isBox ? 'Boîte noire' : 'Conteneur'}</code>
            <br>Liens: ${item.count}
          </div>

          <button class="btn btn-small btn-secondary"
                  onclick="${isBox ? `restoreBlackBox('${item.id}')` : `restoreContainer('${item.id}')`}">
            <i class="fas fa-undo"></i> Restaurer
          </button>
        </div>
      `;
    });

    html += '</div>';
    listDiv.innerHTML = html;

  } catch (e) {
    console.error('Erreur archive:', e);
    const listDiv = document.getElementById('archive-list');
    if (listDiv) {
      listDiv.innerHTML = '<p style="color: var(--red);">Erreur: ' + e.message + '</p>';
    }
  }
}

/**
 * Archive un conteneur
 */
async function archiveContainer(idConteneur) {
  if (typeof openDeleteConfirmModal === 'function') {
    openDeleteConfirmModal({
      title: 'Supprimer conteneur',
      message: `Supprimer le conteneur ${idConteneur} ? Il passera hors ligne et ses boîtes liées seront libérées.`,
      details: '<i class="fas fa-link"></i> Cette suppression sera enregistrée dans la blockchain ARGOS.',
      confirmLabel: 'Supprimer le conteneur',
      onConfirm: `confirmArchiveContainer(${JSON.stringify(String(idConteneur))})`
    });
    return;
  }
  return confirmArchiveContainer(idConteneur);
}

async function confirmArchiveContainer(idConteneur) {
  
  try {
    const res = await secureApiFetch(`/api/containers/${encodeURIComponent(idConteneur)}`, {
      method: 'DELETE'
    });
    
    const result = await res.json();
    
    if (!res.ok) {
      showToast('<i class="fas fa-times-circle"></i> ' + (result.error || 'Suppression échouée'), 'danger');
      return;
    }
    
    showToast('<i class="fas fa-check-circle"></i> Conteneur supprimé', 'success');
    closeModal();
    // Rafraîchir la liste
    if (currentPage === 'archive') {
      loadArchivedContainers();
    } else {
      if (typeof loadContainerData === 'function') await loadContainerData();
      renderPage('containers');
    }
    
  } catch(e) {
    showToast('Erreur: ' + e.message, 'danger');
  }
}

/**
 * Restaure un conteneur archivé
 */
async function restoreContainer(idConteneur) {
  if (!confirm('Restaurer ce conteneur?')) {
    return;
  }
  
  try {
    const res = await secureApiFetch(`/api/containers/${idConteneur}/restore`, {
      method: 'POST'
    });
    
    const result = await res.json();
    
    if (!res.ok) {
      alert('<i class="fas fa-times-circle"></i> Erreur: ' + (result.error || 'Restauration échouée'));
      return;
    }
    
    showToast('<i class="fas fa-check-circle"></i> Conteneur restauré');
    if (currentPage === 'archive') {
      renderPage('archive');
    } else {
      loadArchivedContainers();
    }
    
  } catch(e) {
    alert('Erreur: ' + e.message);
  }
}

async function restoreBlackBox(boxId) {
  if (!confirm('Restaurer cette boîte noire?')) {
    return;
  }

  try {
    const res = await secureApiFetch(`/api/black-boxes/${boxId}/restore`, { method: 'POST' });
    const result = await res.json();

    if (!res.ok) {
      showToast('<i class="fas fa-times-circle"></i> ' + (result.error || 'Restauration échouée'), 'error');
      return;
    }

    showToast('<i class="fas fa-check-circle"></i> Boîte restaurée', 'success');
    if (currentPage === 'archive') {
      renderPage('archive');
    } else {
      renderPage('my-boxes');
    }
  } catch (e) {
    showToast('<i class="fas fa-times-circle"></i> Erreur: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════
//  🔧 BOÎTES NOIRES & WIFI SETTINGS - VERSION 2
// ══════════════════════════════════════════════════════════════════

// PAGE: Mes Boîtes Noires
async function buildMyBlackBoxesPage() {
  currentPage = 'my-boxes';
  try {
    const res = await secureApiFetch('/api/black-boxes/my-boxes');
    const data = await res.json();
    if (!res.ok) return `<div class="page active"><div class="card" style="color:red">Erreur: ${data.error}</div></div>`;
    
    const boxes = data.boxes || [];
    window.argosBlackBoxesById = Object.fromEntries(
      boxes.map(box => [String(box.id_boite), box])
    );
    if (boxes.length === 0) {
      return `
        <div class="page active">
          <div class="page-header">
            <div class="page-title"><i class="fas fa-cube cube-3d-bounce"></i> Mes Boîtes Noires <small>0 boîte</small></div>
          </div>
          <div class="card" style="text-align: center; padding: 60px 20px; color: var(--text-secondary);">
            <div style="font-size: 48px; margin-bottom: 20px;"><i class="fas fa-cube cube-3d-bounce cube-3d-large"></i></div>
            <div>Aucune boîte noire active</div>
            <button class="btn-primary" onclick="openCreateBlackBoxModal()" style="margin-top: 20px;">
              <i class="fas fa-plus"></i> Créer une Boîte Noire
            </button>
          </div>
        </div>
      `;
    }
    
    const boxesHtml = boxes.map(box => {
      const telemetry = box.telemetry || {};
      const quality = telemetry.quality && typeof telemetry.quality === 'object' ? telemetry.quality : {};
      const measuredBattery = quality.batteryMeasured !== false && telemetry.battery_level != null
        ? Number(telemetry.battery_level) : null;
      const batteryPercent = Number.isFinite(measuredBattery) ? measuredBattery : null;
      const batteryColor = batteryPercent == null ? 'var(--text3)' : (batteryPercent >= 50 ? 'green' : batteryPercent >= 25 ? 'orange' : 'red');
      const qualityLabels = [];
      if (quality.dhtValid === false) qualityLabels.push('DHT22 invalide');
      if (quality.mpuValid === false) qualityLabels.push('MPU6050 invalide');
      if (quality.distanceValid === false) qualityLabels.push('Distance invalide');
      if (quality.pressureMeasured === false) qualityLabels.push('Pression estimée');
      if (quality.batteryMeasured === false) qualityLabels.push('Batterie estimée');
      const isDeadClass = box.is_dead ? 'style="opacity: 0.6; border-left: 3px solid red;"' : '';
      const isUnassigned = box.assignment_status === 'unassigned' || !box.container_id;
      const deviceConnected = Boolean(box.device_connected);
      const deviceLabel = box.device_uid || 'Aucun dispositif lié';
      const deviceState = deviceConnected ? 'CONNECTÉ' : (box.device_status === 'PENDING_ENROLLMENT' ? 'EN ATTENTE D’ENRÔLEMENT' : 'HORS LIGNE');
      const deviceColor = deviceConnected ? '#00a86b' : (box.device_status === 'PENDING_ENROLLMENT' ? '#f0a500' : '#d9534f');
      
      return `
        <div class="card" data-argos-direct-box="${box.id_boite}" ${isDeadClass}>
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
            <div>
              <div style="font-size: 18px; font-weight: bold;">${box.numero_serie}</div>
              <div style="margin-top:4px;font:12px monospace;color:var(--text-secondary)">
                Dispositif : <strong>${escapeHTML(deviceLabel)}</strong>
                ${box.device_hardware_serial && box.device_hardware_serial !== box.device_uid ? ` • série ${escapeHTML(box.device_hardware_serial)}` : ''}
                ${box.device_firmware ? ` • firmware ${escapeHTML(box.device_firmware)}` : ''}
                ${box.device_protocol ? ` • protocole ${escapeHTML(box.device_protocol)}` : ''}
                ${box.device_last_ip ? ` • IP ${escapeHTML(box.device_last_ip)}` : ''}
              </div>
              <div style="margin-top:3px;font-size:11px;color:${deviceColor}">
                <i class="fas fa-circle" style="font-size:8px"></i> ${deviceState}
                ${box.last_seen_at ? ` • dernière transmission ${new Date(box.last_seen_at).toLocaleString('fr-FR')}` : ' • aucune transmission reçue'}
              </div>
              <div data-argos-direct-status style="margin-top:3px;font-size:11px;color:var(--text3)"></div>
              <div style="color: var(--text-secondary); font-size: 12px;">Conteneur: ${box.container_id || 'Aucun'}</div>
              <div style="margin-top:6px;font-size:12px;color:${isUnassigned ? '#8a8f98' : '#00a86b'}">
                <i class="fas fa-circle" style="font-size:9px"></i>
                Télémétrie ${isUnassigned ? 'non assignée' : 'assignée'}
              </div>
            </div>
            <div style="text-align: right;">
              <span class="badge" style="background: ${box.status === 'active' ? 'green' : 'gray'}; padding: 4px 12px; border-radius: 20px; color: white; font-size: 11px; font-weight: bold;">
                ${box.status === 'active' ? '<i class="fas fa-circle" style="color: #00e676;"></i> ACTIF' : '<i class="fas fa-circle"></i> ' + box.status.toUpperCase()}
              </span>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;background:var(--bg3);padding:10px;border-radius:8px;margin-bottom:15px;font-size:12px;">
            <div><span style="color:var(--text-secondary)">Température</span><br><strong data-argos-direct-metric="temperature">${telemetry.temperature ?? '—'}${telemetry.temperature != null ? ' °C' : ''}</strong></div>
            <div><span style="color:var(--text-secondary)">Humidité</span><br><strong data-argos-direct-metric="humidity">${telemetry.humidity ?? '—'}${telemetry.humidity != null ? ' %' : ''}</strong></div>
            <div><span style="color:var(--text-secondary)">Distance</span><br><strong data-argos-direct-metric="distance">${telemetry.distance_cm ?? '—'}${telemetry.distance_cm != null ? ' cm' : ''}</strong></div>
            <div><span style="color:var(--text-secondary)">Pression</span><br><strong data-argos-direct-metric="pressure">${telemetry.pressure ?? '—'}${telemetry.pressure != null ? ' hPa' : ''}</strong></div>
            <div><span style="color:var(--text-secondary)">Choc</span><br><strong data-argos-direct-metric="shock">${telemetry.shock ?? '—'}${telemetry.shock != null ? ' G' : ''}</strong></div>
            <div><span style="color:var(--text-secondary)">Accélération X/Y/Z</span><br><strong data-argos-direct-metric="acceleration">${telemetry.acceleration_x ?? '—'} / ${telemetry.acceleration_y ?? '—'} / ${telemetry.acceleration_z ?? '—'}</strong></div>
            <div><span style="color:var(--text-secondary)">GPS</span><br><strong data-argos-direct-metric="position">${telemetry.latitude ?? '—'}, ${telemetry.longitude ?? '—'}</strong></div>
            <div><span style="color:var(--text-secondary)">Dernière mesure</span><br><strong data-argos-direct-metric="timestamp">${telemetry.measured_at ? new Date(telemetry.measured_at).toLocaleString('fr-FR') : '—'}</strong></div>
          </div>
          <div data-argos-direct-quality style="font-size:11px;color:var(--amber);margin:-8px 0 15px">${qualityLabels.length ? qualityLabels.join(' • ') : 'Qualité capteurs en attente…'}</div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; font-size: 13px;">
            <div>
              <div style="color: var(--text-secondary); margin-bottom: 4px;">Déploiement</div>
              <div style="font-weight: bold;">${box.deployment_date ? new Date(box.deployment_date).toLocaleDateString('fr-FR') : '—'}</div>
            </div>
            <div>
              <div style="color: var(--text-secondary); margin-bottom: 4px;">Fin de vie</div>
              <div style="font-weight: bold;">${box.is_dead ? '<i class="fas fa-exclamation-triangle" style="color: orange;"></i> EXPIRÉ' : (box.end_of_life_date ? new Date(box.end_of_life_date).toLocaleDateString('fr-FR') : '—')}</div>
            </div>
            <div>
              <div style="color: var(--text-secondary); margin-bottom: 4px;">Batterie</div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <div style="flex: 1; background: var(--bg3); height: 8px; border-radius: 4px; overflow: hidden;">
                  <div style="background: ${batteryColor}; height: 100%; width: ${batteryPercent ?? 0}%;"></div>
                </div>
                <span style="font-weight: bold; color: ${batteryColor};">${batteryPercent == null ? '— (non mesurée)' : batteryPercent + '%'}</span>
              </div>
            </div>
            <div>
              <div style="color: var(--text-secondary); margin-bottom: 4px;">Durée restante</div>
              <div style="font-weight: bold; color: ${box.days_remaining < 7 ? 'orange' : 'inherit'};">
                ${box.is_dead ? 'Expiré' : (box.days_remaining == null ? 'À configurer' : box.days_remaining + ' jours')}
              </div>
            </div>
          </div>
          
          <div style="background: var(--bg3); padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 11px; color: var(--text-secondary); font-family: monospace; word-break: break-all;">
            UUID: ${box.uuid}
          </div>
          
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="btn-primary" onclick="downloadBoxQRCode(${box.id_boite}, '${box.numero_serie}')">
              <i class="fas fa-qrcode"></i> Télécharger QR
            </button>
            <button class="btn-secondary" onclick="viewBoxQRModal(${box.id_boite})">
              <i class="fas fa-eye"></i> Voir QR
            </button>
            <button class="btn-secondary" onclick="openChangeContainerModal('${box.id_boite}')">
              <i class="fas fa-exchange-alt"></i> Changer
            </button>
            <button class="btn-secondary" onclick="openEditBlackBoxModal(window.argosBlackBoxesById[String(${box.id_boite})])">
              <i class="fas fa-cog"></i> Configurer
            </button>
            ${box.device_uid ? `<button class="btn-secondary" onclick="openBlackBoxConsultModal(${box.id_boite})"><i class="fas fa-route"></i> Historique du trajet</button>` : ''}
            ${box.device_uid ? `<button class="btn-secondary" onclick="reconnectBlackBox(${box.id_boite})"><i class="fas fa-wifi"></i> Configurer le réseau ESP32</button>` : ''}
            <button class="btn-danger" onclick="archiveBlackBox(${box.id_boite})">
              <i class="fas fa-trash"></i> Supprimer
            </button>
          </div>
        </div>
      `;
    }).join('');
    
    return `
      <div class="page active">
        <div class="page-header">
          <div class="page-title"><i class="fas fa-cube cube-3d-bounce"></i> Mes Boîtes Noires <small>${boxes.length} boîte${boxes.length !== 1 ? 's' : ''}</small></div>
          <button class="btn-primary" onclick="openCreateBlackBoxModal()" style="padding: 8px 16px;">
            <i class="fas fa-plus"></i> Nouvelle Boîte
          </button>
        </div>
        <div style="display: grid; grid-template-columns: 1fr; gap: 15px;">
          ${boxesHtml}
        </div>
      </div>
    `;
  } catch(e) {
    console.error('Erreur:', e);
    return `<div class="page active"><div class="card" style="color:red">Erreur: ${e.message}</div></div>`;
  }
}

let argosHistoryMap = null;
let argosCurrentBoxHistory = null;
let argosAudioObjectUrl = null;

function argosHistoryAlerts(point) {
  let alerts = point?.notif || [];
  if (typeof alerts === 'string') {
    try { alerts = JSON.parse(alerts); } catch (_) { alerts = alerts ? [alerts] : []; }
  }
  return Array.isArray(alerts) ? alerts : [];
}

function argosHistoryPlace(point) {
  const places = [
    ['Yaoundé',3.8480,11.5021], ['Awaé',3.8330,11.6830],
    ['Ayos',3.9000,12.5160], ['Abong-Mbang',3.9830,13.1830],
    ['Doumé',4.2330,13.4500], ['Bertoua',4.5770,13.6846]
  ];
  if (point?.latitude == null || point?.longitude == null) return 'Position inconnue';
  return places.reduce((best, place) => {
    const distance = Math.hypot(Number(point.latitude)-place[1], Number(point.longitude)-place[2]);
    return !best || distance < best.distance ? {name:place[0], distance} : best;
  }, null).name;
}

async function openBlackBoxConsultModal(boxId) {
  try {
    const response = await secureApiFetch(`/api/black-boxes/${encodeURIComponent(boxId)}/history?limit=1200`);
    const data = await response.json().catch(()=>({}));
    if (!response.ok) return showToast(data.error || 'Historique indisponible', 'error');
    argosCurrentBoxHistory = data;
    renderBlackBoxConsultModal(data);
  } catch (error) {
    showToast(`Historique indisponible : ${error.message}`, 'error');
  }
}

function renderBlackBoxConsultModal(data) {
  const box = window.argosBlackBoxesById?.[String(data.box.id)] || {};
  const telemetry = box.telemetry || {};
  const modes = telemetry.modes || {};
  const points = (data.points || []).filter(point=>point.latitude != null && point.longitude != null);
  const eventCount = points.filter(point=>argosHistoryAlerts(point).length || Number(point.shock) > 5 || point.audio_url).length;
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:1100px;width:92vw;max-height:92vh;overflow-y:auto">
        <div class="modal-header">
          <div><div class="modal-title" style="font-family:var(--display);color:var(--cyan)"><i class="fas fa-route"></i> ${escapeHTML(data.box.serial || `Boîte ${data.box.id}`)}</div>
          <div style="font-size:11px;color:var(--text3)">${escapeHTML(data.box.deviceUid || '—')} · ${escapeHTML(data.box.containerId || 'Sans conteneur')}</div></div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
            <span class="badge badge-info">${points.length} positions</span>
            <span class="badge ${eventCount ? 'badge-danger' : 'badge-ok'}">${eventCount} événement(s)</span>
            <span class="badge badge-info">Yaoundé → Bertoua</span>
          </div>
          <div id="argos-history-map" style="height:430px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg3)"></div>
          <div style="margin-top:14px;padding:12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--card2)">
            <div style="font-size:12px;color:var(--text3);margin-bottom:8px">COMMANDES DU DISPOSITIF</div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px">
              ${[
                ['security','Mode sécurité','fa-shield-alt',modes.securityEnabled ?? telemetry.security_enabled],
                ['recording','Enregistrer les sons','fa-microphone',modes.audioRecordingEnabled],
                ['listening','Écoute audio','fa-headphones',modes.audioListeningEnabled],
                ['flame-detection','Détection de flammes','fa-fire',modes.flameDetectionEnabled]
              ].map(([command,label,icon,checked])=>`<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg3)">
                <div><div style="font-size:12px;font-weight:600"><i class="fas ${icon}"></i> ${label}</div><div style="font-size:10px;color:var(--text3)">Commande distante</div></div>
                <label class="toggle-switch"><input type="checkbox" ${checked?'checked':''} onchange="sendContainerCommand('${data.box.id}','${command}',this.checked)"><span class="toggle-slider"></span></label>
              </div>`).join('')}
            </div>
          </div>
          <div style="margin-top:14px">
            <div style="font-size:12px;color:var(--text3);margin-bottom:8px">ÉVÉNEMENTS DU TRAJET — cliquez pour consulter toutes les données</div>
            <div style="display:grid;gap:6px">${points.map((point,index)=>{
              const alerts=argosHistoryAlerts(point); const critical=alerts.length||Number(point.shock)>5;
              return `<div style="display:flex;gap:6px;align-items:center"><button class="btn-secondary" style="flex:1;text-align:left;justify-content:flex-start;border-color:${critical?'var(--red)':'var(--border)'}" onclick="openBlackBoxHistoryEvent(${index})"><i class="fas ${critical?'fa-exclamation-triangle':'fa-wave-square'}" style="color:${critical?'var(--red)':'var(--cyan)'}"></i> ${new Date(point.measured_at).toLocaleString('fr-FR')} — ${escapeHTML(argosHistoryPlace(point))} — ${escapeHTML(alerts.join(' · ') || 'Mesure normale')}</button>${point.recording_uid?`<button class="btn-icon" title="Lire le son associé" onclick="playProtectedEventAudio('${escapeHTML(point.recording_uid)}',this)"><i class="fas fa-play"></i> Lire</button>`:''}</div>`;
            }).join('') || '<div style="color:var(--text3);font-size:12px">Aucun événement critique enregistré.</div>'}</div>
          </div>
        </div>
        <div class="modal-footer"><button class="btn-secondary" onclick="closeModal()">Fermer</button></div>
      </div>
    </div>`;
  setTimeout(()=>drawBlackBoxHistoryMap(points), 0);
}

function drawBlackBoxHistoryMap(points) {
  const element = document.getElementById('argos-history-map');
  if (!element || typeof L === 'undefined') return;
  if (argosHistoryMap) { argosHistoryMap.remove(); argosHistoryMap = null; }
  argosHistoryMap = L.map(element, {zoomControl:true});
  L.tileLayer(MAP_LAYERS[mapLayerIdx].url, {attribution:'© ARGOS',maxZoom:19}).addTo(argosHistoryMap);
  const latLngs = points.map(point=>[Number(point.latitude),Number(point.longitude)]);
  for(let index=1; index<points.length; index++) {
    const critical = argosHistoryAlerts(points[index]).length || Number(points[index].shock)>5 || argosHistoryAlerts(points[index-1]).length || Number(points[index-1].shock)>5;
    L.polyline([latLngs[index-1],latLngs[index]], {color:critical?'#ff4444':'#00d4ff',weight:critical?6:4,opacity:.9}).addTo(argosHistoryMap);
  }
  points.forEach((point,index)=>{
    const alerts=argosHistoryAlerts(point); const critical=alerts.length||Number(point.shock)>5;
    if(!critical && !point.audio_url && index!==0 && index!==points.length-1) return;
    const marker=L.circleMarker(latLngs[index],{radius:critical?8:6,color:critical?'#ff4444':'#00d4ff',fillColor:critical?'#ff4444':'#00d4ff',fillOpacity:.9}).addTo(argosHistoryMap);
    marker.bindTooltip(`${argosHistoryPlace(point)} · ${new Date(point.measured_at).toLocaleTimeString('fr-FR')}`);
    marker.on('click',()=>openBlackBoxHistoryEvent(index));
  });
  if(latLngs.length) argosHistoryMap.fitBounds(L.latLngBounds(latLngs).pad(.08));
  else argosHistoryMap.setView([3.9,12.5],7);
  setTimeout(()=>argosHistoryMap?.invalidateSize(),100);
}

function openBlackBoxHistoryEvent(index) {
  const point=argosCurrentBoxHistory?.points?.[index];
  if(!point) return;
  const alerts=argosHistoryAlerts(point);
  const fields=[
    ['Température',point.temperature,'°C'],['Humidité',point.humidity,'%'],['Pression',point.pressure,' hPa'],
    ['Choc',point.shock,' G'],['Niveau sonore',point.sound_level,''],['Distance',point.distance_cm,' cm'],
    ['Batterie',point.battery_level,'%'],['Vitesse',point.speed,' km/h'],['Cap',point.heading,'°'],
    ['Accélération X',point.acceleration_x,' G'],['Accélération Y',point.acceleration_y,' G'],['Accélération Z',point.acceleration_z,' G']
  ];
  document.getElementById('modal-root').innerHTML=`<div class="modal-overlay"><div class="modal" style="max-width:760px;max-height:90vh;overflow:auto">
    <div class="modal-header"><div class="modal-title" style="color:${alerts.length?'var(--red)':'var(--cyan)'}"><i class="fas fa-map-marker-alt"></i> Événement — ${escapeHTML(argosHistoryPlace(point))}</div><button class="modal-close" onclick="renderBlackBoxConsultModal(argosCurrentBoxHistory)"><i class="fas fa-arrow-left"></i></button></div>
    <div class="modal-body"><div style="font-size:12px;color:var(--text3);margin-bottom:12px">${new Date(point.measured_at).toLocaleString('fr-FR')} · ${Number(point.latitude).toFixed(6)}, ${Number(point.longitude).toFixed(6)} · séquence ${point.sequence}</div>
    ${alerts.map(alert=>`<div class="alert alert-warn"><i class="fas fa-exclamation-triangle"></i> ${escapeHTML(alert)}</div>`).join('')}
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px;margin-top:12px">${fields.map(([label,value,unit])=>`<div style="padding:10px;background:var(--card2);border:1px solid var(--border);border-radius:var(--radius)"><div style="font-size:10px;color:var(--text3)">${label}</div><strong>${value??'—'}${value==null?'':unit}</strong></div>`).join('')}</div>
    <div style="margin-top:14px;padding:12px;background:var(--card2);border:1px solid var(--border);border-radius:var(--radius)"><div style="font-size:12px;color:var(--text3);margin-bottom:8px">SON ENREGISTRÉ LORS DE L'ÉVÉNEMENT</div>${point.recording_uid?`<audio id="argos-event-audio" controls style="width:100%"></audio><div id="argos-audio-status" style="font-size:11px;color:var(--text3);margin-top:5px">Chargement sécurisé…</div>`:'<div style="font-size:12px;color:var(--text3)">Aucun son associé. Activez « Enregistrer les sons » avant l’événement.</div>'}</div>
    </div><div class="modal-footer"><button class="btn-secondary" onclick="renderBlackBoxConsultModal(argosCurrentBoxHistory)"><i class="fas fa-arrow-left"></i> Retour à l’historique</button></div></div></div>`;
  if(point.recording_uid) loadBlackBoxEventAudio(point.recording_uid);
}

async function loadBlackBoxEventAudio(recordingUid) {
  const status=document.getElementById('argos-audio-status');
  try {
    const response=await secureApiFetch(`/api/audio/${encodeURIComponent(recordingUid)}`);
    if(!response.ok) throw new Error('Lecture audio refusée');
    if(argosAudioObjectUrl) URL.revokeObjectURL(argosAudioObjectUrl);
    argosAudioObjectUrl=URL.createObjectURL(await response.blob());
    const player=document.getElementById('argos-event-audio');
    if(player) player.src=argosAudioObjectUrl;
    if(status) status.textContent='Audio prêt à être lu.';
  } catch(error) { if(status) status.textContent=error.message; }
}

async function sendConfigurationToEsp(accessPointUrl, configuration, setupKey = 'ARGOS-PROVISION-2026') {
  const base = String(accessPointUrl || 'http://192.168.4.1').replace(/\/$/, '');
  const response = await fetch(`${base}/api/v1/provision`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-ARGOS-Setup-Key': setupKey,
      'X-ARGOS-Client-Timestamp': new Date().toISOString()
    },
    body: JSON.stringify(configuration)
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !['configured', 'success'].includes(result.status)) {
    throw new Error(result.error || `L’ESP32 a refusé la configuration (HTTP ${response.status})`);
  }
  return result;
}

function reconnectBlackBox(boxId) {
  const box = window.argosBlackBoxesById?.[String(boxId)] || {};
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-wifi"></i> Configurer le réseau de ${escapeHTML(box.numero_serie || `boîte #${boxId}`)}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <form onsubmit="submitReconnectBlackBox(event, ${boxId})">
          <div class="modal-body">
            <div style="padding:12px;border:1px solid #f0a500;border-radius:8px;margin-bottom:15px;font-size:12px">
              Maintenez BOOT sur l’ESP32 pendant 3 secondes, puis connectez cet ordinateur au Wi-Fi <strong>ARGOS-SETUP-…</strong>. La configuration sera envoyée directement par ce navigateur à l’ESP32.
            </div>
            <div class="form-group">
              <label>Mode de connexion</label>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <label style="padding:12px;border:1px solid var(--border);border-radius:8px;cursor:pointer">
                  <input type="radio" name="reconnect-mode" value="multiple" checked onchange="updateReconnectModeUI(${boxId})">
                  <strong> Connecter plusieurs boîtes</strong><br><small>L’ESP32 rejoint le Wi-Fi Internet et envoie lui-même les données.</small>
                </label>
                <label style="padding:12px;border:1px solid var(--cyan);border-radius:8px;cursor:pointer">
                  <input type="radio" name="reconnect-mode" value="direct" onchange="updateReconnectModeUI(${boxId})">
                  <strong> Recevoir directement cette boîte</strong><br><small>Restez sur ARGOS-SETUP : lecture et affichage immédiats dans ARGOS.</small>
                </label>
              </div>
            </div>
            <div id="reconnect-identity" style="padding:10px;border:1px solid var(--border);border-radius:8px;margin-bottom:12px;font-size:12px">
              Identité attendue : <strong>${escapeHTML(box.device_uid || '—')}</strong><br>
              <button type="button" class="btn-secondary" style="margin-top:8px" onclick="verifyReconnectDevice(${boxId})"><i class="fas fa-fingerprint"></i> Vérifier l’ESP32 connecté</button>
              <span id="reconnect-detected-uid"></span>
            </div>
            <div class="form-row">
              <div class="form-group"><label>Adresse locale de l’ESP32 *</label><input id="reconnect-ap-url" type="url" value="http://192.168.4.1" required></div>
              <div class="form-group"><label>Clé de configuration *</label><input id="reconnect-setup-key" type="password" value="ARGOS-PROVISION-2026" required></div>
            </div>
            <div id="reconnect-network-fields">
              <div class="form-row">
                <div class="form-group"><label>Wi-Fi utilisé après redémarrage *</label><input id="reconnect-wifi-ssid" required autocomplete="off"></div>
                <div class="form-group"><label>Mot de passe Wi-Fi</label><input id="reconnect-wifi-password" type="password" autocomplete="new-password"></div>
              </div>
              <div class="form-group"><label>Adresse ARGOS accessible depuis l’ESP32 *</label><input id="reconnect-api-url" type="url" placeholder="http://192.168.1.20:5002" required></div>
              <div class="form-group"><label>Distance maximale porte fermée (cm)</label><input id="reconnect-distance" type="number" min="5" max="400" step="0.1" value="15"></div>
            </div>
            <div id="reconnect-direct-fields" style="display:none">
              <div class="form-group"><label>Fréquence de lecture locale</label>
                <select id="reconnect-direct-poll"><option value="1000">Chaque seconde</option><option value="2000" selected>Toutes les 2 secondes</option><option value="5000">Toutes les 5 secondes</option></select>
              </div>
              <div style="padding:10px;border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:space-between;gap:12px">
                <div><strong>Mode sécurité des portes</strong><br><small>Réservé aux gestionnaires ; auteur et heure enregistrés.</small></div>
                <label class="toggle-switch"><input data-argos-security-box="${boxId}" type="checkbox" onchange="sendArgosDirectSecurity(this)"><span class="toggle-slider"></span></label>
              </div>
              ${typeof buildArgosDirectLivePanel === 'function' ? buildArgosDirectLivePanel(boxId) : ''}
            </div>
            <div id="reconnect-progress" style="font-size:12px;color:var(--text-secondary)"></div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" onclick="closeModal()">Annuler</button>
            <button id="reconnect-submit" type="submit" class="btn-primary"><i class="fas fa-paper-plane"></i> Envoyer la configuration</button>
          </div>
        </form>
      </div>
    </div>`;
  document.getElementById('modal-root').innerHTML = html;
  updateReconnectModeUI(boxId);
}

function updateReconnectModeUI(boxId) {
  const mode = document.querySelector('input[name="reconnect-mode"]:checked')?.value || 'multiple';
  const direct = mode === 'direct';
  const networkFields = document.getElementById('reconnect-network-fields');
  const directFields = document.getElementById('reconnect-direct-fields');
  if (networkFields) networkFields.style.display = direct ? 'none' : '';
  if (directFields) directFields.style.display = direct ? '' : 'none';
  ['reconnect-wifi-ssid', 'reconnect-api-url'].forEach(id => {
    const field = document.getElementById(id);
    if (field) field.disabled = direct;
  });
  const button = document.getElementById('reconnect-submit');
  if (button) button.innerHTML = direct
    ? '<i class="fas fa-play"></i> Identifier et recevoir maintenant'
    : '<i class="fas fa-paper-plane"></i> Envoyer la configuration';
  if (direct && window.argosDirectBridge?.lastTelemetry && String(window.argosDirectBridge.boxId) === String(boxId)) {
    argosDirectRenderTelemetry(window.argosDirectBridge.lastTelemetry);
  }
}

async function verifyReconnectDevice(boxId) {
  const accessPointUrl = document.getElementById('reconnect-ap-url').value.trim().replace(/\/$/, '');
  const output = document.getElementById('reconnect-detected-uid');
  try {
    output.textContent = ' Vérification…';
    const setupKey = document.getElementById('reconnect-setup-key')?.value || 'ARGOS-PROVISION-2026';
    const response = await fetch(`${accessPointUrl}/api/device/info`, {headers:{
      'Accept':'application/json',
      'X-ARGOS-Setup-Key': setupKey,
      'X-ARGOS-Client-Timestamp': new Date().toISOString()
    }});
    const info = await response.json();
    const uid = String(info.deviceUid || info.device_uid || '');
    if (!response.ok || !uid) throw new Error(info.error || 'Identité absente');
    const expected = window.argosBlackBoxesById?.[String(boxId)]?.device_uid || '';
    if (uid !== expected) throw new Error(`ID différent : ${uid}`);
    document.getElementById('reconnect-ap-url').dataset.detectedUid = uid;
    output.innerHTML = ` <span style="color:var(--green)">✓ ${escapeHTML(uid)}</span>`;
    return uid;
  } catch (error) {
    document.getElementById('reconnect-ap-url').dataset.detectedUid = '';
    output.innerHTML = ` <span style="color:var(--red)">✗ ${escapeHTML(error.message)}</span>`;
    return null;
  }
}

async function submitReconnectBlackBox(event, boxId) {
  event.preventDefault();
  const progress = document.getElementById('reconnect-progress');
  const accessPointUrl = document.getElementById('reconnect-ap-url').value.trim();
  const mode = document.querySelector('input[name="reconnect-mode"]:checked')?.value || 'multiple';
  if (mode === 'direct') {
    try {
      progress.textContent = 'Vérification puis passage de l’ESP32 en mode direct…';
      const box = window.argosBlackBoxesById?.[String(boxId)] || {};
      const setupKey = document.getElementById('reconnect-setup-key').value;
      const detectedUid = await verifyReconnectDevice(boxId);
      if (!detectedUid) throw new Error('Identité ESP32 non vérifiée');
      await sendConfigurationToEsp(accessPointUrl, {
        deviceUid: detectedUid,
        blackBoxId: Number(boxId),
        containerId: box.container_id || '',
        enrollmentToken: '',
        apiBaseUrl: '',
        wifi: {ssid: '', password: ''},
        thresholds: {distanceCm: 15}
      }, setupKey);
      progress.textContent = 'ESP32 redémarré en mode direct • attente du point d’accès…';
      await new Promise(resolve => setTimeout(resolve, 1800));
      let lastError = null;
      for (let attempt = 0; attempt < 8; attempt += 1) {
        try {
          await startArgosDirectBridge({
            boxId, expectedUid: box.device_uid, baseUrl: accessPointUrl, setupKey,
            pollMs: document.getElementById('reconnect-direct-poll')?.value
          });
          lastError = null;
          break;
        } catch (error) {
          lastError = error;
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      if (lastError) throw lastError;
      progress.textContent = 'Connexion directe active. Les mesures ci-dessus sont transmises à ARGOS.';
      showToast('Réception directe ESP32 active.', 'success');
    } catch (error) {
      progress.textContent = `Échec : ${error.message}`;
      showToast(error.message, 'error');
    }
    return;
  }
  const payload = {
    setup_key: document.getElementById('reconnect-setup-key').value,
    wifi_ssid: document.getElementById('reconnect-wifi-ssid').value.trim(),
    wifi_password: document.getElementById('reconnect-wifi-password').value,
    api_base_url: document.getElementById('reconnect-api-url').value.trim(),
    access_point_url: accessPointUrl,
    distance_cm: Number(document.getElementById('reconnect-distance').value || 15),
    connection_mode: mode,
    detected_device_uid: document.getElementById('reconnect-ap-url').dataset.detectedUid || ''
  };
  try {
    progress.textContent = '1/2 — Préparation d’un nouveau jeton sécurisé…';
    const response = await secureApiFetch(`/api/black-boxes/${boxId}/reprovision`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Reconnexion impossible');
    progress.textContent = '2/2 — Envoi direct vers l’ESP32 à 192.168.4.1…';
    await sendConfigurationToEsp(accessPointUrl, result.device_configuration, payload.setup_key);
    const share = result.share_url ? ` Lien distant : ${result.share_url}` : '';
    showToast(`ESP32 configuré : ${result.device_uid}. Redémarrage en cours.${share}`, 'success');
    closeModal();
    setTimeout(() => renderPage('my-boxes'), 8000);
  } catch (error) {
    progress.textContent = `Échec : ${error.message}`;
    showToast(error.message, 'error');
  }
}

// MODAL: Créer une nouvelle boîte noire
async function openCreateBlackBoxModal(context = null) {
  context = context || JSON.parse(sessionStorage.getItem('argosSetupIntent') || 'null') || {};
  const setupIntent = JSON.parse(sessionStorage.getItem('argosSetupIntent') || 'null');
  const deviceUid = context.device_uid || context.deviceUid || setupIntent?.deviceUid || '';
  if (deviceUid) {
    try {
      const response = await secureApiFetch(`/api/iot/devices/${encodeURIComponent(deviceUid)}/status`);
      if (response.ok) {
        const registered = await response.json();
        if (registered.blackBoxId) {
          sessionStorage.setItem('argosSetupIntent', JSON.stringify({...(setupIntent || {}), deviceUid, registered: true, blackBoxId: registered.blackBoxId}));
          navigateTo('my-boxes');
          showToast(`Création bloquée : l’ESP32 ${deviceUid} appartient déjà à la boîte #${registered.blackBoxId}. Cliquez sur « Configurer le réseau ESP32 ».`, 'warn');
          return;
        }
      }
    } catch (error) {
      showToast(`Vérification de l’ESP32 impossible : ${error.message}`, 'error');
      return;
    }
  }
  const containerValue = context?.container_id || '';
  const selectedOwner = context?.proprietaire_id || (currentRole === 'owner' ? currentUserId : '');
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-cube"></i> Créer une Nouvelle Boîte Noire</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <form id="form-create-bn" onsubmit="handleCreateBlackBox(event)">
            <div style="margin-bottom:20px;padding:14px;border:1px solid #5b8def;border-radius:8px;background:rgba(91,141,239,.08)">
              <div style="font-weight:bold;margin-bottom:8px"><i class="fas fa-wifi"></i> Première configuration de l’ESP32</div>
              <div style="font-size:12px;line-height:1.5;margin-bottom:12px">Avant de cliquer sur « Créer », connectez cet ordinateur au point d’accès <strong>ARGOS-SETUP-…</strong> de la boîte. L’identifiant et cette configuration seront enregistrés dans sa mémoire.</div>
              <div class="form-row">
                <div class="form-group"><label>Adresse du boîtier *</label><input type="url" id="bn-access-point-url" value="http://192.168.4.1" required></div>
                <div class="form-group"><label>Clé de configuration *</label><input type="password" id="bn-setup-key" value="ARGOS-PROVISION-2026" required></div>
              </div>
              <div class="form-group"><label>Mode de communication *</label>
                <select id="bn-connection-mode" onchange="updateCreateBlackBoxConnectionMode()">
                  <option value="direct" selected>Wi-Fi direct ESP32 — ordinateur connecté à ARGOS-SETUP</option>
                  <option value="network">Wi-Fi réseau — ESP32 envoie lui-même vers ARGOS</option>
                </select>
                <small id="bn-connection-help">L’ordinateur lit directement les capteurs à 192.168.4.1 et les enregistre dans ARGOS.</small>
              </div>
              <div id="bn-network-configuration" style="display:none"><div class="form-row">
                <div class="form-group"><label>Wi-Fi utilisé ensuite par la boîte *</label><input type="text" id="bn-wifi-ssid" required autocomplete="off"></div>
                <div class="form-group"><label>Mot de passe Wi-Fi</label><input type="password" id="bn-wifi-password" autocomplete="new-password"></div>
              </div>
              <div class="form-group"><label>Adresse ARGOS accessible depuis l’ESP32</label><input type="url" id="bn-api-base-url" placeholder="Ex. http://192.168.1.20:5002"></div>
              </div>
            </div>
            <div style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border);">
              <div style="font-weight: bold; margin-bottom: 10px;"><i class="fas fa-box"></i> Conteneur</div>
              <div class="form-group">
                <label>Conteneur disponible</label>
                <select id="bn-container-id" onchange="validateISO6346(this)" disabled>
                  <option value="">Aucune (créer sans conteneur)</option>
                </select>
                <small id="iso-feedback" style="display: block; margin-top: 5px; color: var(--text-secondary);">Optionnel : sélectionnez une entreprise uniquement pour filtrer ses conteneurs disponibles.</small>
              </div>
              <div class="form-group">
                <label>Propriétaire/Entreprise (optionnel)</label>
                <select id="bn-proprietaire"></select>
              </div>
            </div>
            
            <div style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border);">
              <div style="font-weight: bold; margin-bottom: 10px;"><i class="fas fa-cog"></i> Configuration</div>
              <div class="form-row">
                <div class="form-group">
                  <label>Type *</label>
                  <select id="bn-type-boite" required><option value="daily">Quotidienne</option><option value="weekly">Hebdomadaire</option><option value="monthly" selected>Mensuelle</option><option value="continuous">Continue</option></select>
                </div>
                <div class="form-group">
                  <label>Version</label>
                  <input type="text" id="bn-version" value="v2.1">
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>Batterie (%)</label>
                  <input type="number" id="bn-battery" value="100" min="0" max="100">
                </div>
                <div class="form-group">
                  <label>Durée/jour</label>
                  <input type="number" id="bn-duration" value="30">
                </div>
              </div>
              <div class="form-group">
                <label>Date Déploiement *</label>
                <input type="date" id="bn-deployment-date" required>
              </div>
            </div>
            
            <div style="margin-bottom: 20px;">
              <div style="font-weight: bold; margin-bottom: 10px;"><i class="fas fa-exclamation-triangle"></i> Seuils</div>
              <div class="form-row">
                <div class="form-group"><label>T° Max (°C)</label><input type="number" id="bn-temp-max" value="32" step="0.1"></div>
                <div class="form-group"><label>T° Min (°C)</label><input type="number" id="bn-temp-min" value="-10" step="0.1"></div>
              </div>
              <div class="form-row">
                <div class="form-group"><label>Humidité Max (%)</label><input type="number" id="bn-humi-max" value="75" min="0" max="100"></div>
                <div class="form-group"><label>Choc Max (G)</label><input type="number" id="bn-choc-max" value="5" step="0.1"></div>
              </div>
              <div class="form-row">
                <div class="form-group"><label>Pression Min (hPa)</label><input type="number" id="bn-pression-min" value="995" step="0.1"></div>
                <div class="form-group"><label>Vitesse Max (km/h)</label><input type="number" id="bn-vitesse-max" value="90"></div>
              </div>
              <div class="form-group"><label>Angle Max (°)</label><input type="number" id="bn-angle-max" value="30"></div>
              <div class="form-group"><label>Ouverture détectée au-delà de (cm)</label><input type="number" id="bn-distance-cm" value="15" min="5" max="400" step="0.5"><small>Déclenche l’alerte et l’écoute automatique lorsque le mode sécurité est actif.</small></div>
            </div>
            
            <div class="modal-footer">
              <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Créer</button>
              <button type="button" class="btn btn-secondary" onclick="closeModal()"><i class="fas fa-times"></i> Annuler</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
  document.getElementById('modal-root').innerHTML = html;
  document.getElementById('bn-deployment-date').value = new Date().toISOString().split('T')[0];
  if (context.access_point_url) document.getElementById('bn-access-point-url').value = context.access_point_url;
  updateCreateBlackBoxConnectionMode();
  const containerSelect = document.getElementById('bn-container-id');
  const ownerSelect = document.getElementById('bn-proprietaire');
  if (containerValue) {
    validateISO6346(containerSelect);
  }
  ownerSelect.addEventListener('change', function () {
    loadContainersForBlackBox(this.value);
  });
  loadProprietairesForBlackBox(selectedOwner, containerValue);
}

function updateCreateBlackBoxConnectionMode() {
  const direct = document.getElementById('bn-connection-mode')?.value === 'direct';
  const network = document.getElementById('bn-network-configuration');
  const ssid = document.getElementById('bn-wifi-ssid');
  const help = document.getElementById('bn-connection-help');
  if (network) network.style.display = direct ? 'none' : '';
  if (ssid) ssid.required = !direct;
  if (help) help.textContent = direct
    ? 'Gardez cet ordinateur connecté à ARGOS-SETUP : il relaie les mesures vers l’application locale.'
    : 'L’ESP32 rejoint le réseau choisi et transmet lui-même les mesures à l’adresse ARGOS.';
}

async function openEditBlackBoxModal(box) {
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-edit"></i> Éditer Boîte Noire</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <form id="form-edit-bn" onsubmit="handleEditBlackBox(event, ${box.id_boite})">
            <div style="background:var(--bg3);padding:12px;border-radius:8px;margin-bottom:15px;font-size:12px">
              <strong>UUID QR:</strong> ${escapeHTML(box.numero_serie)}
            </div>
            <div class="form-row">
              <div class="form-group"><label>Type</label><select id="edit-type-boite"><option value="daily">Quotidienne</option><option value="weekly">Hebdomadaire</option><option value="monthly">Mensuelle</option><option value="continuous">Continue</option></select></div>
              <div class="form-group"><label>Version</label><input type="text" id="edit-version" value="${escapeHTML(box.version || 'v2.1')}"></div>
            </div>
            <div class="form-row">
              <div class="form-group"><label>Batterie (%)</label><input type="number" id="edit-battery" value="${Number(box.battery ?? 100)}" min="0" max="100"></div>
              <div class="form-group"><label>Durée (jours)</label><input type="number" id="edit-duration" value="${parseInt(box.expected_duration, 10) || 30}" min="1"></div>
            </div>
            <div class="form-group">
              <label>Date de déploiement</label>
              <input type="date" id="edit-deployment-date" value="${box.deployment_date ? String(box.deployment_date).slice(0, 10) : new Date().toISOString().slice(0, 10)}" required>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" onclick="closeModal()">Annuler</button>
              <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
  document.getElementById('modal-root').innerHTML = html;
  document.getElementById('edit-type-boite').value = box.type || 'monthly';
}

async function handleEditBlackBox(event, boxId) {
  event.preventDefault();
  try {
    const res = await secureApiFetch(`/api/black-boxes/${boxId}/configure`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        type_boite: document.getElementById('edit-type-boite').value,
        versions: document.getElementById('edit-version').value || 'v2.1',
        battery_level: Number(document.getElementById('edit-battery').value || 100),
        expected_duration: Number(document.getElementById('edit-duration').value || 30),
        deployment_date: document.getElementById('edit-deployment-date').value
      })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.error || 'Modification impossible');
    showToast('Configuration enregistrée', 'success');
    closeModal();
    renderPage('my-boxes');
  } catch (e) { showToast(e.message, 'error'); }
}

function validateISO6346(input) {
  const value = input.value.trim().toUpperCase();
  const feedback = document.getElementById('iso-feedback');
  if (!feedback) return true;
  const iso6346Regex = /^[A-Z]{4}\d{6}\d$/;
  if (!value) {
    feedback.textContent = 'Laissez vide si la boîte doit être créée sans conteneur initial.';
    feedback.style.color = 'var(--text-secondary)';
    return true;
  }
  if (!iso6346Regex.test(value)) {
    feedback.innerHTML = '<i class="fas fa-times-circle"></i> Format invalide!';
    feedback.style.color = 'red';
    return false;
  }
  feedback.innerHTML = '<i class="fas fa-check-circle"></i> Format valide';
  feedback.style.color = 'green';
  return true;
}

async function loadProprietairesForBlackBox(selectedValue = '', selectedContainer = '') {
  try {
    const res = await secureApiFetch('/api/companies');
    const companies = await res.json();
    const select = document.getElementById('bn-proprietaire');
    if (!select) {
      console.error('Élément bn-proprietaire non trouvé');
      return;
    }
    if (!Array.isArray(companies)) return;
    select.innerHTML = '<option value="">Sans entreprise</option>';
    companies.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.nom_agence || `Propriétaire #${c.id}`;
      select.appendChild(opt);
    });
    if (selectedValue) {
      select.value = String(selectedValue);
    }
    await loadContainersForBlackBox(select.value, selectedContainer);
  } catch(e) {
    console.error('Erreur propriétaires:', e);
  }
}

async function loadContainersForBlackBox(companyId = '', selectedContainer = '') {
  const select = document.getElementById('bn-container-id');
  if (!select) return;

  select.innerHTML = '<option value="">Aucune (créer sans conteneur)</option>';
  select.disabled = true;

  if (!companyId) {
    select.disabled = false;
    return;
  }

  try {
    const res = await secureApiFetch(`/api/containers/disponibles?company_id=${encodeURIComponent(companyId)}`);
    const containers = await res.json();
    if (!Array.isArray(containers)) return;

    containers.forEach(container => {
      const option = document.createElement('option');
      option.value = container.id;
      option.textContent = `${container.id} (${container.type_conteneurs || '—'})`;
      select.appendChild(option);
    });

    select.disabled = false;
    if (selectedContainer) {
      select.value = String(selectedContainer);
    }
  } catch (e) {
    console.error('Erreur chargement conteneurs:', e);
  }
}

async function handleCreateBlackBox(event) {
  event.preventDefault();
  const containerValue = document.getElementById('bn-container-id').value.trim().toUpperCase();
  if (containerValue && !validateISO6346(document.getElementById('bn-container-id'))) {
    showToast('<i class="fas fa-times-circle"></i> ISO 6346 invalide', 'error');
    return;
  }
  
  const ownerValue = document.getElementById('bn-proprietaire').value;
  const connectionMode = document.getElementById('bn-connection-mode')?.value || 'direct';
  const data = {
    container_id: containerValue || null,
    proprietaire_id: ownerValue ? parseInt(ownerValue) : null,
    type_boite: document.getElementById('bn-type-boite').value,
    version: document.getElementById('bn-version').value,
    battery_capacity: parseInt(document.getElementById('bn-battery').value),
    expected_duration: document.getElementById('bn-duration').value,
    deployment_date: document.getElementById('bn-deployment-date').value,
    temp_max: parseFloat(document.getElementById('bn-temp-max').value),
    temp_min: parseFloat(document.getElementById('bn-temp-min').value),
    humi_max: parseFloat(document.getElementById('bn-humi-max').value),
    choc_max: parseFloat(document.getElementById('bn-choc-max').value),
    pression_min: parseFloat(document.getElementById('bn-pression-min').value),
    vitesse_max: parseFloat(document.getElementById('bn-vitesse-max').value),
    angle_max: parseFloat(document.getElementById('bn-angle-max').value),
    distance_cm: parseFloat(document.getElementById('bn-distance-cm').value || '15'),
    device_uid: (JSON.parse(sessionStorage.getItem('argosSetupIntent') || 'null') || {}).deviceUid || null,
    access_point_url: document.getElementById('bn-access-point-url').value.trim(),
    setup_key: document.getElementById('bn-setup-key').value,
    wifi_ssid: document.getElementById('bn-wifi-ssid').value.trim(),
    wifi_password: document.getElementById('bn-wifi-password').value,
    api_base_url: document.getElementById('bn-api-base-url').value.trim(),
    connection_mode: connectionMode,
  };
  
  try {
    const res = await secureApiFetch('/api/black-boxes/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json();
    if (!res.ok) {
      showToast('<i class="fas fa-times-circle"></i> ' + (result.error || 'Création échouée'), 'error');
      return;
    }
    await sendConfigurationToEsp(data.access_point_url, result.device_configuration, data.setup_key);
    if (connectionMode === 'direct') {
      await new Promise(resolve => setTimeout(resolve, 1800));
      let lastError = null;
      for (let attempt = 0; attempt < 8; attempt += 1) {
        try {
          await startArgosDirectBridge({
            boxId: result.id_boite,
            expectedUid: result.device_uid,
            baseUrl: data.access_point_url,
            setupKey: data.setup_key,
            pollMs: 2000
          });
          lastError = null;
          break;
        } catch (error) {
          lastError = error;
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      if (lastError) throw new Error(`Boîte créée, mais réception directe non démarrée : ${lastError.message}`);
    }
    showToast(connectionMode === 'direct'
      ? 'Boîte créée : réception Wi-Fi directe active.'
      : 'Boîte créée et ESP32 configuré. ID #' + result.id_boite, 'success');
    sessionStorage.removeItem('argosSetupIntent');
    closeModal();
    setTimeout(() => renderPage('my-boxes'), 500);
  } catch(e) {
    console.error('Erreur:', e);
    showToast('<i class="fas fa-times-circle"></i> Erreur: ' + e.message, 'error');
  }
}

async function downloadBoxQRCode(boxId, serial) {
  try {
    const res = await secureApiFetch(`/api/black-boxes/${boxId}/qrcode`);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qrcode_${serial}.png`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    showToast('<i class="fas fa-check-circle"></i> QR Code téléchargé', 'success');
  } catch(e) {
    showToast('<i class="fas fa-times-circle"></i> Erreur', 'error');
  }
}

async function viewBoxQRModal(boxId) {
  try {
    const res = await secureApiFetch(`/api/black-boxes/${boxId}/qrcode`);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    
    document.getElementById('modal-root').innerHTML = `
      <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
        <div class="modal" style="max-width:500px">
          <div class="modal-header">
            <div class="modal-title"><i class="fas fa-qrcode"></i> QR Code Boîte Noire</div>
            <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
          </div>
          <div class="modal-body" style="text-align:center;padding:30px">
            <img src="${url}" alt="QR Code" style="max-width:300px;border-radius:8px;border:2px solid var(--border);">
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" onclick="closeModal()">Fermer</button>
            <button class="btn-primary" onclick="downloadBoxQRCode(${boxId}, 'qrcode')">
              <i class="fas fa-download"></i> Télécharger
            </button>
          </div>
        </div>
      </div>`;
  } catch(e) {
    showToast('<i class="fas fa-times-circle"></i> Erreur: ' + e.message, 'error');
  }
}

function showAssignBoxModal(data) {
  const box = data.box || {};
  const companyField = data.is_owner ? '' : `
    <div class="form-group">
      <label>Entreprise *</label>
      <select id="assign-company" required>
        <option value="">-- Sélectionner --</option>
        ${data.companies?.map(c => `<option value="${escapeHTML(c.id)}">${escapeHTML(c.nom_agence)}</option>`).join('') || ''}
      </select>
    </div>`;
  const containerOptions = (data.containers || []).map(c =>
    `<option value="${escapeHTML(c.id)}">${escapeHTML(c.id)} (${escapeHTML(c.type_conteneurs || '—')})</option>`
  ).join('');

  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:480px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-link"></i> Assigner la boîte ${escapeHTML(box.numero_serie || '')}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          ${companyField}
          <div class="form-group">
            <label>Conteneur libre *</label>
            <select id="assign-container" required>
              <option value="">-- Sélectionner --</option>
              ${containerOptions || '<option value="">Aucun conteneur disponible</option>'}
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-primary" onclick="confirmAssignBox(${box.id_boite})"><i class="fas fa-check"></i> Valider</button>
        </div>
      </div>
    </div>`;
}

async function confirmAssignBox(boxId) {
  const container = document.getElementById('assign-container').value;
  const companyEl = document.getElementById('assign-company');
  if (!container) return showToast('Conteneur requis', 'warn');
  if (companyEl && !companyEl.value) return showToast('Entreprise requise', 'warn');

  const res = await secureApiFetch(`/api/black-boxes/${boxId}/assign`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id_conteneurs: container,
      id_proprietaire: companyEl ? parseInt(companyEl.value) : undefined
    })
  });
  const d = await res.json();
  if (!res.ok) return showToast(d.error || 'Erreur assignation', 'error');
  showToast('Boîte assignée avec succès', 'success');
  closeModal();
  renderPage('my-boxes');
}

function showBlackBoxQrDecisionModal(data) {
  const box = data.box || {};
  const isArchived = data.action === 'archived';
  const title = isArchived ? 'Boîte archivée' : 'Boîte noire détectée';
  const subtitle = isArchived
    ? 'Cette boîte a déjà été mise hors service.'
    : 'La boîte a été retrouvée et peut être consultée.';

  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:480px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-cube"></i> ${title}</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <p style="color:var(--text2);margin-bottom:12px">${subtitle}</p>
          <div style="background:var(--bg3);padding:12px;border-radius:8px;font-size:13px;line-height:1.5">
            <div><strong>Numéro:</strong> ${escapeHTML(box.numero_serie || '—')}</div>
            <div><strong>Conteneur:</strong> ${escapeHTML(box.container_id || '—')}</div>
            <div><strong>Statut:</strong> ${escapeHTML(box.status || '—')}</div>
            <div><strong>Propriétaire:</strong> ${escapeHTML(box.proprietaire || '—')}</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Fermer</button>
          ${box.id_boite ? `<button class="btn-primary" onclick="viewBoxQRModal(${box.id_boite})"><i class="fas fa-qrcode"></i> Voir QR</button>` : ''}
          ${isArchived && box.id_boite ? `<button class="btn-danger" onclick="restoreBlackBox(${box.id_boite})"><i class="fas fa-undo"></i> Restaurer</button>` : ''}
          ${!isArchived && box.id_boite ? `<button class="btn-danger" onclick="archiveBlackBox(${box.id_boite})"><i class="fas fa-trash"></i> Supprimer</button>` : ''}
        </div>
      </div>
    </div>`;
}

async function archiveBlackBox(boxId) {
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal" style="max-width:450px">
        <div class="modal-header">
          <div class="modal-title"><i class="fas fa-exclamation-triangle" style="color:var(--red)"></i> Supprimer Boîte Noire</div>
          <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <p style="color:var(--text2);margin-bottom:15px">
            Êtes-vous sûr de vouloir supprimer cette boîte noire ?
          </p>
          <div style="background:var(--bg3);padding:15px;border-radius:8px;margin-bottom:15px;font-size:12px;color:var(--text-secondary)">
            <i class="fas fa-info-circle"></i> Le conteneur lié sera libéré et l'action sera enregistrée dans la blockchain.
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeModal()">Annuler</button>
          <button class="btn-danger" onclick="confirmArchiveBlackBox(${boxId})">
            <i class="fas fa-trash"></i> Supprimer
          </button>
        </div>
      </div>
    </div>`;
}

async function confirmArchiveBlackBox(boxId) {
  try {
    const res = await secureApiFetch(`/api/black-boxes/${boxId}`, { method: 'DELETE' });
    const result = await res.json();
    
    if (!res.ok) {
      showToast('<i class="fas fa-times-circle"></i> ' + (result.error || 'Erreur'), 'error');
      return;
    }
    
    showToast('<i class="fas fa-check-circle"></i> ' + (result.message || 'Boîte supprimée'), 'success');
    closeModal();
    setTimeout(() => {
      if (currentPage === 'archive') {
        renderPage('archive');
      } else {
        renderPage('my-boxes');
      }
    }, 500);
  } catch(e) {
    showToast('<i class="fas fa-times-circle"></i> Erreur: ' + e.message, 'error');
  }
}

async function openWiFiSettingsModalNew() {
  try {
    const res = await secureApiFetch('/api/wifi/settings');
    const data = await res.json();
    
    document.getElementById('modal-root').innerHTML = `
      <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
        <div class="modal" style="max-width:450px">
          <div class="modal-header">
            <div class="modal-title"><i class="fas fa-wifi"></i> Paramètres WiFi</div>
            <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
          </div>
          <div class="modal-body">
            <form id="form-wifi-new" onsubmit="handleWiFiUpdateNew(event)">
              <div class="form-group">
                <label>SSID (Nom du WiFi) *</label>
                <input type="text" id="wifi-ssid" placeholder="Ex: MonReseau" value="${data.ssid || ''}" required style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg3);color:var(--text1)">
                <small style="display:block;margin-top:5px;color:var(--text-secondary);font-size:11px">Nom du réseau WiFi</small>
              </div>
              <div class="form-group" style="margin-top:12px">
                <label>Mot de passe WiFi *</label>
                <input type="password" id="wifi-password-new" placeholder="Mot de passe" value="${data.password || ''}" required style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg3);color:var(--text1)">
                <small style="display:block;margin-top:5px;color:var(--text-secondary);font-size:11px">Chiffré en BD</small>
              </div>
              <div style="background:var(--bg3);padding:12px;border-radius:8px;margin-top:15px;font-size:12px;color:var(--text-secondary)">
                <i class="fas fa-info-circle"></i> Vos modules IoT utiliseront ces paramètres pour se connecter automatiquement.
              </div>
              <div class="modal-footer" style="margin-top:20px;display:flex;gap:8px">
                <button type="button" class="btn btn-secondary" onclick="closeModal()"><i class="fas fa-times"></i> Annuler</button>
                <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
              </div>
            </form>
          </div>
        </div>
      </div>`;
  } catch(e) {
    showToast('<i class="fas fa-times-circle"></i> Erreur', 'error');
  }
}

async function handleWiFiUpdateNew(event) {
  event.preventDefault();
  const data = {
    ssid: document.getElementById('wifi-ssid').value.trim(),
    password: document.getElementById('wifi-password-new').value
  };
  if (!data.ssid || !data.password) {
    showToast('<i class="fas fa-times-circle"></i> Tous les champs requis', 'error');
    return;
  }
  try {
    const res = await secureApiFetch('/api/wifi/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json();
    if (!res.ok) {
      showToast('<i class="fas fa-times-circle"></i> ' + (result.error || 'Erreur'), 'error');
      return;
    }
    showToast('<i class="fas fa-check-circle"></i> WiFi enregistré', 'success');
    closeModal();
  } catch(e) {
    console.error('Erreur:', e);
    showToast('<i class="fas fa-times-circle"></i> Erreur: ' + e.message, 'error');
  }
}

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
