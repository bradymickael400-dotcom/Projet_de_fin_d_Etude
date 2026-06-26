# utils/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env depuis la racine du projet
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/mydb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ── Google Gemini IA ──
    API_KEY = os.getenv('API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'models/gemini-2.5-flash')
    
    # ── SMTP (optionnel) ──
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

    # ── BIC BoxTech / Maritime Tracking ──
    BIC_CLIENT_ID = os.getenv('BIC_CLIENT_ID', '')
    BIC_CLIENT_SECRET = os.getenv('BIC_CLIENT_SECRET', '')
    MARITIME_PROVIDER = os.getenv('MARITIME_PROVIDER', 'vizion')
    VIZION_API_KEY = os.getenv('VIZION_API_KEY', '')
    MT_API_KEY = os.getenv('MT_API_KEY', '')
