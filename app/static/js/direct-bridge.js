// ARGOS — pont navigateur <-> point d'acces ESP32.
// Le navigateur affiche les mesures locales immédiatement, puis les transmet à
// l'API authentifiée. Si le changement de Wi-Fi coupe momentanément l'accès à
// ARGOS, les snapshots restent dans une file locale bornée et sont resynchronisés.

const ARGOS_DIRECT_ALLOWED_ROLES = new Set(['superadmin', 'owner', 'company']);
const ARGOS_DIRECT_QUEUE_KEY = 'argos_direct_bridge_queue_v1';
const ARGOS_DIRECT_SESSION_KEY = 'argos_direct_bridge_session_v1';
const ARGOS_DIRECT_QUEUE_LIMIT = 300;

window.argosDirectBridge = window.argosDirectBridge || {
  running: false,
  polling: false,
  flushing: false,
  timer: null,
  boxId: null,
  expectedUid: '',
  baseUrl: 'http://192.168.4.1',
  setupKey: 'ARGOS-PROVISION-2026',
  pollMs: 2000,
  lastFingerprint: '',
  lastTelemetry: null,
  lastServerLiveAt: 0,
  samples: [],
  positionStatus: 'Position GPS ESP32',
  deviceSecurityEnabled: null,
  audioRecorder: null,
  audioStream: null,
  audioChunks: [],
  audioStartedAt: null,
  audioStopTimer: null,
  status: 'Arrêté'
};

function argosDirectRoleAllowed() {
  const authenticated = localStorage.getItem('isLoggedIn') === 'true' &&
    Boolean(sessionStorage.getItem('argosAccessToken') || localStorage.getItem('argosAccessToken'));
  return authenticated && ARGOS_DIRECT_ALLOWED_ROLES.has(String(currentRole || '').toLowerCase());
}

