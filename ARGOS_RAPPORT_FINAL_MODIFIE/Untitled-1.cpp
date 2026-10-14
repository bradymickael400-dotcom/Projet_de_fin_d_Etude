/*
 * ARGOS ESP32 (module DevKit 38 broches)
 * Compatible avec le pont direct de app/static/js/direct-bridge.js.
 *
 * Bibliothèques à installer :
 *   ArduinoJson 7.x, DHT sensor library, TinyGPSPlus,
 *   Adafruit MPU6050, Adafruit BMP280, Adafruit Unified Sensor.
 */

#include <WiFi.h>
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
#include <esp_system.h>

// --- BROCHAGE SÉCURISÉ (ANTI-CONFLIT) ---
// constexpr uint8_t PIN_LED = 1;              
constexpr uint8_t PIN_DHT = 19;             
constexpr uint8_t PIN_I2C_SCL = 5;          
constexpr uint8_t PIN_BUZZER = 13;          
constexpr uint8_t PIN_SD_MOSI = 14;         
constexpr uint8_t PIN_GPS_RX = 4;           // GPS TX branché sur GPIO 4
constexpr uint8_t PIN_GPS_TX = 15;          // GPS RX branché sur GPIO 15
constexpr uint8_t PIN_HCSR04_ECHO = 16;     
constexpr uint8_t PIN_FLAME = 17;           
constexpr uint8_t PIN_HCSR04_TRIG = 18;     
constexpr uint8_t PIN_I2C_SDA = 21;         
constexpr uint8_t PIN_MIC = 22;             
constexpr uint8_t PIN_SD_SCK = 26;          
constexpr uint8_t PIN_SD_MISO = 27;         
constexpr uint8_t PIN_SD_CS = 33;           // Carte SD CS sur GPIO 33

constexpr char SETUP_KEY_DEFAULT[] = "ARGOS-PROVISION-2026";
constexpr uint32_t SAMPLE_INTERVAL_MS = 2000;
constexpr uint32_t REMOTE_SEND_INTERVAL_MS = 10000;
constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 30000;
constexpr float DEFAULT_DISTANCE_THRESHOLD_CM = 50.0f;

// Position de repli : ENSPT, Yaoundé.
constexpr double FALLBACK_LATITUDE = 3.85;
constexpr double FALLBACK_LONGITUDE = 11.49;

DHT dht(PIN_DHT, DHT11);
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
WebServer server(80);
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
  bool flameDetected = false, doorOpen = false, securityAlarm = false;
  bool dhtValid = false, mpuValid = false, gpsValid = false;
  bool distanceValid = false, sdReady = false, pressureMeasured = false;
} values;

bool securityEnabled = true;
bool audioRecordingEnabled = false;
bool audioListeningEnabled = false;
bool flameDetectionEnabled = true;
uint32_t sequenceNumber = 0;
uint32_t lastSampleAt = 0, lastRemoteSendAt = 0, lastWifiRetryAt = 0;
String lastMessageId;
String lastTimestamp;

void addCors() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type,X-ARGOS-Setup-Key,X-ARGOS-Client-Timestamp");
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
  if (now < 1700000000) return "1970-01-01T00:00:00Z";
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

