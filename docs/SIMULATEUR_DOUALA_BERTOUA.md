# Simulation IoT Douala → Yaoundé → Bertoua

## Lancement

Le backend doit être démarré. L'appareil simulé doit être enrôlé, actif et
affecté à la boîte noire et au conteneur correspondants. La génération émet 600
trames à 1 Hz; le POST HTTP est réalisé dans un thread d'envoi séparé.

```bash
python3 simulateur_iot.py --base-url http://127.0.0.1:5002 simulate-route \
  --device-uid ARGOS-ESP32-001 \
  --api-key CLE_APPAREIL \
  --black-box-id 1 \
  --container-id MSCU1234566
```

Le script envoie vers `POST /api/iot/telemetry`, avec l'en-tête
`X-Device-Key`. Il ne requiert aucune dépendance supplémentaire à `requests`,
déjà utilisée par le projet. La lecture navigateur se fait par
`GET /api/stats/live`, authentifiée par le jeton ARGOS. Le dépôt n'embarque pas
de serveur Socket.IO; ce flux REST est la voie déjà disponible.

## Chronologie exacte

Les intervalles sont inclusifs au début et exclusifs à la fin. L'arrêt et la
déviation se chevauchent de t=500 à t=519 : pendant cette période, la vitesse
reste à 0 et le point GPS est décalé; les deux événements sont conservés.

| Temps | Trame / état |
|---|---|
| t=0…119 | Route normale, tracé vert |
| t=120 | Ouverture de porte suspecte; `sensors.doorOpen=true` |
| t=121…269 | Route normale |
| t=270 | Choc anormal; `sensors.shock=12`, accélération élevée |
| t=271…399 | Route normale |
| t=400…519 | Arrêt non planifié; `position.speed=0` |
| t=500…579 | Déviation GPS de 8 km, `quality.scenario.isDeviated=true`, tronçon rouge |
| t=520…599 | Déviation active et reprise du déplacement |
| t=580…599 | Retour au tracé nominal |

Chaque trame comporte `quality.dataOrigin="SYNTHETIC"` et un identifiant de
scénario. Les valeurs simulées ne doivent pas être confondues avec des mesures
terrain.

## Forme JSON réellement émise

Exemple de la trame générée à t=120 (valeurs GPS, heure et UUID représentatifs) :

```json
{
  "messageId": "e606d3e1-c607-4978-8f8c-12cd701a93ae",
  "type": "telemetry",
  "deviceUid": "ARGOS-ESP32-001",
  "blackBoxId": 1,
  "containerId": "MSCU1234566",
  "timestamp": "2026-11-07T10:02:00.000+00:00",
  "sequence": 121,
  "position": {
    "latitude": 3.9,
    "longitude": 10.52,
    "accuracy": 8.0,
    "speed": 55.0,
    "heading": 90.0,
    "source": "ARGOS_SIMULATOR"
  },
  "sensors": {
    "temperature": 28.0,
    "humidity": 68.0,
    "shock": 0.2,
    "pressure": 1013.0,
    "flameDetected": false,
    "doorOpen": true,
    "batteryLevel": 96.0,
    "lightLevel": 1200,
    "soundLevel": 350,
    "distanceCm": 40.0,
    "accelerationX": 0.1,
    "accelerationY": -0.1,
    "accelerationZ": 9.8,
    "securityAlarm": false
  },
  "modes": {
    "securityEnabled": true,
    "audioRecordingEnabled": false,
    "audioListeningEnabled": false,
    "flameDetectionEnabled": false
  },
  "quality": {
    "dhtValid": true,
    "mpuValid": true,
    "gpsValid": true,
    "distanceValid": true,
    "sdReady": false,
    "pressureMeasured": false,
    "batteryMeasured": false,
    "timestampSource": "SIMULATION",
    "dataOrigin": "SYNTHETIC",
    "datasetId": "douala-yaounde-bertoua-<session>",
    "scenarioId": "douala-yaounde-bertoua",
    "sampleLabel": "simulation temporelle; données synthétiques"
  },
  "scenario": {
    "simulation_id": "douala-yaounde-bertoua-<session>",
    "t_seconds": 120,
    "event_code": "SUSPICIOUS_DOOR_OPEN",
    "event": "Ouverture de porte suspecte",
    "events": [
      {"code": "SUSPICIOUS_DOOR_OPEN", "label": "Ouverture de porte suspecte"}
    ],
    "door_open": true,
    "shock_event": false,
    "stopped": false,
    "is_deviated": false,
    "speed_kmh": 55.0
  }
}
```

L'API valide les champs usuels et reporte les métadonnées de scénario dans
`quality.scenario` dans Redis et la réponse live. Le POST renvoie un accusé par
trame dans la console du script.