function argosDirectNumber(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function argosDirectUuid() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  if (window.crypto?.getRandomValues) window.crypto.getRandomValues(bytes);
  else for (let i = 0; i < bytes.length; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function argosDirectReadQueue() {
  try {
    const value = JSON.parse(localStorage.getItem(ARGOS_DIRECT_QUEUE_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch (_) {
    return [];
  }
}

function argosDirectWriteQueue(queue) {
  try {
    localStorage.setItem(ARGOS_DIRECT_QUEUE_KEY, JSON.stringify(queue.slice(-ARGOS_DIRECT_QUEUE_LIMIT)));
  } catch (error) {
    console.warn('File directe ARGOS indisponible', error);
  }
  argosDirectUpdateStatusUi();
}

function argosDirectEnqueue(item) {
  const queue = argosDirectReadQueue();
  const messageId = item.body?.messageId;
  if (messageId && queue.some(entry => entry.body?.messageId === messageId)) return;
  queue.push({
    ...item,
    queueId: argosDirectUuid(),
    actorUserId: String(currentUserId || ''),
    queuedAt: new Date().toISOString()
  });
  argosDirectWriteQueue(queue);
}

function argosDirectSetStatus(message, tone = 'info') {
  const bridge = window.argosDirectBridge;
  bridge.status = message;
  bridge.statusTone = tone;
  argosDirectUpdateStatusUi();
}

function argosDirectForBox(boxId, selector, callback) {
  document.querySelectorAll('[data-argos-direct-box]').forEach(root => {
    if (String(root.dataset.argosDirectBox) !== String(boxId)) return;
    root.querySelectorAll(selector).forEach(callback);
  });
}

function argosDirectMetrics(payload, validOnly = false) {
  const sensors = payload?.sensors || {};
  const position = payload?.position || {};
  const modes = payload?.modes || {};
  const quality = payload?.quality || {};
  const dhtValid = quality.dhtValid !== false;
  const mpuValid = quality.mpuValid !== false;
  const distanceValid = quality.distanceValid !== false;
  const pressureValid = quality.pressureMeasured !== false;
  const batteryValid = quality.batteryMeasured !== false;
  const hasPosition = !(Number(position.latitude) === 0 && Number(position.longitude) === 0);
  return {
    temperature: dhtValid ? sensors.temperature : null,
    humidity: dhtValid ? sensors.humidity : null,
    pressure: !validOnly || pressureValid ? sensors.pressure : null,
    shock: mpuValid ? sensors.shock : null,
    distance: distanceValid ? sensors.distanceCm : null,
    battery: !validOnly || batteryValid ? sensors.batteryLevel : null,
    acceleration: (mpuValid
      ? [sensors.accelerationX, sensors.accelerationY, sensors.accelerationZ]
      : [null, null, null])
      .map(value => value ?? '—').join(' / '),
    position: hasPosition ? `${position.latitude ?? '—'}, ${position.longitude ?? '—'}` : '—',
    sequence: payload?.sequence,
    security: Boolean(modes.securityEnabled),
    timestamp: payload?.timestamp
  };
}

function argosDirectFormatMetric(name, value) {
  if (value === null || value === undefined || value === '') return '—';
  const units = {temperature: ' °C', humidity: ' %', pressure: ' hPa', shock: ' G', distance: ' cm', battery: ' %'};
  if (typeof value === 'number') value = Math.round(value * 100) / 100;
  if (name === 'timestamp') {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('fr-FR');
  }
  return `${value}${units[name] || ''}`;
}

function argosDirectUpdateStatusUi() {
  const bridge = window.argosDirectBridge;
  const pending = argosDirectReadQueue().length;
  const colors = {success: 'var(--green)', error: 'var(--red)', warn: 'var(--amber)', info: 'var(--cyan)'};
  argosDirectForBox(bridge.boxId, '[data-argos-direct-status]', element => {
    element.textContent = `${bridge.status}${pending ? ` • ${pending} mesure(s) en attente` : ''}`;
    element.style.color = colors[bridge.statusTone] || colors.info;
  });
  argosDirectForBox(bridge.boxId, '[data-argos-direct-position-status]', element => {
    element.textContent = bridge.positionStatus;
  });
  document.querySelectorAll('[data-argos-direct-stop]').forEach(button => {
    const root = button.closest('[data-argos-direct-box]');
    button.disabled = !bridge.running || String(root?.dataset.argosDirectBox) !== String(bridge.boxId);
  });
  document.querySelectorAll('[data-argos-direct-running]').forEach(element => {
    element.textContent = bridge.running ? `ACTIVE — boîte ${bridge.boxId}` : 'ARRÊTÉ';
    element.style.color = bridge.running ? 'var(--green)' : 'var(--text3)';
  });
  if (typeof bridge.deviceSecurityEnabled === 'boolean') {
    document.querySelectorAll('[data-argos-security-box]').forEach(input => {
      if (String(input.dataset.argosSecurityBox) === String(bridge.boxId) && document.activeElement !== input) {
        input.checked = bridge.deviceSecurityEnabled;
      }
    });
  }
}

function argosDirectRenderTelemetry(payload) {
  const bridge = window.argosDirectBridge;
  const metrics = argosDirectMetrics(payload);
  argosDirectForBox(bridge.boxId, '[data-argos-direct-metric]', element => {
    const name = element.dataset.argosDirectMetric;
    element.textContent = argosDirectFormatMetric(name, metrics[name]);
  });
  const quality = payload.quality || {};
  const qualityItems = [
    ['DHT22', quality.dhtValid], ['MPU6050', quality.mpuValid],
    ['GPS', quality.gpsValid], ['HC-SR04', quality.distanceValid], ['SD', quality.sdReady]
  ].map(([label, valid]) => `${label}:${valid === false ? 'ERREUR' : 'OK'}`);
  if (quality.pressureMeasured === false) qualityItems.push('Pression:estimée');
  if (quality.batteryMeasured === false) qualityItems.push('Batterie:estimée');
  argosDirectForBox(bridge.boxId, '[data-argos-direct-quality]', element => {
    element.textContent = qualityItems.join(' • ');
  });
  document.querySelectorAll(`[data-argos-security-box="${String(bridge.boxId).replace(/"/g, '')}"]`).forEach(input => {
    if (document.activeElement !== input) input.checked = metrics.security;
  });
  argosDirectUpdateSessionStats(payload);
  argosDirectMergeIntoApplication(payload);
  argosDirectUpdateStatusUi();
}

function argosDirectUpdateSessionStats(payload) {
  const bridge = window.argosDirectBridge;
  // Les valeurs de remplacement restent visibles dans le panneau live, mais
  // ne participent jamais aux moyennes de la session.
  const metrics = argosDirectMetrics(payload, true);
  const fingerprint = `${payload.messageId || ''}:${payload.sequence}`;
  if (bridge.samples.some(sample => sample.fingerprint === fingerprint)) return;
  bridge.samples.push({
    fingerprint,
    timestamp: payload.timestamp,
    temperature: argosDirectNumber(metrics.temperature),
    humidity: argosDirectNumber(metrics.humidity),
    pressure: argosDirectNumber(metrics.pressure),
    shock: argosDirectNumber(metrics.shock)
  });
  if (bridge.samples.length > 120) bridge.samples.shift();

  const average = key => {
    const values = bridge.samples.map(sample => sample[key]).filter(Number.isFinite);
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  };
  const values = {
    count: bridge.samples.length,
    avgTemperature: average('temperature'),
    avgHumidity: average('humidity'),
    maxShock: Math.max(...bridge.samples.map(sample => sample.shock).filter(Number.isFinite), 0),
    latest: payload.timestamp
  };
  document.querySelectorAll('[data-argos-direct-stat]').forEach(element => {
    const key = element.dataset.argosDirectStat;
    const unit = key === 'avgTemperature' ? ' °C' : key === 'avgHumidity' ? ' %' : key === 'maxShock' ? ' G' : '';
    const value = values[key];
    element.textContent = key === 'latest'
      ? argosDirectFormatMetric('timestamp', value)
      : (value === null || value === undefined ? '—' : `${Math.round(value * 100) / 100}${unit}`);
  });
  const directCard = document.getElementById('argos-direct-stats-card');
  if (directCard) directCard.style.display = bridge.running ? '' : 'none';
  argosDirectAppendCharts(payload);
}

function argosDirectAppendCharts(payload) {
  if (currentPage !== 'stats') return;
  const selectedBox = document.getElementById('stats-boite-select')?.value || '';
  if (selectedBox && String(selectedBox) !== String(window.argosDirectBridge.boxId)) return;
  const metrics = argosDirectMetrics(payload, true);
  const label = new Date(payload.timestamp).toLocaleTimeString('fr-FR');
  const entries = {
    'chart-temp': metrics.temperature,
    'chart-hum': metrics.humidity,
    'chart-press': metrics.pressure,
    'chart-shock': metrics.shock
  };
  Object.entries(entries).forEach(([id, value]) => {
    const chart = charts?.[id];
    if (!chart || !Number.isFinite(Number(value))) return;
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(Number(value));
    if (chart.data.labels.length > 60) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update('none');
  });
}

function argosDirectMergeIntoApplication(payload) {
  if (!Array.isArray(DB_CONTAINERS)) return;
  const bridge = window.argosDirectBridge;
  const sensors = payload.sensors || {};
  const position = payload.position || {};
  const quality = payload.quality || {};
  const dhtValid = quality.dhtValid !== false;
  const mpuValid = quality.mpuValid !== false;
  const distanceValid = quality.distanceValid !== false;
  const pressureValid = quality.pressureMeasured !== false;
  const batteryValid = quality.batteryMeasured !== false;
  const hasPosition = !(Number(position.latitude) === 0 && Number(position.longitude) === 0);
  let container = DB_CONTAINERS.find(item => String(item.id_boite) === String(bridge.boxId));
  if (!container) {
    container = {
      id_boite: String(bridge.boxId),
      id: payload.containerId || String(bridge.boxId),
      id_conteneurs: payload.containerId || null,
      type_conteneurs: payload.containerId ? 'Conteneur connecté' : 'Boîte non assignée',
      alerts: []
    };
    DB_CONTAINERS.push(container);
  }
  const alerts = [];
  if (sensors.flameDetected && payload.modes?.flameDetectionEnabled) alerts.push('Flamme détectée');
  if (sensors.doorOpen && payload.modes?.securityEnabled) alerts.push('Porte ouverte');
  if (sensors.securityAlarm && payload.modes?.securityEnabled) alerts.push('Alarme de sécurité');
  Object.assign(container, {
    device_uid: payload.deviceUid,
    sequence: payload.sequence,
    temp: dhtValid ? sensors.temperature : null,
    humidity: dhtValid ? sensors.humidity : null,
    pressure: pressureValid ? sensors.pressure : null,
    shock: mpuValid ? sensors.shock : null,
    battery: batteryValid ? sensors.batteryLevel : null,
    distance: distanceValid ? sensors.distanceCm : null,
    acceleration_x: mpuValid ? sensors.accelerationX : null,
    acceleration_y: mpuValid ? sensors.accelerationY : null,
    acceleration_z: mpuValid ? sensors.accelerationZ : null,
    speed: position.speed,
    lat: hasPosition ? position.latitude : (container.lat ?? null),
    lon: hasPosition ? position.longitude : (container.lon ?? null),
    security_alarm: sensors.securityAlarm,
    security_enabled: payload.modes?.securityEnabled,
    quality: payload.quality || {},
    alerts,
    status: alerts.length ? 'danger' : 'ok',
    lastUpdate: new Date(payload.timestamp).toLocaleString('fr-FR')
  });
  if (typeof updateContainerPageUI === 'function') updateContainerPageUI();
  if (typeof updateMapPageUI === 'function') updateMapPageUI();
  if (currentPage === 'map' && typeof refreshMapMarkers === 'function') refreshMapMarkers();
}

async function argosDirectFetchEsp(path, options = {}) {
  const bridge = window.argosDirectBridge;
  if (window.location.protocol === 'https:' && bridge.baseUrl.startsWith('http:')) {
    throw new Error("Le navigateur bloque HTTP depuis une page HTTPS. Ouvrez ARGOS par son adresse locale HTTP pour utiliser le mode direct.");
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4500);
  try {
    const response = await nativeFetch(`${bridge.baseUrl}${path}`, {
      ...options,
      mode: 'cors',
      cache: 'no-store',
      credentials: 'omit',
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'X-ARGOS-Setup-Key': bridge.setupKey,
        'X-ARGOS-Client-Timestamp': new Date().toISOString(),
        ...(options.headers || {})
      }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `ESP32 HTTP ${response.status}`);
    return data;
  } finally {
    clearTimeout(timeout);
  }
}

async function argosDirectGrantedPosition() {
  if (!navigator.permissions?.query || !navigator.geolocation) return null;
  try {
    const permission = await navigator.permissions.query({name: 'geolocation'});
    if (permission.state !== 'granted') return null;
    return await new Promise(resolve => navigator.geolocation.getCurrentPosition(
      position => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      }),
      () => resolve(null),
      {enableHighAccuracy: true, timeout: 3500, maximumAge: 120000}
    ));
  } catch (_) {
    return null;
  }
}

async function argosDirectNormalizeTelemetry(raw) {
  const bridge = window.argosDirectBridge;
  const payload = typeof structuredClone === 'function'
    ? structuredClone(raw?.telemetry || raw)
    : JSON.parse(JSON.stringify(raw?.telemetry || raw));
  if (!payload || typeof payload !== 'object') throw new Error('Snapshot ESP32 invalide');
  const uid = String(payload.deviceUid || payload.device_uid || '').trim();
  if (!uid) throw new Error('Le snapshot ne contient pas de deviceUid');
  if (uid !== bridge.expectedUid) throw new Error(`ESP32 incorrect : ${uid} au lieu de ${bridge.expectedUid}`);
  payload.deviceUid = uid;
  payload.blackBoxId = Number(bridge.boxId);
  payload.containerId = payload.containerId || payload.container_id || null;
  payload.type = 'telemetry';
  if (!Number.isInteger(Number(payload.sequence)) || Number(payload.sequence) < 0) {
    throw new Error('Séquence firmware absente ou invalide');
  }
  payload.sequence = Number(payload.sequence);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(payload.messageId || ''))) {
    payload.messageId = argosDirectUuid();
  }
  const timestamp = Date.parse(payload.timestamp);
  if (!Number.isFinite(timestamp) || Math.abs(Date.now() - timestamp) > 5.5 * 60 * 60 * 1000) {
    payload.timestamp = new Date().toISOString();
  }
  payload.position = payload.position && typeof payload.position === 'object' ? payload.position : {};
  payload.sensors = payload.sensors && typeof payload.sensors === 'object' ? payload.sensors : {};
  payload.modes = payload.modes && typeof payload.modes === 'object' ? payload.modes : {};

  const latitude = argosDirectNumber(payload.position.latitude, 0);
  const longitude = argosDirectNumber(payload.position.longitude, 0);
  if (latitude === 0 && longitude === 0) {
    const fallback = await argosDirectGrantedPosition();
    if (fallback) {
      Object.assign(payload.position, fallback, {source: 'BROWSER_FALLBACK'});
      bridge.positionStatus = 'GPS ESP32 = 0,0 • position déjà autorisée de cet appareil utilisée sans nouvelle demande';
    } else {
      bridge.positionStatus = 'GPS ESP32 = 0,0 • aucune autorisation préalable : dernier secours serveur conservé';
    }
  } else {
    bridge.positionStatus = 'Position GPS fournie par l’ESP32';
  }
  return payload;
}

async function argosDirectSendToApi(url, body, kind = 'telemetry') {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await secureApiFetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
      signal: controller.signal
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `ARGOS HTTP ${response.status}`);
      error.httpStatus = response.status;
      throw error;
    }
    return {sent: true, data};
  } catch (error) {
    if (error.httpStatus && error.httpStatus < 500) throw error;
    argosDirectEnqueue({kind, url, body});
    return {sent: false, queued: true};
  } finally {
    clearTimeout(timeout);
  }
}

