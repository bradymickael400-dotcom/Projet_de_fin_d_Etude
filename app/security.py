"""Authentification HTTP et autorisations centralisees pour ARGOS."""

from datetime import timedelta
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


PUBLIC_API_ENDPOINTS = {
    "auth.api_login",
    "auth.api_login_availability",
    "iot.api_enroll_device",
    "iot.api_iot_time",
    "iot.api_iot_telemetry",
    "telemetry.receive_telemetry",
    "iot.api_iot_acknowledgements",
    "iot.api_iot_audio",
    "iot.api_iot_device_commands",
    "users.register_iot_account",
    "boites_noires.captive_register_black_box",
    "boites_noires.captive_registration_options",
}


def _serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="argos-access-token-v1",
    )


def ensure_identity_registry(role, user_id, login, display_name=None, must_change_password=False):
    from sqlalchemy import text
    from app.extensions import db
    return db.session.execute(text("""
        INSERT INTO identity_registry
            (login_normalized, actor_role, actor_id, display_name, must_change_password)
        VALUES
            (LOWER(TRIM(:login)), :role, :uid, NULLIF(TRIM(:display_name), ''), :must_change_password)
        ON CONFLICT (actor_role, actor_id) DO UPDATE SET
            login_normalized = EXCLUDED.login_normalized,
            display_name = COALESCE(EXCLUDED.display_name, identity_registry.display_name),
            updated_at = NOW()
        RETURNING token_version
    """), {
        "role": str(role),
        "uid": str(user_id),
        "login": str(login),
        "display_name": str(display_name or login),
        "must_change_password": bool(must_change_password),
    }).scalar() or 1


def issue_access_token(role, user_id, login, display_name=None, access_scope="full"):
    token_version = ensure_identity_registry(role, user_id, login, display_name)
    return _serializer().dumps({
        "role": str(role),
        "user_id": str(user_id),
        "login": str(login),
        "display_name": str(display_name or login),
        "version": 1,
        "access_scope": access_scope,
        "token_version": int(token_version),
    })


def decode_access_token(token):
    max_age = int(current_app.config.get("AUTH_TOKEN_MAX_AGE_SECONDS", 28800))
    return _serializer().loads(token, max_age=max_age)


def _bearer_token():
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()

    header_token = (request.headers.get("X-Access-Token", "") or request.headers.get("X-Auth-Token", "") or "").strip()
    if header_token:
        return header_token

    return ""


def authenticate_request():
    """Charge une identite signee; les en-tetes X-Role/X-User-Id sont ignores."""
    g.argos_identity = None
    token = _bearer_token()
    if not token:
        return None
    try:
        identity = decode_access_token(token)
    except (BadSignature, SignatureExpired):
        return None
    if not identity.get("role") or not identity.get("user_id"):
        return None
    try:
        from sqlalchemy import text
        from app.extensions import db
        registry = db.session.execute(text("""
            SELECT token_version,disabled_at FROM identity_registry
            WHERE actor_role=:role AND actor_id=:uid
        """), {"role":identity["role"],"uid":identity["user_id"]}).fetchone()
        if not registry or registry.disabled_at or int(registry.token_version) != int(identity.get("token_version", 0)):
            return None
    except Exception:
        db.session.rollback()
        return None
    g.argos_identity = identity
    return identity


def enforce_api_authentication():
    """Politique deny-by-default pour toutes les routes /api/."""
    if request.method == "OPTIONS" or not request.path.startswith("/api/"):
        return None
    if request.endpoint in PUBLIC_API_ENDPOINTS:
        return None
    identity = authenticate_request()
    if identity:
        if identity.get("access_scope") == "contract_pending" and request.endpoint not in {
            "workflows.pending_contract",
            "workflows.contract_document",
            "workflows.decide_contract",
            "auth.api_change_password",
        }:
            return jsonify({
                "error": "Acceptation du contrat requise avant l'acces a la plateforme",
                "code": "CONTRACT_ACCEPTANCE_REQUIRED",
            }), 403
        return None
    return jsonify({
        "status": "error",
        "error": "Authentification requise ou session expiree",
        "code": "AUTH_REQUIRED",
    }), 401


def current_identity():
    identity = getattr(g, "argos_identity", None)
    if identity is None:
        identity = authenticate_request()
    return identity or {}


def roles_required(*allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            identity = current_identity()
            if not identity:
                return jsonify({"error": "Authentification requise"}), 401
            if identity.get("role") not in allowed_roles:
                return jsonify({"error": "Acces refuse"}), 403
            return func(*args, **kwargs)
        return wrapped
    return decorator