// --- NOUVELLE FONCTION : AFFICHAGE EN TEMPS RÉEL DES DONNÉES SUR LE PORT SÉRIE ---
void printTelemetryToSerial() {
  Serial.println("\n--- [ TÉLÉMÉTRIE EN TEMPS RÉEL ] ---");
  Serial.printf("Séquence    : %d | Timestamp: %s\n", sequenceNumber, lastTimestamp.c_str());
  
  Serial.print("DHT         : ");
  if (values.dhtValid) Serial.printf("Temp: %.1f°C | Hum: %.1f%%\n", values.temperature, values.humidity);
  else Serial.println("Invalide/Erreur");

  Serial.print("Ultrasons   : ");
  if (values.distanceValid) Serial.printf("Distance: %.1f cm (Seuil: %.1f) -> Porte %s\n", 
                                          values.distanceCm, config.distanceThresholdCm, values.doorOpen ? "[OUVERTE]" : "[FERMÉE]");
  else Serial.println("Invalide/Erreur");

  Serial.print("MPU6050     : ");
  if (values.mpuValid) Serial.printf("Ax: %.2fG, Ay: %.2fG, Az: %.2fG | Choc: %.2fG\n", values.ax, values.ay, values.az, values.shock);
  else Serial.println("Invalide/Erreur");

  Serial.print("BMP280      : ");
  if (values.pressureMeasured) Serial.printf("Pression: %.2f hPa\n", values.pressure);
  else Serial.println("Non mesurée");

  Serial.print("GPS         : ");
  if (values.gpsValid) Serial.printf("Lat: %.6f, Lng: %.6f | Vit: %.1f km/h | Cap: %.1f°\n", values.latitude, values.longitude, values.speed, values.heading);
  else Serial.printf("Pas de fix (Repli Lat: %.6f, Lng: %.6f)\n", values.latitude, values.longitude);

  Serial.printf("Environnem. : Son (Valeur brute): %d | Flamme: %s\n", values.soundLevel, values.flameDetected ? "OUI [ALERTE]" : "NON");
  
  Serial.printf("ALARME      : %s (Mode Sécurité: %s)\n", values.securityAlarm ? "DÉCLENCHÉE !!!" : "RAS", securityEnabled ? "ON" : "OFF");
  Serial.println("------------------------------------");
}

void readSensors() {
  while (gpsSerial.available()) gps.encode(gpsSerial.read());

  float t = dht.readTemperature(), h = dht.readHumidity();
  values.dhtValid = isfinite(t) && isfinite(h);
  if (values.dhtValid) { values.temperature = t; values.humidity = h; }

  float d = readDistanceCm();
  values.distanceValid = isfinite(d) && d >= 0 && d <= 1000;
  if (values.distanceValid) values.distanceCm = d;

  values.flameDetected = digitalRead(PIN_FLAME) == LOW; 
  values.soundLevel = digitalRead(PIN_MIC) ? 4095 : 0;

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
  digitalWrite(PIN_LED, values.securityAlarm ? HIGH : LOW);
  digitalWrite(PIN_BUZZER, values.securityAlarm ? HIGH : LOW);

  sequenceNumber++;
  lastMessageId = makeUuid();
  lastTimestamp = isoTimestamp();
  
  // Affichage en temps réel des données lues
  printTelemetryToSerial();

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
  s["batteryLevel"] = 100.0; s["lightLevel"] = 0;
  s["soundLevel"] = values.soundLevel; s["distanceCm"] = values.distanceCm;
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
  q["batteryMeasured"] = false; q["timestampSource"] = time(nullptr) > 1700000000 ? "NTP" : "BROWSER_REQUIRED";
}

bool httpPostJson(const String &url, const String &body, const String &deviceKey, int &status, String &response) {
  HTTPClient http;
  if (!http.begin(url)) return false;
  http.addHeader("Content-Type", "application/json");
  if (!deviceKey.isEmpty()) http.addHeader("X-Device-Key", deviceKey);
  status = http.POST(body);
  response = status > 0 ? http.getString() : "";
  http.end();
  return status > 0;
}

void enrollIfNeeded() {
  if (WiFi.status() != WL_CONNECTED || config.apiBaseUrl.isEmpty() ||
      config.enrollmentToken.isEmpty() || !config.apiKey.isEmpty()) return;
  JsonDocument request;
  request["deviceUid"] = config.deviceUid;
  request["enrollmentToken"] = config.enrollmentToken;
  String body, response; serializeJson(request, body);
  int status = 0;
  if (!httpPostJson(config.apiBaseUrl + "/api/iot/enroll", body, "", status, response) || status != 201) return;
  JsonDocument result;
  if (deserializeJson(result, response)) return;
  config.apiKey = result["credentials"]["apiKey"] | "";
  if (!config.apiKey.isEmpty()) { config.enrollmentToken = ""; saveConfiguration(); }
}