async function flushArgosDirectQueue() {
  const bridge = window.argosDirectBridge;
  if (bridge.flushing) return;
  let queue = argosDirectReadQueue();
  if (!queue.length) return;
  bridge.flushing = true;
  try {
    let processed = 0;
    while (queue.length && processed < 40) {
      queue = argosDirectReadQueue();
      if (!queue.length) break;
      const item = queue[0];
      if (item.kind === 'security-audit' && String(item.actorUserId || '') !== String(currentUserId || '')) break;
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4000);
        const response = await secureApiFetch(item.url, {
          method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(item.body),
          signal: controller.signal
        });
        clearTimeout(timeout);
        // Authentification expirée, limitation ou panne serveur : conserver
        // toute la file et réessayer après reconnexion, sans perdre de mesure.
        if (!response.ok && ([401, 403, 408, 425, 429].includes(response.status) || response.status >= 500)) break;
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          console.warn('Mesure directe rejetée définitivement', data.error || response.status);
        }
        const latestQueue = argosDirectReadQueue();
        const itemIndex = latestQueue.findIndex(entry => entry.queueId === item.queueId);
        if (itemIndex >= 0) latestQueue.splice(itemIndex, 1);
        else latestQueue.shift();
        queue = latestQueue;
        argosDirectWriteQueue(queue);
        processed += 1;
      } catch (_) {
        break;
      }
    }
    argosDirectUpdateStatusUi();
  } finally {
    bridge.flushing = false;
  }
}

