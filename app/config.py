"""Configuration centralisée de l’application ARGOS.

Les variables d’environnement sont chargées ici pour fournir les paramètres
communs utilisés par Flask, la base de données et les intégrations externes.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def _default_database_url():
    env_url = os.getenv('DATABASE_URL', '').strip()
    if env_url:
        return env_url
    docker_url = os.getenv('DOCKER_DATABASE_URL', '').strip()
    if docker_url:
        return docker_url
    return 'postgresql://brady:brady123@localhost:5432/argos'

# Charger le .env depuis la racine du projet
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    AUTH_TOKEN_MAX_AGE_SECONDS = int(os.getenv('AUTH_TOKEN_MAX_AGE_SECONDS', '28800'))
    SQLALCHEMY_DATABASE_URI = _default_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ── Google Gemini IA ──
    API_KEY = os.getenv('API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'models/gemini-2.5-flash')
    GEMINI_API_BASE_URL = os.getenv('GEMINI_API_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
    KNOWLEDGE_BASE_PATH = os.getenv('KNOWLEDGE_BASE_PATH', '').strip()
    
    # ── Notifications email / WhatsApp ──
    NOTIFICATION_PROVIDER = os.getenv('NOTIFICATION_PROVIDER', 'smtp').strip().lower()

    # Infobip HTTP API. INFOBIP_BASE_URL doit ressembler a:
    # https://xxxxx.api.infobip.com
    INFOBIP_BASE_URL = os.getenv('INFOBIP_BASE_URL', '').strip()
    INFOBIP_API_KEY = os.getenv('INFOBIP_API_KEY', '').strip()
    INFOBIP_EMAIL_FROM = os.getenv('INFOBIP_EMAIL_FROM', '').strip()
    INFOBIP_EMAIL_FROM_NAME = os.getenv('INFOBIP_EMAIL_FROM_NAME', 'ARGOS Alertes').strip()
    INFOBIP_WHATSAPP_SENDER = os.getenv('INFOBIP_WHATSAPP_SENDER', '').strip()

    # ── SMTP historique (fallback optionnel) ──
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL') or os.getenv('SMTP_USER', '')

    # ── WhatsApp / notifications ──
    WHATSAPP_DEFAULT_RECIPIENT = os.getenv('WHATSAPP_DEFAULT_RECIPIENT', '')

    # ── BIC BoxTech / Maritime Tracking ──
    # BoxTech nomme ces valeurs username/password (Basic Auth). Les anciens noms
    # restent acceptes pour ne pas casser les installations existantes.
    BIC_CLIENT_ID = os.getenv('BIC_USERNAME') or os.getenv('BIC_CLIENT_ID', '')
    BIC_CLIENT_SECRET = os.getenv('BIC_PASSWORD') or os.getenv('BIC_CLIENT_SECRET', '')
    MARITIME_PROVIDER = os.getenv('MARITIME_PROVIDER', 'vizion')
    VIZION_API_KEY = os.getenv('VIZION_API_KEY', '')
    MT_API_KEY = os.getenv('MT_API_KEY', '')

    # ── IoT / ESP32 ──
    IOT_TRANSPORT = os.getenv('IOT_TRANSPORT', 'mock')
    MQTT_BROKER_URL = os.getenv('MQTT_BROKER_URL', '')
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
    MQTT_CA_CERT_PATH = os.getenv('MQTT_CA_CERT_PATH', '')
    IOT_HTTP_SHARED_ENDPOINT = os.getenv('IOT_HTTP_SHARED_ENDPOINT', '')
    IOT_COMMAND_TTL_SECONDS = int(os.getenv('IOT_COMMAND_TTL_SECONDS', '120'))
    IOT_RAW_LOG_ENABLED = os.getenv('IOT_RAW_LOG_ENABLED', 'true').lower() == 'true'
    PRIVATE_STORAGE_PATH = os.getenv('PRIVATE_STORAGE_PATH', '')
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').strip()
    NOTIFICATION_ARCHIVE_AFTER_HOURS = int(os.getenv('NOTIFICATION_ARCHIVE_AFTER_HOURS', '168'))
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    IOT_REDIS_URL = os.getenv('IOT_REDIS_URL', '').strip()
    IOT_REDIS_REQUIRED = os.getenv('IOT_REDIS_REQUIRED', 'false').lower() == 'true'
    IOT_ONLINE_WINDOW_SECONDS = int(os.getenv('IOT_ONLINE_WINDOW_SECONDS', '120'))
    MAX_AUDIO_BYTES = int(os.getenv('MAX_AUDIO_BYTES', str(25 * 1024 * 1024)))

    @classmethod
    def validate(cls):
        environment = os.getenv("APP_ENV", "development").lower()
        if environment == "production" and cls.SECRET_KEY in ("", "dev", "change-me"):
            raise RuntimeError("SECRET_KEY robuste obligatoire en production")
