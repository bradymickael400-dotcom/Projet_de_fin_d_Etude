from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy.ext.automap import automap_base

db = SQLAlchemy()
Base = automap_base()


def init_automap(app):
    # Envelopper la préparation de l'automap dans le contexte de l'application
    with app.app_context():
        # ENLEVER LES PARENTHÈSES ICI : db.engine et non db.engine() 💡
        engine = db.engine

        # Prépare les modèles à partir de la base de données 
        Base.prepare(autoload_with=engine)
        
        # Importer les classes automap dans le contexte de l'application
        app.config['AUTOMAP_CLASSES'] = Base.classes


def create_app():
    app = Flask(__name__)
    
    # 1. Configurations de base
    app.config['SECRET_KEY'] = 'Argos_direction_generale2026'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://brady:argos%401234@localhost:5432/argos'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 2. Options de l'Engine (Doivent être définies ICI dans app.config)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 2400,       # Recycle la connexion après 40 minutes
        "connect_args": {
            "keepalives": 1,        # Active les keepalives TCP
            "keepalives_idle": 30,  # Envoie un keepalive après 30 secondes d'inactivité
            "keepalives_interval": 5, # Puis envoie toutes les 5 secondes
            "keepalives_count": 5,   # Après 5 échecs, abandonne
        }
    }
    
    # 3. Configuration CORS globale et permissive pour le développement
    # On autorise explicitement les méthodes POST, GET, OPTIONS et les en-têtes de contenu
    CORS(app, resources={r"/api/*": {
        "origins": "*", 
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }})
    
    # 4. Initialisation des composants
    db.init_app(app)
    init_automap(app)

    # 5. Importer et enregistrer les routes
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
# À insérer dans create_app() juste avant le "return app"
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    return app

