/*
 * ARGOS ESP32 (module DevKit 38 broches)
 * Compatible avec le pont direct de app/static/js/direct-bridge.js.
 *
 * Bibliothèques à installer depuis le gestionnaire Arduino :
 *   ArduinoJson 7.x, DHT sensor library, TinyGPSPlus,
 *   Adafruit MPU6050, Adafruit BMP280, Adafruit Unified Sensor.
 */

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <TinyGPSPlus.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_BMP280.h>
#include <time.h>
#include <sys/time.h>
#include <esp_system.h>

// Brochage du prototype DevKit 38 broches fourni.
constexpr uint8_t PIN_DHT = 19;
constexpr uint8_t PIN_I2C_SCL = 5;
constexpr uint8_t PIN_BUZZER = 13;
constexpr uint8_t PIN_SD_MOSI = 14;
constexpr uint8_t PIN_GPS_RX = 4;
constexpr uint8_t PIN_GPS_TX = 15;
constexpr uint8_t PIN_HCSR04_ECHO = 16;
constexpr uint8_t PIN_FLAME = 17;
constexpr uint8_t PIN_HCSR04_TRIG = 18;
constexpr uint8_t PIN_I2C_SDA = 21;
// Sortie numérique DO du module microphone. GPIO22 n'est pas une entrée ADC :
// il permet la détection d'activité sonore, pas la capture d'une forme d'onde.
constexpr uint8_t PIN_MIC = 22;
constexpr uint8_t PIN_SD_SCK = 26;
constexpr uint8_t PIN_SD_MISO = 27;

constexpr uint8_t PIN_SD_CS = 33;

constexpr char SETUP_KEY_DEFAULT[] = "ARGOS-PROVISION-2026";
// Adresse LAN de l'application ARGOS. Le bouton du portail captif utilise
// toujours cette adresse locale, indépendamment de l'URL API enregistrée.
constexpr char ARGOS_LOCAL_APP_URL[] = "http://127.0.0.2:5002";
constexpr uint32_t SAMPLE_INTERVAL_MS = 2000;
constexpr uint32_t REMOTE_SEND_INTERVAL_MS = 10000;
constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 30000;
constexpr uint32_t COMMAND_POLL_INTERVAL_MS = 5000;
constexpr float DEFAULT_DISTANCE_THRESHOLD_CM = 15.0f;
constexpr uint16_t DNS_PORT = 53;
constexpr char PORTAL_IP[] = "192.168.4.1";
// Position de repli : ENSPT, Yaoundé. Elle est publiée tant que le GPS
// physique ne dispose pas d'un fix récent et valide.
constexpr double FALLBACK_LATITUDE = 3.85;
constexpr double FALLBACK_LONGITUDE = 11.49;

DHT dht(PIN_DHT, DHT11);
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
WebServer server(80);
DNSServer dnsServer;
Preferences prefs;
SPIClass sdSpi(HSPI);
Adafruit_MPU6050 mpu;
Adafruit_BMP280 bmp;

struct Configuration {
  String deviceUid;
  String enrollmentToken;
  String apiKey;
  String apiBaseUrl;
  String wifiSsid;
  String wifiPassword;
  String containerId;
  int blackBoxId = 0;
  float distanceThresholdCm = DEFAULT_DISTANCE_THRESHOLD_CM;
  bool configured = false;
} config;

struct Measurements {
  float temperature = 0, humidity = 0, pressure = 1013.25f;
  float distanceCm = 0, ax = 0, ay = 0, az = 0, shock = 0;
  float latitude = FALLBACK_LATITUDE, longitude = FALLBACK_LONGITUDE;
  float speed = 0, heading = 0, accuracy = 50;
  int soundLevel = 0;
  int soundPeakToPeak = 0;
  float soundRms = 0;
  bool flameDetected = false, doorOpen = false, securityAlarm = false;
  bool dhtValid = false, mpuValid = false, gpsValid = false;
  bool distanceValid = false, sdReady = false, pressureMeasured = false;
} values;