async function argosDirectPoll() {
  const bridge = window.argosDirectBridge;
  if (!bridge.running || bridge.polling) return;
  bridge.polling = true;
  try {
    const raw = await argosDirectFetchEsp('/api/v1/telemetry');
    const payload = await argosDirectNormalizeTelemetry(raw);
    const fingerprint = `${payload.messageId}:${payload.sequence}`;
    bridge.lastTelemetry = payload;
    argosDirectRenderTelemetry(payload);
    if (fingerprint !== bridge.lastFingerprint) {
      bridge.lastFingerprint = fingerprint;
      const url = `/api/black-boxes/${encodeURIComponent(bridge.boxId)}/direct-telemetry`;
      // Toujours mettre en file puis vider en FIFO. Ainsi une séquence N ne peut
      // jamais dépasser N-1 après une coupure réseau.
      argosDirectEnqueue({kind: 'telemetry', url, body: payload});
      await flushArgosDirectQueue();
      const stillQueued = argosDirectReadQueue().some(item => item.body?.messageId === payload.messageId);
      argosDirectSetStatus(
        !stillQueued ? 'Mesure locale reçue et enregistrée par ARGOS' : 'Mesure locale affichée • synchronisation ARGOS en attente',
        !stillQueued ? 'success' : 'warn'
      );
    } else {
      argosDirectSetStatus('ESP32 connecté • en attente de la prochaine séquence', 'success');
    }
  } catch (error) {
    const message = error.name === 'AbortError'
      ? 'ESP32 non joignable : vérifiez le Wi-Fi ARGOS-SETUP'
      : error.message;
    argosDirectSetStatus(message, 'error');
  } finally {
    bridge.polling = false;
  }
}