## JavaScript Leaflet — réception live, tracé et alertes

Ce snippet s'intègre dans une page où Leaflet est chargé et où existe un élément
`<div id="argos-live-map" style="height: 480px"></div>`. Il utilise le jeton de
session existant `argosAccessToken` et l'endpoint live authentifié. Les alertes
sont insérées avec `textContent` pour ne pas interpréter leur libellé comme HTML.

```js
const boxId = 1;
const deviceUid = "ARGOS-ESP32-001";
const accessToken = sessionStorage.getItem("argosAccessToken")
  || localStorage.getItem("argosAccessToken");

const liveMap = L.map("argos-live-map").setView([4.1, 11.4], 7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors"
}).addTo(liveMap);

const trailGroups = { normal: [], deviated: [] };
const trailLayers = {
  normal: L.polyline([], { color: "#16a34a", weight: 5 }).addTo(liveMap),
  deviated: L.polyline([], { color: "#dc2626", weight: 6 }).addTo(liveMap)
};
let currentGroup = null;
let marker = null;
let previousPoint = null;
let lastSequence = -1;
let lastEventCodes = new Set();
let stopped = false;

function showAgentAlert(label, timestamp) {
  const panel = document.getElementById("argos-live-alerts");
  if (!panel) return;
  const item = document.createElement("div");
  item.className = "argos-live-alert";
  item.setAttribute("role", "alert");
  item.textContent = `${timestamp || "Maintenant"} — ${label}`;
  panel.prepend(item);
}

function acceptTelemetry(row) {
  const point = row.position;
  if (!point || !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) return;
  const latlng = [point.latitude, point.longitude];
  const scenario = row.quality?.scenario || {};
  const isDeviated = scenario.isDeviated === true;
  const group = isDeviated ? "deviated" : "normal";

  if (previousPoint) {
    if (group !== currentGroup) trailGroups[group].push([previousPoint, latlng]);
    else trailGroups[group][trailGroups[group].length - 1].push(latlng);
    trailLayers.normal.setLatLngs(trailGroups.normal);
    trailLayers.deviated.setLatLngs(trailGroups.deviated);
  } else {
    trailGroups[group].push([latlng]);
    trailLayers[group].setLatLngs(trailGroups[group]);
  }
  currentGroup = group;
  previousPoint = latlng;

  const color = isDeviated ? "#dc2626" : "#16a34a";
  if (!marker) marker = L.circleMarker(latlng, { radius: 8, color, fillColor: color, fillOpacity: 1 }).addTo(liveMap);
  else marker.setLatLng(latlng).setStyle({ color, fillColor: color });
  marker.bindPopup(
    `<strong>${isDeviated ? "Déviation" : "Position"}</strong><br>` +
    `${row.containerId || "Conteneur"}<br>${point.speed ?? 0} km/h`
  );
  liveMap.panTo(latlng, { animate: true, duration: 0.4 });

  const codes = new Set((scenario.events || []).map(event => event.code));
  for (const event of scenario.events || []) {
    if (!lastEventCodes.has(event.code)) showAgentAlert(event.label, row.timestamp);
  }
  if (scenario.stopped && !lastEventCodes.has("UNPLANNED_STOP")) {
    showAgentAlert("Arrêt prolongé non planifié", row.timestamp);
  }
  lastEventCodes = codes;
  stopped = false;
  lastSequence = Math.max(lastSequence, Number(row.sequence));
}

async function pollArgosLive() {
  if (stopped) return;
  const params = new URLSearchParams({
    boite: String(boxId), device_uid: deviceUid,
    after_sequence: String(lastSequence), limit: "10", sort: "asc"
  });
  try {
    const response = await fetch(`/api/stats/live?${params}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store"
    });
    if (response.status === 401 || response.status === 403) {
      stopped = true;
      showAgentAlert("Session expirée ou accès refusé au flux live", new Date().toISOString());
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    for (const row of (result.telemetry || []).sort((a, b) => a.sequence - b.sequence)) {
      if (Number(row.sequence) > lastSequence) acceptTelemetry(row);
    }
  } catch (error) {
    console.error("Lecture télémétrie ARGOS impossible", error);
  } finally {
    if (!stopped) window.setTimeout(pollArgosLive, 1000);
  }
}

if (!accessToken) showAgentAlert("Connectez-vous à ARGOS pour recevoir les données live", "");
else pollArgosLive();
```

Le point `t=500…519` reste rouge même si sa vitesse est nulle : les deux états
sont simultanés. Les trames normales sont vertes. La route live actuelle ne
fournit que le dernier point par boîte; pour rejouer sans perte chaque trame
après une interruption du navigateur, un endpoint de lecture du Redis Stream
avec curseur est à ajouter.