bool securityEnabled = true;
bool audioRecordingEnabled = false;
bool audioListeningEnabled = false;
bool flameDetectionEnabled = true;
bool previousDoorOpen = false;
bool openingEventPending = false;
String openingEventTimestamp;
uint32_t sequenceNumber = 0;
uint32_t lastSampleAt = 0, lastRemoteSendAt = 0, lastWifiRetryAt = 0;
uint32_t lastCommandPollAt = 0;
String lastMessageId;
String lastTimestamp;

void addCors() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type,X-ARGOS-Setup-Key,X-ARGOS-Client-Timestamp");
  server.sendHeader("Access-Control-Allow-Private-Network", "true");
  server.sendHeader("Cache-Control", "no-store");
}

void sendJson(int status, const JsonDocument &doc) {
  String body;
  serializeJson(doc, body);
  addCors();
  server.send(status, "application/json", body);
}

bool localAuthorized() {
  String supplied = server.header("X-ARGOS-Setup-Key");
  if (supplied.isEmpty() && server.hasArg("plain")) {
    JsonDocument body;
    if (!deserializeJson(body, server.arg("plain"))) supplied = body["setupKey"] | "";
  }
  return supplied == SETUP_KEY_DEFAULT;
}

void rejectUnauthorized() {
  JsonDocument out;
  out["status"] = "error";
  out["error"] = "Clé locale ARGOS invalide";
  sendJson(401, out);
}

String makeUuid() {
  uint8_t b[16];
  esp_fill_random(b, sizeof(b));
  b[6] = (b[6] & 0x0F) | 0x40;
  b[8] = (b[8] & 0x3F) | 0x80;
  char out[37];
  snprintf(out, sizeof(out),
           "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
           b[0],b[1],b[2],b[3],b[4],b[5],b[6],b[7],b[8],b[9],b[10],b[11],b[12],b[13],b[14],b[15]);
  return String(out);
}