async function verifyArgosDirectDevice({boxId, expectedUid, baseUrl, setupKey}) {
  const bridge = window.argosDirectBridge;
  const previous = {baseUrl: bridge.baseUrl, setupKey: bridge.setupKey};
  bridge.baseUrl = String(baseUrl || 'http://192.168.4.1').replace(/\/$/, '');
  bridge.setupKey = setupKey || 'ARGOS-PROVISION-2026';
  try {
    const info = await argosDirectFetchEsp('/api/device/info');
    const uid = String(info.deviceUid || info.device_uid || '').trim();
    if (!uid) throw new Error('Identité ESP32 absente');
    if (expectedUid && uid !== String(expectedUid)) throw new Error(`Mauvaise boîte : ${uid} au lieu de ${expectedUid}`);
    const securityEnabled = info.modes?.securityEnabled ?? info.securityEnabled ?? info.security_enabled;
    if (typeof securityEnabled === 'boolean') bridge.deviceSecurityEnabled = securityEnabled;
    return uid;
  } catch (error) {
    bridge.baseUrl = previous.baseUrl;
    bridge.setupKey = previous.setupKey;
    throw error;
  }
}

async function startArgosDirectBridge(config) {
  if (!argosDirectRoleAllowed()) throw new Error('Connexion directe réservée aux gestionnaires autorisés');
  const bridge = window.argosDirectBridge;
  const boxId = Number(config.boxId);
  if (!Number.isInteger(boxId) || boxId <= 0) throw new Error('Boîte ARGOS invalide');
  const expectedUid = String(config.expectedUid || '').trim();
  if (!expectedUid) throw new Error('Cette boîte ne possède pas de deviceUid enregistré');
  const baseUrl = String(config.baseUrl || 'http://192.168.4.1').replace(/\/$/, '');
  const setupKey = config.setupKey || 'ARGOS-PROVISION-2026';
  argosDirectSetStatus('Vérification de l’identité ESP32…', 'info');
  const detectedUid = await verifyArgosDirectDevice({boxId, expectedUid, baseUrl, setupKey});
  stopArgosDirectBridge(false);
  Object.assign(bridge, {
    running: true,
    boxId,
    expectedUid: detectedUid,
    baseUrl,
    setupKey,
    pollMs: Math.max(1000, Math.min(30000, Number(config.pollMs) || 2000)),
    lastFingerprint: '',
    samples: [],
    status: 'ESP32 identifié • première mesure en cours',
    statusTone: 'success'
  });
  sessionStorage.setItem(ARGOS_DIRECT_SESSION_KEY, JSON.stringify({
    boxId, expectedUid: detectedUid, baseUrl, setupKey, pollMs: bridge.pollMs
  }));
  let announcement;
  try {
    announcement = await argosDirectSendToApi(
      `/api/black-boxes/${encodeURIComponent(boxId)}/direct-session`,
      {deviceUid: detectedUid},
      'direct-session'
    );
  } catch (error) {
    stopArgosDirectBridge();
    throw error;
  }
  if (announcement.sent) bridge.shareUrl = announcement.data?.shareUrl || '';
  await argosDirectPoll();
  bridge.timer = setInterval(argosDirectPoll, bridge.pollMs);
  argosDirectUpdateStatusUi();
  return detectedUid;
}

function stopArgosDirectBridge(clearSession = true) {
  const bridge = window.argosDirectBridge;
  if (bridge.audioRecorder?.state === 'recording') bridge.audioRecorder.stop();
  if (bridge.timer) clearInterval(bridge.timer);
  bridge.timer = null;
  bridge.running = false;
  bridge.polling = false;
  bridge.status = 'Connexion directe arrêtée';
  bridge.statusTone = 'info';
  if (clearSession) sessionStorage.removeItem(ARGOS_DIRECT_SESSION_KEY);
  argosDirectUpdateStatusUi();
}

