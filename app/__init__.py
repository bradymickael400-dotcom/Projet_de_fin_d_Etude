from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'Argos_direction_generale2026'
    CORS(app, supports_credentials=True)

    # Importer et enregistrer les routes
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app