String isoTimestamp() {
  time_t now = time(nullptr);
  if (now < 1700000000) return "1970-01-01T00:00:00Z"; // corrigé par le pont navigateur
  struct tm utc;
  gmtime_r(&now, &utc);
  char out[25];
  strftime(out, sizeof(out), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(out);
}

void loadConfiguration() {
  prefs.begin("argos", true);
  config.deviceUid = prefs.getString("uid", "");
  config.enrollmentToken = prefs.getString("enroll", "");
  config.apiKey = prefs.getString("apiKey", "");
  config.apiBaseUrl = prefs.getString("apiUrl", "");
  config.wifiSsid = prefs.getString("ssid", "");
  config.wifiPassword = prefs.getString("wifiPass", "");
  config.containerId = prefs.getString("container", "");
  config.blackBoxId = prefs.getInt("boxId", 0);
  config.distanceThresholdCm = prefs.getFloat("distance", DEFAULT_DISTANCE_THRESHOLD_CM);
  securityEnabled = prefs.getBool("security", true);
  sequenceNumber = prefs.getULong("sequence", 0);
  prefs.end();
  config.configured = !config.deviceUid.isEmpty() && config.blackBoxId > 0;
}

void ensurePersistentIdentity() {
  if (!config.deviceUid.isEmpty()) return;
  uint64_t mac = ESP.getEfuseMac();
  char uid[32];
  snprintf(uid, sizeof(uid), "ARGOS-ESP32-%08X", (uint32_t)mac);
  config.deviceUid = uid;
  prefs.begin("argos", false);
  prefs.putString("uid", config.deviceUid);
  prefs.end();
}

void saveConfiguration() {
  prefs.begin("argos", false);
  prefs.putString("uid", config.deviceUid);
  prefs.putString("enroll", config.enrollmentToken);
  prefs.putString("apiKey", config.apiKey);
  prefs.putString("apiUrl", config.apiBaseUrl);
  prefs.putString("ssid", config.wifiSsid);
  prefs.putString("wifiPass", config.wifiPassword);
  prefs.putString("container", config.containerId);
  prefs.putInt("boxId", config.blackBoxId);
  prefs.putFloat("distance", config.distanceThresholdCm);
  prefs.putBool("security", securityEnabled);
  prefs.putULong("sequence", sequenceNumber);
  prefs.end();
}

float readDistanceCm() {
  digitalWrite(PIN_HCSR04_TRIG, LOW); delayMicroseconds(3);
  digitalWrite(PIN_HCSR04_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_HCSR04_TRIG, LOW);
  uint32_t duration = pulseIn(PIN_HCSR04_ECHO, HIGH, 30000);
  if (!duration) return NAN;
  return duration * 0.0343f / 2.0f;
}

void readSoundSignal() {
  // La plupart des modules LM393 ont une sortie DO active à l'état bas.
  const bool soundDetected = digitalRead(PIN_MIC) == LOW;
  values.soundLevel = soundDetected ? 100 : 0;
  values.soundRms = soundDetected ? 1.0f : 0.0f;
  values.soundPeakToPeak = soundDetected ? 1 : 0;
}

void readSensors() {
  while (gpsSerial.available()) gps.encode(gpsSerial.read());

  float t = dht.readTemperature(), h = dht.readHumidity();
  values.dhtValid = isfinite(t) && isfinite(h);
  if (values.dhtValid) { values.temperature = t; values.humidity = h; }

  float d = readDistanceCm();
  values.distanceValid = isfinite(d) && d >= 0 && d <= 1000;
  if (values.distanceValid) values.distanceCm = d;

  values.flameDetected = digitalRead(PIN_FLAME) == LOW; // modules flamme généralement actifs à LOW
  readSoundSignal();

  sensors_event_t accel, gyro, temp;
  if (values.mpuValid) {
    mpu.getEvent(&accel, &gyro, &temp);
    values.ax = accel.acceleration.x / 9.80665f;
    values.ay = accel.acceleration.y / 9.80665f;
    values.az = accel.acceleration.z / 9.80665f;
    values.shock = fabs(sqrt(values.ax*values.ax + values.ay*values.ay + values.az*values.az) - 1.0f);
  }
  if (values.pressureMeasured) values.pressure = bmp.readPressure() / 100.0f;

  values.gpsValid = gps.location.isValid() && gps.location.age() < 10000;
  if (values.gpsValid) {
    values.latitude = gps.location.lat(); values.longitude = gps.location.lng();
    values.speed = gps.speed.isValid() ? gps.speed.kmph() : 0;
    values.heading = gps.course.isValid() ? gps.course.deg() : 0;
    values.accuracy = gps.hdop.isValid() ? gps.hdop.hdop() * 5.0f : 20.0f;
  } else {
    values.latitude = FALLBACK_LATITUDE;
    values.longitude = FALLBACK_LONGITUDE;
    values.speed = 0;
    values.heading = 0;
    values.accuracy = 50;
  }

  values.doorOpen = values.distanceValid && values.distanceCm > config.distanceThresholdCm;
  values.securityAlarm = securityEnabled && (values.doorOpen || (flameDetectionEnabled && values.flameDetected));
  digitalWrite(PIN_BUZZER, values.securityAlarm ? HIGH : LOW);

  sequenceNumber++;
  lastMessageId = makeUuid();
  lastTimestamp = isoTimestamp();
  if (securityEnabled && values.doorOpen && !previousDoorOpen) {
    openingEventPending = true;
    openingEventTimestamp = lastTimestamp;
    // L'ouverture déclenche immédiatement la surveillance sonore. Un module
    // I2S/ADC est nécessaire pour transporter ensuite un véritable flux audio.
    audioListeningEnabled = true;
    audioRecordingEnabled = true;
  }
  previousDoorOpen = values.doorOpen;
  if ((sequenceNumber % 20) == 0) saveConfiguration();
}

void buildTelemetry(JsonDocument &doc) {
  doc["messageId"] = lastMessageId;
  doc["type"] = "telemetry";
  doc["deviceUid"] = config.deviceUid;
  doc["blackBoxId"] = config.blackBoxId;
  if (config.containerId.isEmpty()) doc["containerId"] = nullptr; else doc["containerId"] = config.containerId;
  doc["timestamp"] = lastTimestamp;
  doc["sequence"] = sequenceNumber;
  JsonObject p = doc["position"].to<JsonObject>();
  p["latitude"] = values.latitude; p["longitude"] = values.longitude;
  p["accuracy"] = values.accuracy; p["speed"] = values.speed;
  p["heading"] = values.heading;
  p["source"] = values.gpsValid ? "ESP32_GPS" : "ENSPT_FALLBACK";
  JsonObject s = doc["sensors"].to<JsonObject>();
  s["temperature"] = values.temperature; s["humidity"] = values.humidity;
  s["shock"] = values.shock; s["pressure"] = values.pressure;
  s["flameDetected"] = values.flameDetected; s["doorOpen"] = values.doorOpen;
  s["batteryLevel"] = 70.0; s["lightLevel"] = 0;
  s["soundLevel"] = values.soundLevel;
  s["soundRms"] = values.soundRms;
  s["soundPeakToPeak"] = values.soundPeakToPeak;
  s["distanceCm"] = values.distanceCm;
  s["accelerationX"] = values.ax; s["accelerationY"] = values.ay; s["accelerationZ"] = values.az;
  s["securityAlarm"] = values.securityAlarm;
  JsonObject m = doc["modes"].to<JsonObject>();
  m["securityEnabled"] = securityEnabled;
  m["audioRecordingEnabled"] = audioRecordingEnabled;
  m["audioListeningEnabled"] = audioListeningEnabled;
  m["flameDetectionEnabled"] = flameDetectionEnabled;
  JsonObject q = doc["quality"].to<JsonObject>();
  q["dhtValid"] = values.dhtValid; q["mpuValid"] = values.mpuValid;
  q["gpsValid"] = values.gpsValid; q["distanceValid"] = values.distanceValid;
  q["sdReady"] = values.sdReady; q["pressureMeasured"] = values.pressureMeasured;
  q["batteryMeasured"] = true; q["timestampSource"] = time(nullptr) > 1700000000 ? "NTP" : "BROWSER_REQUIRED";
  JsonObject alert = doc["alert"].to<JsonObject>();
  alert["raised"] = openingEventPending;
  alert["label"] = openingEventPending ? "OUVERTURE_CONTENEUR" : "";
  alert["occurredAt"] = openingEventPending ? openingEventTimestamp : "";
  alert["distanceCm"] = values.distanceCm;
  alert["thresholdCm"] = config.distanceThresholdCm;
  alert["latitude"] = values.latitude;
  alert["longitude"] = values.longitude;
  alert["automaticListening"] = openingEventPending && audioListeningEnabled;
}

bool httpPostJson(const String &url, const String &body, const String &deviceKey, int &status, String &response) {
  HTTPClient http;
  if (!http.begin(url)) {
    Serial.println("[HTTP] URL POST invalide : " + url);
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  if (!deviceKey.isEmpty()) http.addHeader("X-Device-Key", deviceKey);
  status = http.POST(body);
  response = status > 0 ? http.getString() : "";
  Serial.printf("[HTTP] POST %s -> %d\n", url.c_str(), status);
  if (status < 0 || status >= 400) Serial.println("[HTTP] Réponse : " + response);
  http.end();
  return status > 0;
}

bool httpGetJson(const String &url, const String &deviceKey, int &status, String &response) {
  HTTPClient http;
  if (!http.begin(url)) {
    Serial.println("[HTTP] URL GET invalide : " + url);
    return false;
  }
  if (!deviceKey.isEmpty()) http.addHeader("X-Device-Key", deviceKey);
  status = http.GET();
  response = status > 0 ? http.getString() : "";
  Serial.printf("[HTTP] GET %s -> %d\n", url.c_str(), status);
  if (status < 0 || status >= 400) Serial.println("[HTTP] Réponse : " + response);
  http.end();
  return status > 0;
}

bool syncClockFromArgos() {
  if (config.apiBaseUrl.isEmpty()) return false;
  String response; int status = 0;
  if (!httpGetJson(config.apiBaseUrl + "/api/iot/time", "", status, response) || status != 200) return false;
  JsonDocument doc;
  if (deserializeJson(doc, response)) return false;
  time_t epoch = doc["epoch"] | 0;
  if (epoch < 1700000000) return false;
  timeval tv = {epoch, 0};
  settimeofday(&tv, nullptr);
  Serial.println("[ARGOS] Horloge synchronisée depuis l'application");
  return true;
}

void acknowledgeCommand(const String &commandUid, const char *statusName, const String &message) {
  JsonDocument ack;
  ack["commandUid"] = commandUid;
  ack["deviceUid"] = config.deviceUid;
  ack["status"] = statusName;
  ack["timestamp"] = isoTimestamp();
  ack["result"]["message"] = message;
  String body, response; serializeJson(ack, body);
  int status = 0;
  httpPostJson(config.apiBaseUrl + "/api/iot/acknowledgements", body, config.apiKey, status, response);
}

void pollRemoteCommands() {
  if (WiFi.status() != WL_CONNECTED || config.apiKey.isEmpty() || config.apiBaseUrl.isEmpty()) return;
  String response; int status = 0;
  String url = config.apiBaseUrl + "/api/iot/devices/" + config.deviceUid + "/commands";
  if (!httpGetJson(url, config.apiKey, status, response) || status != 200) return;
  JsonDocument doc;
  if (deserializeJson(doc, response)) return;
  for (JsonObject command : doc["commands"].as<JsonArray>()) {
    String commandUid = command["commandUid"] | "";
    String type = command["type"] | "";
    String commandStatus = command["status"] | "";
    if (commandUid.isEmpty() || !(commandStatus == "PENDING" || commandStatus == "PUBLISHED")) continue;
    JsonObject payload = command["payload"].as<JsonObject>();
    bool applied = true;
    if (type == "SET_SECURITY_MODE") securityEnabled = payload["enabled"] | securityEnabled;
    else if (type == "SET_AUDIO_LISTENING") audioListeningEnabled = payload["enabled"] | audioListeningEnabled;
    else if (type == "SET_AUDIO_RECORDING") audioRecordingEnabled = payload["enabled"] | audioRecordingEnabled;
    else if (type == "SET_FLAME_DETECTION") flameDetectionEnabled = payload["enabled"] | flameDetectionEnabled;
    else if (type == "SET_DISTANCE_THRESHOLD") config.distanceThresholdCm = payload["distanceCm"] | config.distanceThresholdCm;
    else if (type == "REQUEST_POSITION" || type == "REQUEST_STATUS") { /* la prochaine télémétrie répond */ }
    else if (type == "TRIGGER_LOCAL_ALERT") digitalWrite(PIN_BUZZER, HIGH);
    else applied = false;
    if (applied) {
      saveConfiguration();
      acknowledgeCommand(commandUid, "EXECUTED", "Commande appliquée par l'ESP32");
    } else acknowledgeCommand(commandUid, "FAILED", "Commande non prise en charge par ce firmware");
  }
}

void enrollIfNeeded() {
  if (WiFi.status() != WL_CONNECTED || config.apiBaseUrl.isEmpty() ||
      config.enrollmentToken.isEmpty() || !config.apiKey.isEmpty()) return;
  JsonDocument request;
  request["deviceUid"] = config.deviceUid;
  request["enrollmentToken"] = config.enrollmentToken;
  String body, response; serializeJson(request, body);
  int status = 0;
  if (!httpPostJson(config.apiBaseUrl + "/api/iot/enroll", body, "", status, response) || status != 201) {
    Serial.println("[ARGOS] Échec de l'enrôlement du dispositif");
    return;
  }
  JsonDocument result;
  if (deserializeJson(result, response)) return;
  config.apiKey = result["credentials"]["apiKey"] | "";
  if (!config.apiKey.isEmpty()) {
    config.enrollmentToken = ""; saveConfiguration();
    Serial.println("[ARGOS] Enrôlement réussi, clé API enregistrée");
  }
}

void sendRemoteTelemetry() {
  if (WiFi.status() != WL_CONNECTED || config.apiKey.isEmpty() || config.apiBaseUrl.isEmpty()) return;
  if (time(nullptr) < 1700000000) {
    Serial.println("[ARGOS] NTP indisponible, synchronisation depuis ARGOS…");
    if (!syncClockFromArgos()) return;
  }
  JsonDocument doc; buildTelemetry(doc);
  String body, response; serializeJson(doc, body);
  int status = 0;
  if (httpPostJson(config.apiBaseUrl + "/api/iot/telemetry", body, config.apiKey, status, response)
      && status >= 200 && status < 300) {
    openingEventPending = false;
    Serial.printf("[ARGOS] Télémétrie transmise, séquence %lu\n", (unsigned long)sequenceNumber);
  }
}

String portalHtml() {
  String escapedUid = config.deviceUid;
  String appUrl = ARGOS_LOCAL_APP_URL;
  String html = F("<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ARGOS — Connexion sécurisée</title><style>*{box-sizing:border-box}body{margin:0;background:#06152f;color:#eaf7ff;font-family:Arial,sans-serif;min-height:100vh;display:grid;place-items:center;padding:20px}.card{width:min(560px,100%);background:linear-gradient(145deg,#0b2348,#071a36);border:1px solid #17618a;border-radius:20px;padding:28px;box-shadow:0 24px 70px #0009}.brand{color:#58ddff;font-size:30px;font-weight:800;letter-spacing:5px}.tag{color:#8ca8c5;font-size:13px;margin:4px 0 24px}.state{padding:12px;border-radius:10px;background:#0c3154;border-left:4px solid #32d7ff;margin-bottom:18px}.uid{font-family:monospace;word-break:break-all;color:#8feaff}label{display:block;font-size:12px;color:#a8bdd3;margin:14px 0 6px}input{width:100%;padding:12px;border-radius:9px;border:1px solid #28557b;background:#06172c;color:white}button,a.btn{display:block;width:100%;margin-top:14px;padding:13px;border:0;border-radius:9px;text-align:center;text-decoration:none;font-weight:700;cursor:pointer}.primary{background:#19c9ef;color:#041329}.secondary{background:#163a60;color:#eaf7ff;border:1px solid #2d668f}.note{font-size:11px;line-height:1.5;color:#829bb5;margin-top:18px}</style></head><body><main class='card'><div class='brand'>ARGOS</div><div class='tag'>Portail local du dispositif connecté</div>");
  html += "<div class='state'>Dispositif : <span class='uid'>" + escapedUid + "</span><br>État : <strong>";
  html += config.configured ? "déjà enregistré" : "première configuration";
  html += "</strong></div><label>Application ARGOS locale</label><input id='app' type='url' readonly value='" + appUrl + "'>";
  if (!config.configured) {
    html += "<button class='primary' onclick=\"go(1)\">Créer une nouvelle boîte</button>";
  }
  html += "<button class='secondary' onclick=\"go(0)\">Se connecter à ARGOS</button>"
          "<p class='note'>L’authentification reste obligatoire. Une personne non associée à cette boîte ne peut consulter aucune télémétrie.</p>"
          "<script>function go(first){let u=document.getElementById('app').value.trim().replace(/\\/$/,'');if(!/^https?:\\/\\//i.test(u)){alert('Adresse ARGOS invalide');return;}location.href=u+'/?argos_setup=1&first='+first+'&device_uid=" + escapedUid + "&esp_url=http%3A%2F%2F192.168.4.1';}</script></main></body></html>";
  return html;
}

void handlePortal() {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "text/html; charset=utf-8", portalHtml());
}

void handleInfo() {
  if (!localAuthorized()) return rejectUnauthorized();
  JsonDocument out;
  out["status"] = "success"; out["deviceUid"] = config.deviceUid;
  out["device_uid"] = config.deviceUid; out["blackBoxId"] = config.blackBoxId;
  out["configured"] = config.configured; out["apSsid"] = WiFi.softAPSSID();
  out["modes"]["securityEnabled"] = securityEnabled;
  sendJson(200, out);
}

void handleTelemetry() {
  if (!localAuthorized()) return rejectUnauthorized();
  JsonDocument out; buildTelemetry(out); sendJson(200, out);
  openingEventPending = false;
}

void handleSecurity() {
  if (!localAuthorized()) return rejectUnauthorized();
  JsonDocument body;
  if (deserializeJson(body, server.arg("plain")) || !body["enabled"].is<bool>()) {
    JsonDocument out; out["status"]="error"; out["error"]="enabled booléen requis"; return sendJson(422, out);
  }
  securityEnabled = body["enabled"].as<bool>(); saveConfiguration();
  JsonDocument out; out["status"]="success"; out["securityEnabled"]=securityEnabled; sendJson(200, out);
}

void handleAudioMode(bool listening) {
  if (!localAuthorized()) return rejectUnauthorized();
  JsonDocument body;
  if (deserializeJson(body, server.arg("plain")) || !body["enabled"].is<bool>()) {
    JsonDocument out; out["status"]="error"; out["error"]="enabled booléen requis"; return sendJson(422, out);
  }
  if (listening) audioListeningEnabled = body["enabled"].as<bool>();
  else audioRecordingEnabled = body["enabled"].as<bool>();
  JsonDocument out; out["status"]="success";
  out["audioListeningEnabled"] = audioListeningEnabled;
  out["audioRecordingEnabled"] = audioRecordingEnabled;
  sendJson(200, out);
}

void handleProvision() {
  if (!localAuthorized()) return rejectUnauthorized();
  JsonDocument body;
  DeserializationError err = deserializeJson(body, server.arg("plain"));
  if (err || !body["deviceUid"].is<const char*>() || !body["blackBoxId"].is<int>()) {
    JsonDocument out; out["status"]="error"; out["error"]="Configuration ARGOS invalide"; return sendJson(422, out);
  }
  if (config.configured &&
      (body["deviceUid"].as<String>() != config.deviceUid ||
       body["blackBoxId"].as<int>() != config.blackBoxId)) {
    JsonDocument out; out["status"]="error";
    out["error"]="Identité permanente verrouillée : création d'une autre boîte refusée";
    return sendJson(409, out);
  }
  config.deviceUid = body["deviceUid"].as<String>();
  config.blackBoxId = body["blackBoxId"].as<int>();
  config.containerId = body["containerId"] | "";
  config.enrollmentToken = body["enrollmentToken"] | "";
  config.apiBaseUrl = body["apiBaseUrl"] | "";
  config.wifiSsid = body["wifi"]["ssid"] | "";
  config.wifiPassword = body["wifi"]["password"] | "";
  config.distanceThresholdCm = body["thresholds"]["distanceCm"] | DEFAULT_DISTANCE_THRESHOLD_CM;
  config.configured = true; config.apiKey = ""; saveConfiguration();
  JsonDocument out; out["status"]="configured"; out["deviceUid"]=config.deviceUid; out["restartInMs"]=1500; sendJson(200, out);
  delay(1500); ESP.restart();
}

void registerRoutes() {
  const char *headers[] = {"X-ARGOS-Setup-Key", "X-ARGOS-Client-Timestamp"};
  server.collectHeaders(headers, 2);
  server.on("/api/device/info", HTTP_GET, handleInfo);
  server.on("/device/info", HTTP_GET, handleInfo);
  server.on("/api/v1/telemetry", HTTP_GET, handleTelemetry);
  server.on("/api/v1/security", HTTP_POST, handleSecurity);
  server.on("/api/v1/listening", HTTP_POST, [](){ handleAudioMode(true); });
  server.on("/api/v1/recording", HTTP_POST, [](){ handleAudioMode(false); });
  server.on("/api/v1/provision", HTTP_POST, handleProvision);
  server.on("/", HTTP_GET, handlePortal);
  server.on("/generate_204", HTTP_GET, handlePortal);
  server.on("/gen_204", HTTP_GET, handlePortal);
  server.on("/hotspot-detect.html", HTTP_GET, handlePortal);
  server.on("/connecttest.txt", HTTP_GET, handlePortal);
  server.on("/ncsi.txt", HTTP_GET, handlePortal);
  server.onNotFound([](){
    if (server.method() == HTTP_OPTIONS) { addCors(); server.send(204); return; }
    handlePortal();
  });
}

void startNetworks() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  uint64_t mac = ESP.getEfuseMac();
  String suffix = String((uint32_t)(mac & 0xFFFFFF), HEX); suffix.toUpperCase();
  while (suffix.length() < 6) suffix = "0" + suffix;
  WiFi.softAP("ARGOS-SETUP-" + suffix); // AP ouvert : les API restent protégées par la clé locale
  dnsServer.start(DNS_PORT, "*", WiFi.softAPIP());
  if (!config.wifiSsid.isEmpty()) WiFi.begin(config.wifiSsid.c_str(), config.wifiPassword.c_str());
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_HCSR04_TRIG, OUTPUT); pinMode(PIN_HCSR04_ECHO, INPUT);
  pinMode(PIN_FLAME, INPUT_PULLUP); pinMode(PIN_MIC, INPUT);
  digitalWrite(PIN_BUZZER, LOW);
  dht.begin();
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  values.mpuValid = mpu.begin(0x68, &Wire);
  // Adafruit_BMP280 utilise le bus global Wire configuré juste au-dessus.
  // Le second paramètre de begin() est un identifiant de puce, pas TwoWire*.
  values.pressureMeasured = bmp.begin(0x76) || bmp.begin(0x77);
  gpsSerial.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  sdSpi.begin(PIN_SD_SCK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
  values.sdReady = SD.begin(PIN_SD_CS, sdSpi);
  loadConfiguration();
  ensurePersistentIdentity();
  startNetworks(); registerRoutes(); server.begin();
  Serial.println("[ARGOS] UID : " + config.deviceUid);
  Serial.println("[ARGOS] API : " + (config.apiBaseUrl.isEmpty() ? String("non configurée") : config.apiBaseUrl));
  Serial.println("[ARGOS] Wi-Fi cible : " + (config.wifiSsid.isEmpty() ? String("non configuré") : config.wifiSsid));
  readSensors();
}