async function resumeArgosDirectBridgeSession() {
  if (window.argosDirectBridge.running || !argosDirectRoleAllowed()) return;
  try {
    const config = JSON.parse(sessionStorage.getItem(ARGOS_DIRECT_SESSION_KEY) || 'null');
    if (config?.boxId && config?.expectedUid) await startArgosDirectBridge(config);
  } catch (error) {
    console.info('Pont direct non repris :', error.message);
  }
}

function buildArgosDirectLivePanel(boxId) {
  const bridge = window.argosDirectBridge;
  const isActive = bridge.running && String(bridge.boxId) === String(boxId);
  return `
    <div data-argos-direct-box="${escapeHTML(boxId)}" style="margin-top:14px;padding:12px;border:1px solid var(--cyan);border-radius:10px;background:rgba(0,212,255,.05)">
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px">
        <strong><i class="fas fa-wave-square"></i> Données ESP32 en direct</strong>
        <button data-argos-direct-stop type="button" class="btn-secondary" onclick="stopArgosDirectBridge()" ${isActive ? '' : 'disabled'}><i class="fas fa-stop"></i> Arrêter</button>
      </div>
      <div data-argos-direct-status style="font-size:12px;color:var(--text3);margin-bottom:8px">${escapeHTML(isActive ? bridge.status : 'Connexion non démarrée')}</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:8px;font-size:11px">
        ${[
          ['temperature','Température'], ['humidity','Humidité'], ['pressure','Pression'],
          ['shock','Choc'], ['distance','Distance'], ['battery','Batterie'],
          ['acceleration','Accélération X/Y/Z'], ['position','Position'], ['sequence','Séquence'], ['timestamp','Reçue à']
        ].map(([key, label]) => `<div style="padding:8px;background:var(--bg3);border-radius:7px"><span style="color:var(--text3)">${label}</span><br><strong data-argos-direct-metric="${key}">—</strong></div>`).join('')}
      </div>
      <div data-argos-direct-position-status style="font-size:11px;color:var(--text3);margin-top:8px">${escapeHTML(bridge.positionStatus)}</div>
      <div data-argos-direct-quality style="font-size:11px;color:var(--amber);margin-top:5px">Qualité capteurs en attente…</div>
      <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)">
        <div style="font-size:11px;color:var(--text3);margin-bottom:7px">Audio capturé avec le microphone de cet ordinateur/téléphone</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn-danger" data-argos-audio-start onclick="startArgosDirectAudioRecording(${Number(boxId)})"><i class="fas fa-microphone"></i> Enregistrer</button>
          <button type="button" class="btn-secondary" data-argos-audio-stop onclick="stopArgosDirectAudioRecording()" disabled><i class="fas fa-stop"></i> Arrêter et sauvegarder</button>
        </div>
        <div data-argos-audio-status style="font-size:11px;color:var(--text3);margin-top:6px">Aucun enregistrement en cours.</div>
      </div>
    </div>`;
}

function argosDirectAudioUi(message, recording = false, tone = 'var(--text3)') {
  document.querySelectorAll('[data-argos-audio-status]').forEach(element => {
    element.textContent = message;
    element.style.color = tone;
  });
  document.querySelectorAll('[data-argos-audio-start]').forEach(button => { button.disabled = recording; });
  document.querySelectorAll('[data-argos-audio-stop]').forEach(button => { button.disabled = !recording; });
}

async function startArgosDirectAudioRecording(boxId) {
  const bridge = window.argosDirectBridge;
  if (!bridge.running || String(bridge.boxId) !== String(boxId)) {
    return showToast('Démarrez d’abord la réception Wi-Fi directe.', 'warn');
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    return showToast('Ce navigateur ne permet pas l’enregistrement audio.', 'error');
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const preferredTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    const mimeType = preferredTypes.find(type => MediaRecorder.isTypeSupported(type)) || '';
    const recorder = new MediaRecorder(stream, mimeType ? {mimeType} : undefined);
    bridge.audioStream = stream;
    bridge.audioRecorder = recorder;
    bridge.audioChunks = [];
    bridge.audioStartedAt = new Date();
    recorder.ondataavailable = event => { if (event.data?.size) bridge.audioChunks.push(event.data); };
    recorder.onerror = event => argosDirectAudioUi(event.error?.message || 'Erreur de capture audio', false, 'var(--red)');
    recorder.onstop = () => uploadArgosDirectAudio(boxId);
    recorder.start(1000);
    bridge.audioStopTimer = setTimeout(() => stopArgosDirectAudioRecording(), 5 * 60 * 1000);
    argosDirectAudioUi('Enregistrement en cours… durée maximale 5 minutes.', true, 'var(--red)');
  } catch (error) {
    argosDirectAudioUi(`Microphone inaccessible : ${error.message}`, false, 'var(--red)');
  }
}

