# app/extensions.py
# Définit les extensions Flask (instanciées une seule fois ici)

from flask_sqlalchemy import SQLAlchemy

# **Instance unique** de SQLAlchemy partagée dans toute l'application
db = SQLAlchemy()


