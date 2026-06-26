from flask import Blueprint, request, jsonify
from sqlalchemy import text # type: ignore
from werkzeug.security import check_password_hash
from app import db, limiter

auth_bp = Blueprint("auth", __name__)

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
                return raw_password == stored_password

        for table_name, id_col, role, fields in auth_rules:
            try:
                clause = " OR ".join([f"{field} = :u" for field in fields])
                query = text(f"SELECT {id_col}, password FROM {table_name} WHERE {clause} LIMIT 1")
                user = db.session.execute(query, {"u": username}).fetchone()
                if user and verify_password(password, user[1]):
                    return jsonify({
                        "status": "success",
                        "role": role,
                        "username": username,
                        "user_id": str(user[0])
                    }), 200
            except Exception:
                db.session.rollback()
                continue

        return jsonify({"error": "Identifiants incorrects ou compte inexistant."}), 401

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"error": "Erreur interne du serveur."}), 500
