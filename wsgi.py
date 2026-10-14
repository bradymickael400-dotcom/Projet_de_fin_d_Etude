"""Point d'entree WSGI de production ARGOS."""

from app import create_app

app = create_app()
