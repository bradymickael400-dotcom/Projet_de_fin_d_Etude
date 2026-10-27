"""Point d'entrée WSGI pour la production (gunicorn wsgi:app)."""
import os
from app import create_app

app = create_app(os.getenv("FLASK_CONFIG", "production"))