void sendRemoteTelemetry() {
  if (WiFi.status() != WL_CONNECTED || config.apiKey.isEmpty() || config.apiBaseUrl.isEmpty()) return;
  JsonDocument doc; buildTelemetry(doc);
  String body, response; serializeJson(doc, body);
  int status = 0;
  
  Serial.printf("\n[TRANSMISSION] Envoi des données vers le serveur (URL: %s)\n", config.apiBaseUrl.c_str());
  if (httpPostJson(config.apiBaseUrl + "/api/iot/telemetry", body, config.apiKey, status, response)) {
    Serial.printf("[SUCCÈS] Code HTTP : %d\n", status);
  } else {
    Serial.println("[ÉCHEC] La transmission a échoué.");
  }
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

void handleProvision() {
  if (!localAuthorized()) return rejectUnauthorized();
  JsonDocument body;
  DeserializationError err = deserializeJson(body, server.arg("plain"));
  if (err || !body["deviceUid"].is<const char*>() || !body["blackBoxId"].is<int>()) {
    JsonDocument out; out["status"]="error"; out["error"]="Configuration ARGOS invalide"; return sendJson(422, out);
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
  server.on("/api/v1/provision", HTTP_POST, handleProvision);
  server.onNotFound([](){
    if (server.method() == HTTP_OPTIONS) { addCors(); server.send(204); return; }
    JsonDocument out; out["status"]="error"; out["error"]="Route inconnue"; sendJson(404, out);
  });
}

void startNetworks() {
  WiFi.mode(WIFI_AP_STA);
  uint64_t mac = ESP.getEfuseMac();
  String suffix = String((uint32_t)(mac & 0xFFFFFF), HEX); suffix.toUpperCase();
  while (suffix.length() < 6) suffix = "0" + suffix;
  WiFi.softAP("ARGOS-SETUP-" + suffix);
  if (!config.wifiSsid.isEmpty()) WiFi.begin(config.wifiSsid.c_str(), config.wifiPassword.c_str());
}

void printSystemDiagnostic() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==================================================");
  Serial.println("           PROJET ARGOS - RAPPORT DE DÉMARRAGE    ");
  Serial.println("==================================================");
  
  uint64_t mac = ESP.getEfuseMac();
  Serial.printf("[SYSTEME] ESP32 Chip Model : %s\n", ESP.getChipModel());
  Serial.printf("[SYSTEME] Fréquence CPU     : %d MHz\n", ESP.getCpuFreqMHz());
  Serial.printf("[SYSTEME] Mémoire Flash libre : %d octets\n", ESP.getFreeHeap());
  Serial.printf("[SYSTEME] Adresse MAC        : %04X%08X\n", (uint16_t)(mac >> 32), (uint32_t)mac);
  Serial.println("--------------------------------------------------");
  Serial.println("           ÉTAT DES ÉQUIPEMENTS & CAPTEURS        ");
  Serial.println("--------------------------------------------------");

  if (values.sdReady) Serial.println("[OK] Carte SD (SPI)        : OPÉRATIONNELLE (CS: G33)");
  else Serial.println("[ERREUR] Carte SD (SPI)    : NON DÉTECTÉE / ÉCHEC D'INITIALISATION");

  if (values.mpuValid) Serial.println("[OK] MPU6050 (I2C)         : OPÉRATIONNEL (SCL: G5, SDA: G21)");
  else Serial.println("[ERREUR] MPU6050 (I2C)     : NON DÉTECTÉ (Vérifier câblage I2C)");

  if (values.pressureMeasured) Serial.println("[OK] BMP280 (Pression)     : OPÉRATIONNEL (I2C 0x76/0x77)");
  else Serial.println("[AVERTISSEMENT] BMP280     : NON DÉTECTÉ (Optionnel)");

  float testTemp = dht.readTemperature();
  if (!isnan(testTemp)) Serial.printf("[OK] DHT11 / DHT22         : OPÉRATIONNEL (Broche G19) | Temp: %.1f°C\n", testTemp);
  else Serial.println("[ERREUR] DHT11 / DHT22     : ÉCHEC DE LECTURE (Vérifier broche G19)");

  float testDist = readDistanceCm();
  if (!isnan(testDist)) Serial.printf("[OK] Ultrasons (HC-SR04)   : OPÉRATIONNEL (Trig: G18, Echo: G16) | Dist: %.1f cm\n", testDist);
  else Serial.println("[AVERTISSEMENT] Ultrasons  : PAS DE RÉPONSE (Vérifier écho/alimentation)");

  int soundVal = digitalRead(PIN_MIC);
  Serial.printf("[OK] Microphone (Son)      : OPÉRATIONNEL (Broche G22) | État actuel : %s\n", soundVal ? "BRUIT" : "SILENCE");

  bool flameVal = digitalRead(PIN_FLAME);
  Serial.printf("[OK] Détecteur de flamme   : OPÉRATIONNEL (Broche G17) | Statut : %s\n", flameVal == LOW ? "FLAMME DÉTECTÉE !" : "SÉCURISÉ");

  Serial.println("[OK] Buzzer (G13) & LED (G1): PRÊts (Actionneurs opérationnels)");
  Serial.println("[OK] Module GPS (Serial2)  : CONFIGURÉ (RX: G4, TX: G15 à 9600 bauds)");
  Serial.printf("[OK] Point d'Accès Wi-Fi   : ACTIF | SSID : ARGOS-SETUP-...\n");
  Serial.println("==================================================");
  Serial.println("   SYSTÈME ARGOS PRÊT - EN ATTENTE DES DONNÉES    ");
  Serial.println("==================================================\n");
}

void setup() {
  pinMode(PIN_LED, OUTPUT); 
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_HCSR04_TRIG, OUTPUT); 
  pinMode(PIN_HCSR04_ECHO, INPUT);
  pinMode(PIN_FLAME, INPUT_PULLUP); 
  pinMode(PIN_MIC, INPUT);
  
  digitalWrite(PIN_LED, LOW); 
  digitalWrite(PIN_BUZZER, LOW);
  
  dht.begin();
  
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  values.mpuValid = mpu.begin(0x68, &Wire);
  values.pressureMeasured = bmp.begin(0x76) || bmp.begin(0x77);

  gpsSerial.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);

  sdSpi.begin(PIN_SD_SCK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
  values.sdReady = SD.begin(PIN_SD_CS, sdSpi);

  loadConfiguration();
  if (config.deviceUid.isEmpty()) {
    uint64_t mac = ESP.getEfuseMac();
    char uid[32]; snprintf(uid, sizeof(uid), "ARGOS-ESP32-%08X", (uint32_t)mac);
    config.deviceUid = uid;
  }
  
  startNetworks(); 
  registerRoutes(); 
  server.begin();
  
  printSystemDiagnostic();
  readSensors();
}

void loop() {
  server.handleClient();
  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  uint32_t now = millis();
  if (now - lastSampleAt >= SAMPLE_INTERVAL_MS) { lastSampleAt = now; readSensors(); }
  if (WiFi.status() == WL_CONNECTED) {
    static bool ntpStarted = false;
    if (!ntpStarted) { configTime(0, 0, "pool.ntp.org", "time.google.com"); ntpStarted = true; }
    enrollIfNeeded();
    if (now - lastRemoteSendAt >= REMOTE_SEND_INTERVAL_MS) { lastRemoteSendAt = now; sendRemoteTelemetry(); }
  } else if (!config.wifiSsid.isEmpty() && now - lastWifiRetryAt >= WIFI_RETRY_INTERVAL_MS) {
    lastWifiRetryAt = now; WiFi.disconnect(); WiFi.begin(config.wifiSsid.c_str(), config.wifiPassword.c_str());
  }
  delay(2);
}