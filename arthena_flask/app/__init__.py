"""Application factory Arthena."""
import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, cors


def create_app(config_name="development"):
    if config_name not in config_by_name:
        raise ValueError(f"Configuration inconnue: {config_name}")
    config_class = config_by_name[config_name]
    if config_name == "production":
        config_class.validate()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # --- Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    if app.config["ALLOWED_ORIGINS"]:
        cors.init_app(app, resources={r"/api/*": {"origins": app.config["ALLOWED_ORIGINS"]}})

    # --- Modèles (import nécessaire pour Flask-Migrate) ---
    from app.models import user, school, student, teacher, academic, requests as req_models, payment, notification, news  # noqa

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(user.User, int(user_id))
        except (TypeError, ValueError):
            return None

    # --- Blueprints ---
    from app.auth import auth_bp
    from app.parent import parent_bp
    from app.teacher import teacher_bp
    from app.school_admin import school_admin_bp
    from app.superadmin import superadmin_bp
    from app.api import api_bp
    from app.news import news_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(parent_bp, url_prefix="/parent")
    app.register_blueprint(teacher_bp, url_prefix="/enseignant")
    app.register_blueprint(school_admin_bp, url_prefix="/ecole")
    app.register_blueprint(superadmin_bp, url_prefix="/superadmin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(news_bp)

    # --- Gestion d'erreurs ---
    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # --- CLI custom (seed, etc.) ---
    from app.utils.cli import register_cli
    register_cli(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(self), payment=(self)",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if config_name == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    return app
