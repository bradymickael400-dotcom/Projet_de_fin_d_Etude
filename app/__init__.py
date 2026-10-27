"""Point d’entrée principal de l’application Flask ARGOS.

Ce module crée l’application, initialise les extensions partagées et
registre les blueprints métier qui exposent les routes API.
"""

import os
from flask import Flask
from flask_cors import CORS

# Instance unique de SQLAlchemy (définie dans extensions.py)
from app.extensions import db
from app.config import Config
# Helpers de la blockchain — source unique de vérité dans app.utils
from app.utils import init_blockchain, seal_block  # noqa: F401  (réexportés pour `from app import db, seal_block`)

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    # L'interface actualise plusieurs ressources en parallèle et peut
    # effectuer plusieurs cycles de synchronisation par minute. Une limite
    # globale trop basse (200/jour) bloquait le tableau de bord en 429.
    limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute", "5000/day"])
except Exception:
    class _NoopLimiter:
        def init_app(self, app):
            return None

        def limit(self, *_args, **_kwargs):
            def decorator(func):
                return func
            return decorator

    limiter = _NoopLimiter()


def create_app():
    Config.validate()
    app = Flask(__name__)
    app.config.from_object(Config)
    schema = os.getenv("DB_SCHEMA", "brady")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 2400,
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
            "options": f"-csearch_path={schema},public",
        },
    }

    # ── 2. CORS (dev permissif sur /api/*) ────────────────────────────
    CORS(app, resources={r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Role", "X-User-Id", "X-Device-Key"],
    }})

    # ── 3. Extensions ─────────────────────────────────────────────────
    db.init_app(app)
    limiter.init_app(app)

    from app.security import enforce_api_authentication
    app.before_request(enforce_api_authentication)

    # ── 4. Blueprints (source canonique des routes) ───────────────────
    from app.routes.auth import auth_bp
    from app.routes.containers import cnt_bp
    from app.routes.telemetry import tel_bp
    from app.routes.dashboard import dash_bp
    from app.routes.blockchain import blockchain_bp
    from app.routes.users import users_bp
    from app.routes.publications import pub_bp
    from app.routes.maritime import maritime_bp
    from app.routes.boites_noires import bn_bp
    from app.routes.black_boxes import bb_bp
    from app.modules.iot import iot_bp
    from app.routes.workflows import workflow_bp
    from app.routes.regulatory import regulatory_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(cnt_bp)
    app.register_blueprint(tel_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(blockchain_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(pub_bp)
    app.register_blueprint(maritime_bp)
    app.register_blueprint(bn_bp)
    app.register_blueprint(bb_bp)
    app.register_blueprint(iot_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(regulatory_bp)

    # ── 5. Initialisation paresseuse de la blockchain (une seule fois) ─
    @app.before_request
    def _setup_db_once():
        if not getattr(app, "db_initialized", False):
            try:
                init_blockchain()
            except Exception:
                pass
            app.db_initialized = True  # type: ignore[attr-defined]

    return app