function stopArgosDirectAudioRecording() {
  const recorder = window.argosDirectBridge.audioRecorder;
  if (recorder?.state === 'recording') recorder.stop();
}

async function uploadArgosDirectAudio(boxId) {
  const bridge = window.argosDirectBridge;
  clearTimeout(bridge.audioStopTimer);
  bridge.audioStream?.getTracks().forEach(track => track.stop());
  const startedAt = bridge.audioStartedAt || new Date();
  const durationSeconds = Math.max(1, Math.round((Date.now() - startedAt.getTime()) / 1000));
  const mimeType = bridge.audioRecorder?.mimeType || bridge.audioChunks[0]?.type || 'audio/webm';
  const blob = new Blob(bridge.audioChunks, {type: mimeType});
  bridge.audioRecorder = null;
  bridge.audioStream = null;
  bridge.audioChunks = [];
  if (!blob.size) return argosDirectAudioUi('Aucun son capturé.', false, 'var(--red)');
  argosDirectAudioUi('Sauvegarde sécurisée du son…', false, 'var(--cyan)');
  const form = new FormData();
  form.append('audio', blob, `argos-${boxId}-${Date.now()}.webm`);
  form.append('startedAt', startedAt.toISOString());
  form.append('durationSeconds', String(durationSeconds));
  try {
    const response = await secureApiFetch(`/api/black-boxes/${encodeURIComponent(boxId)}/direct-audio`, {method:'POST', body:form});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    argosDirectAudioUi('Son sauvegardé. Il est disponible dans l’historique du trajet.', false, 'var(--green)');
    showToast('Enregistrement audio sauvegardé.', 'success');
  } catch (error) {
    argosDirectAudioUi(`Sauvegarde impossible : ${error.message}`, false, 'var(--red)');
  }
}

function buildArgosDirectSettingsCard() {
  if (!argosDirectRoleAllowed()) return '';
  setTimeout(loadArgosDirectSettingsBoxes, 0);
  return `
    <div class="card" style="margin-bottom:16px;border:1px solid var(--cyan)">
      <div class="settings-title"><i class="fas fa-satellite-dish" style="color:var(--cyan)"></i> ESP32 en connexion directe</div>
      <p style="font-size:12px;color:var(--text2);line-height:1.5">Connectez d’abord cet appareil au Wi-Fi <strong>ARGOS-SETUP-…</strong>. ARGOS vérifie l’ID, lit les capteurs immédiatement et synchronise chaque nouvelle séquence.</p>
      <div class="form-field" style="margin:12px 0"><label>Boîte enregistrée</label><select id="direct-settings-box" onchange="argosDirectSettingsBoxChanged()"><option value="">Chargement…</option></select></div>
      <div class="form-row">
        <div class="form-field"><label>Adresse ESP32</label><input id="direct-settings-url" type="url" value="http://192.168.4.1"></div>
        <div class="form-field"><label>Clé locale</label><input id="direct-settings-key" type="password" value="ARGOS-PROVISION-2026"></div>
      </div>
      <div class="form-field" style="margin-top:10px"><label>Lecture</label><select id="direct-settings-poll"><option value="1000">Chaque seconde</option><option value="2000" selected>Toutes les 2 secondes</option><option value="5000">Toutes les 5 secondes</option></select></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
        <button class="btn-primary" style="width:auto" onclick="startArgosDirectFromSettings()"><i class="fas fa-play"></i> Identifier et recevoir</button>
        <button class="btn-secondary" onclick="stopArgosDirectBridge()"><i class="fas fa-stop"></i> Arrêter</button>
      </div>
      <div style="margin-top:12px;padding:10px;border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:space-between;gap:12px">
        <div><strong>Mode sécurité des portes</strong><div style="font-size:11px;color:var(--text3)">L’action locale et l’auteur sont audités par ARGOS.</div></div>
        <label class="toggle-switch"><input id="direct-settings-security" data-argos-security-box="" type="checkbox" onchange="sendArgosDirectSecurity(this)"><span class="toggle-slider"></span></label>
      </div>
      <div data-argos-direct-running style="margin-top:10px;font-size:12px">ARRÊTÉ</div>
      <div id="direct-settings-live"></div>
    </div>`;
}

