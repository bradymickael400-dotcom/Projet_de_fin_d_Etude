# Firmware ARGOS pour ESP32 38 broches

Ce sketch implémente les contrats déjà utilisés par l'application :

- point d'accès `ARGOS-SETUP-XXXXXX`, adresse `http://192.168.4.1` ;
- portail captif DNS ouvert automatiquement par Android, iOS, Windows et macOS ;
- création proposée uniquement tant qu'aucune boîte n'est enregistrée dans la mémoire NVS ;
- détection par `GET /api/device/info` ;
- mesures automatiques par `GET /api/v1/telemetry` ;
- configuration par `POST /api/v1/provision` ;
- activation de la sécurité par `POST /api/v1/security` ;
- en mode réseau, enrôlement, envoi à `/api/iot/telemetry`, récupération des
  commandes et accusés d'exécution.

## Installation

Dans Arduino IDE, sélectionner **ESP32 Dev Module**, puis installer : ArduinoJson,
DHT sensor library, TinyGPSPlus, Adafruit MPU6050, Adafruit BMP280 et Adafruit
Unified Sensor. Compiler et téléverser `argos_esp32.ino`.

Connecter ensuite l'ordinateur ou le téléphone au Wi-Fi
`ARGOS-SETUP-XXXXXX`. Ce point d'accès est volontairement ouvert, sans mot de
passe Wi-Fi ; les API de configuration restent protégées par la clé locale.
Le portail captif s'ouvre automatiquement et son bouton de connexion dirige
directement vers l'application locale `http://127.0.0.2:5002`. Lors de la
première utilisation, **Créer une nouvelle boîte** conduit à la connexion ARGOS
puis au formulaire de création. Après l'enregistrement permanent de l'UID, le
portail masque cette action et ne propose plus que la connexion. La clé locale
par défaut est `ARGOS-PROVISION-2026`.

## Points matériels importants

- Le HC-SR04 renvoie généralement 5 V sur ECHO : placer un pont diviseur vers
  GPIO16 (par exemple 1 kΩ + 2 kΩ) pour ne pas endommager l'ESP32 3,3 V.
- Le signal CS de la carte SD est placé sur GPIO33.
- Le DHT11 est placé sur GPIO19. Le GPS utilise RX=GPIO4 et TX=GPIO15.
- Le moniteur série fonctionne à 115200 bauds.
- La sortie numérique `DO` du module microphone est raccordée à GPIO22. Elle
  signale une activité sonore selon le seuil réglé sur le potentiomètre du
  module, mais ne transporte pas une forme d'onde audio.
- Le seuil d'ouverture par défaut du HC-SR04 est de 15 cm. Une transition de
  porte fermée vers porte ouverte, lorsque la sécurité est active, produit une
  alerte horodatée et géolocalisée et active les modes écoute/enregistrement.
- Les capteurs I²C attendus sont un MPU6050 (adresse 0x68) et, facultativement,
  un BMP280 (0x76/0x77). Sans BMP280, la pression est marquée comme estimée.

## Limite audio matérielle

La sortie numérique sur GPIO22 détecte un dépassement de seuil, mais ne fournit
pas d'échantillons audio. Pour enregistrer directement depuis le boîtier,
utiliser un microphone I2S (par exemple INMP441) avec une ligne DATA dédiée,
encoder les échantillons et les envoyer vers `/api/iot/audio`.

En mode direct, le bouton **Enregistrer** dans l'application peut
enregistrer le microphone de l'ordinateur de l'opérateur pendant cinq minutes.
Le navigateur demande obligatoirement son autorisation et affiche un indicateur
rouge pendant la capture. Le fichier est placé dans le stockage privé ARGOS,
associé à la boîte et lisible dans son historique par les comptes autorisés.
Cette API navigateur exige une page HTTPS (lien public Cloudflare) ou
`http://localhost`; une adresse LAN en HTTP n'est pas un contexte sécurisé pour
`getUserMedia` dans les navigateurs modernes.
