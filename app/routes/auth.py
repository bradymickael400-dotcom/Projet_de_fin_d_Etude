"""Routes d’authentification et de connexion utilisateur."""

from flask import Blueprint, current_app, request, jsonify
from sqlalchemy import text # type: ignore
from werkzeug.security import check_password_hash, generate_password_hash
from app import db, limiter
from app.security import current_identity, issue_access_token

auth_bp = Blueprint("auth", __name__)


LOGIN_SOURCES = [
    ("superadmin", "id", "login"),
    ("proprietaire_conteneur", "id", "login"),
    ("client", "id_cni", "login"),
    ("transporteur", "id_cni", "login"),
    ("agence_utilisatrice", "niu", "login"),
    ("port_authority_user", "id", "login"),
]


def _login_exists(login):
    if not login:
        return False
    for table_name, _id_col, login_col in LOGIN_SOURCES:
        try:
            found = db.session.execute(text(
                f"SELECT 1 FROM {table_name} WHERE LOWER({login_col}) = LOWER(:login) LIMIT 1"
            ), {"login": login}).fetchone()
            if found:
                return True
        except Exception:
            db.session.rollback()
    return False


def _login_suggestions(login):
    base = "".join(ch if ch.isalnum() or ch in "._-" else "." for ch in (login or "argos.user").lower()).strip(".")
    base = base or "argos.user"
    candidates = [base, f"{base}2", f"{base}.argos", f"{base}.{datetime_suffix()}"]
    available = []
    for candidate in candidates:
        if candidate not in available and not _login_exists(candidate):
            available.append(candidate)
    suffix = 3
    while len(available) < 4 and suffix < 100:
        candidate = f"{base}{suffix}"
        if not _login_exists(candidate):
            available.append(candidate)
        suffix += 1
    return available


def datetime_suffix():
    from datetime import datetime
    return datetime.utcnow().strftime("%m%d")


@auth_bp.route("/api/auth/login-availability", methods=["GET"])
def api_login_availability():
    login = (request.args.get("login") or "").strip()
    if not login:
        return jsonify({"available": False, "error": "Login requis", "suggestions": _login_suggestions("argos.user")}), 400
    exists = _login_exists(login)
    return jsonify({
        "login": login,
        "available": not exists,
        "suggestions": [] if not exists else _login_suggestions(login),
    }), 200


@auth_bp.route("/api/auth/change-password", methods=["POST"])
def api_change_password():
    identity = current_identity()
    role = str(identity.get("role", ""))
    user_id = str(identity.get("user_id", ""))
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or data.get("currentPassword") or ""
    new_password = data.get("new_password") or data.get("newPassword") or ""
    if not role or not user_id:
        return jsonify({"error": "Authentification requise"}), 401
    if len(new_password) < 8:
        return jsonify({"error": "Le nouveau mot de passe doit contenir au moins 8 caractères"}), 400

    table_by_role = {
        "superadmin": ("superadmin", "id"),
        "owner": ("proprietaire_conteneur", "id"),
        "client": ("client", "id_cni"),
        "driver": ("transporteur", "id_cni"),
        "company": ("agence_utilisatrice", "niu"),
        "port_authority": ("port_authority_user", "id"),
    }
    table_info = table_by_role.get(role)
    if not table_info:
        return jsonify({"error": "Rôle inconnu"}), 403
    table_name, id_col = table_info
    try:
        row = db.session.execute(text(
            f"SELECT password FROM {table_name} WHERE CAST({id_col} AS TEXT) = :uid LIMIT 1"
        ), {"uid": str(user_id)}).fetchone()
        if not row or not check_password_hash(row.password, current_password):
            return jsonify({"error": "Mot de passe actuel incorrect"}), 403
        db.session.execute(text(
            f"UPDATE {table_name} SET password = :password WHERE CAST({id_col} AS TEXT) = :uid"
        ), {"password": generate_password_hash(new_password), "uid": str(user_id)})
        db.session.execute(text("""
            UPDATE identity_registry SET token_version=token_version+1,updated_at=NOW()
            WHERE actor_role=:role AND actor_id=:uid
        """), {"role":role,"uid":str(user_id)})
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur changement mot de passe: {str(e)}"}), 500

# ═══════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════
@auth_bp.route("/api/login", methods=["POST", "OPTIONS"])
@limiter.limit("10/minute")
def api_login():
    if request.method == "OPTIONS":
        return jsonify({"status": "CORS_OK"}), 200
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données JSON manquantes"}), 400

        username = (data.get("username") or data.get("login") or "").strip()
        password = (data.get("password") or "").strip()

        if not username or not password:
            return jsonify({"error": "Login et mot de passe requis"}), 400

        auth_rules = [
            ("superadmin", "id", "superadmin", ["login"]),
            ("proprietaire_conteneur", "id", "owner", ["login", "niu"]),
            ("client", "id_cni", "client", ["login", "id_cni"]),
            ("transporteur", "id_cni", "driver", ["login", "id_cni"]),
            ("agence_utilisatrice", "niu", "company", ["login", "niu"]),
            ("port_authority_user", "id", "port_authority", ["login"]),
        ]

        def verify_password(raw_password, stored_password):
            if not stored_password:
                return False
            try:
                return check_password_hash(stored_password, raw_password)
            except Exception:
                return False

        for table_name, id_col, role, fields in auth_rules:
            try:
                clause = " OR ".join([f"{field} = :u" for field in fields])
                name_columns = {
                    "superadmin": "login",
                    "proprietaire_conteneur": "COALESCE(nom_agence, login)",
                    "client": "TRIM(COALESCE(prenom, '') || ' ' || COALESCE(nom, ''))",
                    "transporteur": "COALESCE(nom_chauffeurs, login)",
                    "agence_utilisatrice": "COALESCE(nom_agence, login)",
                    "port_authority_user": "login",
                }
                display_expr = name_columns.get(table_name, "login")
                query = text(f"SELECT {id_col}, password, {display_expr} AS display_name FROM {table_name} WHERE {clause} LIMIT 1")
                user = db.session.execute(query, {"u": username}).fetchone()
                if user and verify_password(password, user[1]):
                    requires_contract = False
                    if role == "owner":
                        try:
                            requires_contract = bool(db.session.execute(text("""
                                SELECT 1 FROM contracts
                                WHERE company_id=:company AND status='PENDING_ACCEPTANCE' LIMIT 1
                            """), {"company": str(user[0])}).scalar())
                        except Exception:
                            db.session.rollback()
                    scope = "contract_pending" if requires_contract else "full"
                    access_token = issue_access_token(role, user[0], username, user[2], scope)
                    db.session.commit()
                    return jsonify({
                        "status": "success",
                        "role": role,
                        "username": username,
                        "user_id": str(user[0]),
                        "display_name": user[2] or username,
                        "access_token": access_token,
                        "token_type": "Bearer",
                        "expires_in": current_app.config.get("AUTH_TOKEN_MAX_AGE_SECONDS", 28800),
                        "requires_contract_acceptance": requires_contract,
                    }), 200
            except Exception:
                db.session.rollback()
                continue

        return jsonify({"error": "Identifiants incorrects ou compte inexistant."}), 401

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"error": "Erreur interne du serveur."}), 500
