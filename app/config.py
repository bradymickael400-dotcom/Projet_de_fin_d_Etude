# utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # charge les variables depuis .env

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/mydb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False