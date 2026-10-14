"""Extensions Flask partagées par l’application.

Les objets instanciés ici doivent être utilisés comme singletons afin
d’éviter d’ouvrir plusieurs connexions SQLAlchemy indépendantes.
"""

from flask_sqlalchemy import SQLAlchemy

# Instance unique de SQLAlchemy partagée dans toute l'application.
db = SQLAlchemy()