async function loadArgosDirectSettingsBoxes() {
  const select = document.getElementById('direct-settings-box');
  if (!select) return;
  let boxes = [];
  try {
    const response = await secureApiFetch('/api/black-boxes/my-boxes');
    const data = await response.json();
    if (response.ok) boxes = data.boxes || [];
    else boxes = Object.values(window.argosBlackBoxesById || {});
  } catch (_) {
    boxes = Object.values(window.argosBlackBoxesById || {});
  }
  if (!boxes.length && Array.isArray(DB_CONTAINERS)) {
    boxes = DB_CONTAINERS.map(item => ({
      id_boite: item.id_boite,
      numero_serie: item.numero_serie || `Boîte #${item.id_boite}`,
      device_uid: item.device_uid
    }));
  }
  const active = window.argosDirectBridge;
  if (active.boxId && !boxes.some(box => String(box.id_boite) === String(active.boxId))) {
    boxes.push({id_boite: active.boxId, numero_serie: `Boîte #${active.boxId}`, device_uid: active.expectedUid});
  }
  select.innerHTML = '<option value="">Sélectionner une boîte…</option>' + boxes
    .filter(box => box.id_boite && box.device_uid)
    .map(box => `<option value="${escapeHTML(box.id_boite)}" data-device-uid="${escapeHTML(box.device_uid)}">${escapeHTML(box.numero_serie || `Boîte #${box.id_boite}`)} — ${escapeHTML(box.device_uid)}</option>`)
    .join('');
  if (active.boxId) select.value = String(active.boxId);
  argosDirectSettingsBoxChanged();
}

function argosDirectSettingsBoxChanged() {
  const select = document.getElementById('direct-settings-box');
  const boxId = select?.value || '';
  const security = document.getElementById('direct-settings-security');
  if (security) security.dataset.argosSecurityBox = boxId;
  const live = document.getElementById('direct-settings-live');
  if (live) live.innerHTML = boxId ? buildArgosDirectLivePanel(boxId) : '';
  if (window.argosDirectBridge.lastTelemetry && String(window.argosDirectBridge.boxId) === String(boxId)) {
    argosDirectRenderTelemetry(window.argosDirectBridge.lastTelemetry);
  }
}

async function startArgosDirectFromSettings() {
  const select = document.getElementById('direct-settings-box');
  const option = select?.selectedOptions?.[0];
  try {
    await startArgosDirectBridge({
      boxId: select?.value,
      expectedUid: option?.dataset.deviceUid,
      baseUrl: document.getElementById('direct-settings-url')?.value,
      setupKey: document.getElementById('direct-settings-key')?.value,
      pollMs: document.getElementById('direct-settings-poll')?.value
    });
    showToast('ESP32 identifié : réception directe active.', 'success');
  } catch (error) {
    argosDirectSetStatus(error.message, 'error');
    showToast(error.message, 'error');
  }
}

async function sendArgosDirectSecurity(input) {
  const boxId = input?.dataset.argosSecurityBox || window.argosDirectBridge.boxId;
  const enabled = Boolean(input?.checked);
  if (!argosDirectRoleAllowed()) {
    if (input) input.checked = !enabled;
    return showToast('Mode sécurité réservé aux gestionnaires autorisés.', 'error');
  }
  if (!boxId) {
    if (input) input.checked = !enabled;
    return showToast('Sélectionnez une boîte.', 'warn');
  }
  if (input) input.disabled = true;
  try {
    const bridge = window.argosDirectBridge;
    const isDirect = bridge.running && String(bridge.boxId) === String(boxId);
    if (isDirect) {
      await argosDirectFetchEsp('/api/v1/security', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled})
      });
      if (bridge.lastTelemetry?.modes) bridge.lastTelemetry.modes.securityEnabled = enabled;
      bridge.deviceSecurityEnabled = enabled;
      const auditBody = {enabled, delivery: 'direct'};
      const fallback = await argosDirectGrantedPosition();
      if (fallback) Object.assign(auditBody, fallback);
      const result = await argosDirectSendToApi(
        `/api/black-boxes/${encodeURIComponent(boxId)}/commands/security`, auditBody, 'security-audit'
      );
      showToast(
        enabled ? 'Sécurité enclenchée sur l’ESP32.' : 'Sécurité bloquée sur l’ESP32.',
        result.sent ? 'success' : 'warn'
      );
      await argosDirectPoll();
    } else {
      await sendContainerCommand(boxId, 'security', enabled);
    }
  } catch (error) {
    if (input) input.checked = !enabled;
    showToast(`Sécurité non modifiée : ${error.message}`, 'error');
  } finally {
    if (input) input.disabled = false;
  }
}

function buildArgosDirectStatsPanel() {
  return `
    <div id="argos-direct-stats-card" class="card" style="display:none;margin-bottom:16px;border:1px solid var(--cyan)">
      <div class="card-header"><span class="card-title"><i class="fas fa-wave-square"></i> Session ESP32 directe</span><span class="badge badge-info" data-argos-direct-running>ARRÊTÉ</span></div>
      <div class="grid-4">
        <div class="stat-card"><div class="stat-label">Mesures reçues</div><div class="stat-value" data-argos-direct-stat="count">0</div></div>
        <div class="stat-card"><div class="stat-label">Temp. moyenne</div><div class="stat-value" data-argos-direct-stat="avgTemperature">—</div></div>
        <div class="stat-card"><div class="stat-label">Humidité moyenne</div><div class="stat-value" data-argos-direct-stat="avgHumidity">—</div></div>
        <div class="stat-card"><div class="stat-label">Choc maximal</div><div class="stat-value" data-argos-direct-stat="maxShock">—</div></div>
      </div>
    </div>`;
}

window.addEventListener('online', flushArgosDirectQueue);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && window.argosDirectBridge.running) argosDirectPoll();
});
setTimeout(resumeArgosDirectBridgeSession, 800);