void loop() {
  dnsServer.processNextRequest();
  server.handleClient();
  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  uint32_t now = millis();
  static wl_status_t previousWifiStatus = WL_NO_SHIELD;
  wl_status_t currentWifiStatus = WiFi.status();
  if (currentWifiStatus != previousWifiStatus) {
    previousWifiStatus = currentWifiStatus;
    Serial.printf("[WIFI] État : %d\n", (int)currentWifiStatus);
    if (currentWifiStatus == WL_CONNECTED) {
      Serial.println("[WIFI] Connecté à " + WiFi.SSID());
      Serial.println("[WIFI] Adresse IP : " + WiFi.localIP().toString());
    }
  }
  if (now - lastSampleAt >= SAMPLE_INTERVAL_MS) { lastSampleAt = now; readSensors(); }
  if (WiFi.status() == WL_CONNECTED) {
    static bool ntpStarted = false;
    if (!ntpStarted) { configTime(0, 0, "pool.ntp.org", "time.google.com"); ntpStarted = true; }
    enrollIfNeeded();
    if (now - lastCommandPollAt >= COMMAND_POLL_INTERVAL_MS) {
      lastCommandPollAt = now;
      pollRemoteCommands();
    }
    if (now - lastRemoteSendAt >= REMOTE_SEND_INTERVAL_MS) { lastRemoteSendAt = now; sendRemoteTelemetry(); }
  } else if (!config.wifiSsid.isEmpty() && now - lastWifiRetryAt >= WIFI_RETRY_INTERVAL_MS) {
    lastWifiRetryAt = now; WiFi.disconnect(); WiFi.begin(config.wifiSsid.c_str(), config.wifiPassword.c_str());
  }
  delay(2);
}
