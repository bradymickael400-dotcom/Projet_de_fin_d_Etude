"""
Routes pour la gestion des boîtes noires (BN)
- Création de nouvelles BN
- Génération de QR codes
- Attribution de conteneurs
- Gestion de l'archivage
"""

import os
import uuid
import qrcode
import io
import socket
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app, has_request_context
from sqlalchemy import text
from urllib.parse import quote
from werkzeug.utils import secure_filename
from app import db
from app.utils import (
    get_caller_identity, get_boites_for_owner, get_boites_for_agency,
    _hash_block, _sceller_evenement
)
from app.modules.iot.repository import ensure_iot_schema
from app.modules.iot.iot_service import provision_device
from app.modules.iot.security import generate_secret, hash_secret

bn_bp = Blueprint("boites_noires", __name__)


@bn_bp.route("/api/captive/black-box/register", methods=["POST"])
def captive_register_black_box():
    """Enregistre une boîte depuis le portail captif de l'ESP32.

    Le firmware fournit son identifiant matériel unique (deviceUid). Aucun
    compte ARGOS n'est requis : une boîte sans propriétaire reste visible par
    le superadministrateur ; avec ``owner_id`` elle devient visible à ce
    propriétaire après connexion.
    """
    setup_key = os.getenv("IOT_SETUP_KEY", "ARGOS-PROVISION-2026")
    supplied_key = request.headers.get("X-ARGOS-Setup-Key", "") or request.form.get("setup_key", "")
    if supplied_key != setup_key:
        return jsonify({"error": "Clé de portail invalide"}), 403
    data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    data = data or {}
    device_uid = str(data.get("deviceUid") or data.get("device_uid") or "").strip()
    if not device_uid:
        return jsonify({"error": "deviceUid requis"}), 400
    # Le portail captif volontairement allégé ne demande pas les paramètres
    # techniques. Le type mensuel est la valeur par défaut modifiable ensuite
    # depuis la plateforme ARGOS.
    data["type_boite"] = data.get("type_boite") or "monthly"
    ensure_iot_schema(commit=False)
    try:
        raw_token = None
        dev = db.session.execute(text(
            "SELECT id FROM iot_devices WHERE device_uid=:uid LIMIT 1"
        ), {"uid": device_uid}).fetchone()
        if not dev:
            # L'identifiant est préprogrammé dans le firmware : il n'existe
            # donc pas encore dans la base lors du premier portail captif.
            raw_token = generate_secret(24)
            dev = db.session.execute(text("""
                INSERT INTO iot_devices
                    (device_uid, hardware_serial, firmware_version, protocol_version,
                     enrollment_token_hash, enrollment_expires_at, status)
                VALUES (:uid,:serial,:firmware,'1.0',:token,NOW() + INTERVAL '24 hours','PENDING_ENROLLMENT')
                ON CONFLICT (device_uid) DO UPDATE SET updated_at=NOW()
                RETURNING id
            """), {"uid": device_uid, "serial": data.get("hardware_serial") or device_uid,
                   "firmware": data.get("firmware_version") or "1.0",
                   "token": hash_secret(raw_token)}).fetchone()
            dev = db.session.execute(text(
                "SELECT id FROM iot_devices WHERE device_uid=:uid LIMIT 1"
            ), {"uid": device_uid}).fetchone()
        if not dev:
            return jsonify({"error": "Impossible d'enregistrer l'identifiant ESP32 dans le registre IoT"}), 500
        owner_id = data.get("owner_id") or data.get("id_proprietaire")
        if owner_id:
            owner = db.session.execute(text(
                "SELECT id FROM proprietaire_conteneur WHERE id=:id LIMIT 1"
            ), {"id": owner_id}).fetchone()
            if not owner:
                return jsonify({"error": "Compte propriétaire inexistant"}), 404
        container_id = str(data.get("container_id") or data.get("id_conteneurs") or "").strip() or None
        if container_id:
            container = db.session.execute(text(
                "SELECT id_conteneurs FROM conteneurs WHERE id_conteneurs=:id LIMIT 1"
            ), {"id": container_id}).fetchone()
            if not container:
                return jsonify({"error": "Conteneur inexistant"}), 404
        box_uuid = str(uuid.uuid4())
        serial = str(data.get("numero_serie") or f"BN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}")
        db.session.execute(text("""
            INSERT INTO boite_noir (id_conteneurs,id_proprietaire,type_boite,versions,uuid_qrcode,
                qrcode_generated_at,deployment_date,battery_level,expected_duration,
                status,numero_serie,created_at,log_action)
            VALUES (:container,:owner,:type,:version,:uuid,NOW(),NOW(),100,30,
                    'active',:serial,NOW(),'Enregistrement portail captif')
        """), {"container": container_id, "owner": owner_id, "type": data.get("type_boite"),
              "version": data.get("versions") or data.get("version") or "v2.1",
              "uuid": box_uuid, "serial": serial})
        box_id = db.session.execute(text(
            "SELECT id_boite FROM boite_noir WHERE uuid_qrcode=:u LIMIT 1"
        ), {"u": box_uuid}).scalar()
        db.session.execute(text("""
            INSERT INTO black_box_devices (black_box_id,device_id,assigned_by,status)
            VALUES (:box,:dev,'captive','ACTIVE')
            ON CONFLICT DO NOTHING
        """), {"box": box_id, "dev": dev.id})
        db.session.commit()
        if not request.is_json:
            return "<html><body><script>location.href='http://127.0.0.1:5002'</script><p>Boîte enregistrée. Redirection vers ARGOS…</p></body></html>", 303
        return jsonify({"status": "success", "id_boite": box_id, "blackBoxId": box_id,
                        "numeroSerie": serial, "deviceUid": device_uid,
                        # Secret à usage unique : il n'est renvoyé que lors de
                        # la toute première inscription matérielle.
                        "enrollmentToken": raw_token,
                        "owner_id": owner_id, "visibility": "owner" if owner_id else "superadmin"}), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@bn_bp.route("/api/captive/options", methods=["GET"])
def captive_registration_options():
    """Retourne uniquement les conteneurs libres et entreprises utilisables."""
    try:
        containers = db.session.execute(text("""
            SELECT c.id_conteneurs AS id, COALESCE(c.type_conteneurs, '') AS type
            FROM conteneurs c
            LEFT JOIN boite_noir b ON b.id_conteneurs = c.id_conteneurs
                AND COALESCE(b.archived, FALSE) = FALSE
            WHERE b.id_boite IS NULL
            ORDER BY c.id_conteneurs
        """)).mappings().all()
        owners = db.session.execute(text("""
            SELECT id, nom_agence AS name FROM proprietaire_conteneur
            ORDER BY nom_agence
        """)).mappings().all()
        response = jsonify({"containers": list(containers), "owners": list(owners)})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response, 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


def _build_qr_scan_url(qr_uuid, base_url=None):
    if has_request_context() and request.host.split(":", 1)[0].lower().endswith(".trycloudflare.com"):
        scheme = request.headers.get("X-Forwarded-Proto", "https")
        base = f"{scheme}://{request.host}"
    elif base_url:
        base = base_url.rstrip('/')
    elif current_app.config.get("PUBLIC_BASE_URL"):
        base = current_app.config["PUBLIC_BASE_URL"].rstrip('/')
    elif has_request_context():
        base = request.url_root.rstrip('/')
        host = request.host.split(":", 1)[0]
        if host in ("localhost", "127.0.0.1", "0.0.0.0"):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    lan_ip = s.getsockname()[0]
                scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
                base = f"{scheme}://{lan_ip}:{request.host.split(':', 1)[1]}" if ":" in request.host else f"{scheme}://{lan_ip}"
            except OSError:
                pass
    else:
        base = "http://localhost:5002"
    return f"{base}/?qr={quote(str(qr_uuid))}"


# ═══════════════════════════════════════════════════════════════════
#  INITIALISATION SCHÉMA - Ajouter les colonnes WiFi et UUID QR
# ═══════════════════════════════════════════════════════════════════

def _ensure_wifi_schema():
    """Ajoute les colonnes WiFi à toutes les tables d'authentification"""
    tables = [
        "superadmin", "proprietaire_conteneur", "agence_utilisatrice",
        "client", "transporteur", "port_authority_user"
    ]
    try:
        for table in tables:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS wifi_name TEXT"))
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS wifi_password TEXT"))
        db.session.execute(text("ALTER TABLE boite_noir ADD COLUMN IF NOT EXISTS uuid_qrcode UUID DEFAULT gen_random_uuid()"))
        db.session.execute(text("ALTER TABLE boite_noir ADD COLUMN IF NOT EXISTS qrcode_generated_at TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("ALTER TABLE conteneurs ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ok'"))
        db.session.execute(text("ALTER TABLE boite_noir ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE boite_noir ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'"))
        db.session.execute(text("UPDATE boite_noir SET status = COALESCE(NULLIF(TRIM(status), ''), 'active') WHERE status IS NULL OR TRIM(status) = ''"))
        db.session.execute(text("ALTER TABLE boite_noir ALTER COLUMN status SET DEFAULT 'active'"))
        try:
            db.session.execute(text("ALTER TABLE boite_noir ALTER COLUMN id_conteneurs DROP NOT NULL"))
        except Exception:
            pass
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Erreur schéma WiFi: {e}")


def _generate_qrcode_image(data) -> bytes:
    """Génère une image QR code à partir du lien de scan."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    return img_io.getvalue()


# ═══════════════════════════════════════════════════════════════════
#  CRÉATION NOUVELLE BOÎTE NOIRE (Superadmin only)
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/boites-noires/create", methods=["POST"])
def create_boite_noire():
    """
    Crée une nouvelle boîte noire avec tous les champs requis
    
    Body expected:
    {
        "id_conteneurs": "MSCU1234566",
        "id_proprietaire": 1,
        "type_boite": "monthly",
        "versions": "v2.1",
        "temp_max": 32,
        "temp_min": -10,
        "humi_max": 75,
        "choc_max": 5,
        "pression_min": 995,
        "vitesse_max": 90,
        "angle_max": 30
    }
    """
    role, user_id = get_caller_identity()
    
    # Superadmin uniquement
    if role != "superadmin":
        return jsonify({"error": "Accès réservé au superadmin"}), 403
    
    _ensure_wifi_schema()
    data = request.get_json() or {}
    command_info = {"status": "not_requested"}
    
    try:
        required = ["type_boite"]
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"Champ obligatoire manquant: {field}"}), 400

        container_value = data.get("id_conteneurs") or None
        if container_value:
            container_check = db.session.execute(text(
                "SELECT id_conteneurs FROM conteneurs WHERE id_conteneurs = :id LIMIT 1"
            ), {"id": container_value}).fetchone()
            if not container_check:
                return jsonify({"error": "Conteneur inexistant"}), 404

            existing_bn = db.session.execute(text(
                "SELECT id_boite FROM boite_noir WHERE id_conteneurs = :id AND COALESCE(archived, FALSE) = FALSE LIMIT 1"
            ), {"id": container_value}).fetchone()
            if existing_bn:
                return jsonify({"error": "Ce conteneur est déjà lié à une boîte noire"}), 409

        bn_uuid = str(uuid.uuid4())

        db.session.execute(text("""
            INSERT INTO boite_noir
            (id_conteneurs, id_proprietaire, type_boite, versions, uuid_qrcode, qrcode_generated_at, status, log_action)
            VALUES (:c, :p, :t, :v, :u, NOW(), 'unassigned', :log)
        """), {
            "c": container_value,
            "p": data.get("id_proprietaire") or None,
            "t": data.get("type_boite", "monthly"),
            "v": data.get("versions", "v2.1"),
            "u": bn_uuid,
            "log": "Création manuelle superadmin"
        })
        
        # Récupérer l'ID de la boîte crée
        bn_id = db.session.execute(text(
            "SELECT id_boite FROM boite_noir WHERE uuid_qrcode = :u LIMIT 1"
        ), {"u": bn_uuid}).scalar()
        
        # Insérer les seuils d'alerte
        db.session.execute(text("""
            INSERT INTO seuils_alerte 
            (id_boite, temp_max, temp_min, humi_max, choc_max, pression_min, vitesse_max, angle_max)
            VALUES (:b, :tm, :ti, :hm, :cm, :pm, :vm, :am)
        """), {
            "b": bn_id,
            "tm": data.get("temp_max", 32),
            "ti": data.get("temp_min", -10),
            "hm": data.get("humi_max", 75),
            "cm": data.get("choc_max", 5),
            "pm": data.get("pression_min", 995),
            "vm": data.get("vitesse_max", 90),
            "am": data.get("angle_max", 30)
        })
        
        db.session.commit()

        # Si le prototype a déjà rejoint le point d'accès et est enrôlé,
        # l'association est mise en file immédiatement. Sinon elle restera
        # en attente jusqu'à l'enrôlement du boîtier.
        device_uid = data.get("device_uid") or data.get("deviceUid")
        if device_uid and bn_id and container_value:
            try:
                from app.modules.iot.iot_command_service import create_device_command
                command_info = create_device_command(
                    int(bn_id), "ASSIGN_CONTAINER",
                    {"containerId": str(container_value), "replace": True},
                    requested_by_user_id=str(user_id or ""), allow_fallback=False,
                )
            except Exception as exc:
                command_info = {"status": "pending_device_enrollment", "message": str(exc)}
        
        # Sceller dans la blockchain
        _sceller_evenement("BOITE_NOIRE_CREEE", bn_id, {
            "id_boite": bn_id,
            "id_conteneurs": data.get("id_conteneurs"),
            "created_at": datetime.now().isoformat()
        })
        
        return jsonify({
            "status": "success",
            "id_boite": bn_id,
            "uuid_qrcode": bn_uuid,
            "numero_serie": db.session.execute(text(
                "SELECT numero_serie FROM boite_noir WHERE id_boite = :b"
            ), {"b": bn_id}).scalar(),
            "assignment_command": command_info
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erreur création boîte: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  GÉNÉRER QR CODE AVEC DONNÉES
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/boites-noires/<int:id_boite>/generate-qr", methods=["GET"])
def generate_qrcode(id_boite):
    """Génère et retourne le QR code d'une boîte noire"""
    role, user_id = get_caller_identity()
    
    _ensure_wifi_schema()
    
    # Vérifier accès
    if role == "owner":
        boites = get_boites_for_owner(user_id)
        if not boites or id_boite not in boites:
            return jsonify({"error": "Accès refusé"}), 403
    elif role != "superadmin":
        return jsonify({"error": "Accès réservé au superadmin ou propriétaire"}), 403
    
    try:
        # Récupérer les données de la boîte
        bn_data = db.session.execute(text("""
            SELECT b.id_boite, b.uuid_qrcode, b.numero_serie, b.id_proprietaire, 
                   b.id_conteneurs, p.nom_agence
            FROM boite_noir b
            LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
            WHERE b.id_boite = :b
            LIMIT 1
        """), {"b": id_boite}).fetchone()
        
        if not bn_data:
            return jsonify({"error": "Boîte noire inexistante"}), 404
        
        scan_url = _build_qr_scan_url(bn_data.uuid_qrcode)
        
        # Générer l'image QR
        qr_image = _generate_qrcode_image(scan_url)
        
        response = send_file(
            io.BytesIO(qr_image),
            mimetype='image/png',
            as_attachment=False,
            download_name=f'qrcode_bn_{bn_data.numero_serie}.png'
        )
        response.headers["X-QR-Scan-URL"] = scan_url
        response.headers["Cache-Control"] = "no-store"
        return response
        
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erreur génération QR: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  SCAN QR CODE - RÉCUPÉRER INFO + CONTENEURS DISPONIBLES
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/boites-noires/scan/<uuid_qrcode>", methods=["GET"])
def scan_qrcode(uuid_qrcode):
    """
    Récupère les info d'une boîte via son UUID QR code
    Retourne aussi les conteneurs disponibles selon le rôle
    """
    role, user_id = get_caller_identity()
    
    _ensure_wifi_schema()
    
    try:
        # Récupérer la boîte
        bn_data = db.session.execute(text("""
            SELECT b.id_boite, b.numero_serie, b.id_proprietaire, b.id_conteneurs,
                   b.type_boite, b.versions
            FROM boite_noir b
            WHERE b.uuid_qrcode = :u
            LIMIT 1
        """), {"u": uuid_qrcode}).fetchone()
        
        if not bn_data:
            return jsonify({"error": "QR code invalide ou expiré"}), 404
        
        # Si superadmin: retourner toutes les entreprises
        companies = []
        if role == "superadmin":
            companies = [dict(row._mapping) for row in db.session.execute(text("""
                SELECT id, niu, nom_agence FROM proprietaire_conteneur ORDER BY nom_agence
            """)).fetchall()]
        
        # Conteneurs libres (non liés à une boîte noire)
        free_containers = []
        if role == "superadmin":
            free_containers = [dict(row._mapping) for row in db.session.execute(text("""
                SELECT DISTINCT c.id_conteneurs, c.taile_perimetre, c.type_conteneurs, c.status
                FROM conteneurs c
                LEFT JOIN boite_noir b ON c.id_conteneurs = b.id_conteneurs
                WHERE b.id_boite IS NULL AND c.status != 'off'
                ORDER BY c.id_conteneurs
            """)).fetchall()]
        elif role == "owner":
            # Owner voit seulement les conteneurs non liés à une BN
            free_containers = [dict(row._mapping) for row in db.session.execute(text("""
                SELECT DISTINCT c.id_conteneurs, c.taile_perimetre, c.type_conteneurs, c.status
                FROM conteneurs c
                LEFT JOIN boite_noir b ON c.id_conteneurs = b.id_conteneurs
                WHERE b.id_boite IS NULL AND c.status != 'off'
                ORDER BY c.id_conteneurs
            """)).fetchall()]
        
        return jsonify({
            "status": "success",
            "boite": {
                "id_boite": bn_data.id_boite,
                "numero_serie": bn_data.numero_serie,
                "type": bn_data.type_boite,
                "version": bn_data.versions,
                "id_proprietaire_actuel": bn_data.id_proprietaire
            },
            "companies": companies,
            "containers": free_containers
        }), 200
        
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erreur scan: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  ATTRIBUER UN CONTENEUR À UNE BOÎTE
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/boites-noires/<int:id_boite>/assign-container", methods=["POST"])
def assign_container(id_boite):
    """
    Assigne un conteneur à une boîte noire
    
    Body expected:
    {
        "id_conteneurs": "MSCU1234566",
        "id_proprietaire": 1  (optionnel - superadmin peut changer)
    }
    """
    role, user_id = get_caller_identity()
    
    _ensure_wifi_schema()
    data = request.get_json() or {}
    
    if not data.get("id_conteneurs"):
        return jsonify({"error": "Conteneur requis"}), 400
    
    try:
        # Récupérer la boîte actuelle
        bn = db.session.execute(text(
            "SELECT id_boite, id_proprietaire, id_conteneurs FROM boite_noir WHERE id_boite = :b"
        ), {"b": id_boite}).fetchone()
        
        if not bn:
            return jsonify({"error": "Boîte inexistante"}), 404
        
        # Vérifier accès selon le rôle
        if role == "owner":
            if str(id_boite) not in {str(value) for value in (get_boites_for_owner(user_id) or [])}:
                return jsonify({"error": "Accès refusé"}), 403
        elif role != "superadmin":
            return jsonify({"error": "Accès réservé au superadmin ou propriétaire"}), 403
        
        # Vérifier que le conteneur existe
        container = db.session.execute(text(
            "SELECT id_conteneurs FROM conteneurs WHERE id_conteneurs = :c"
        ), {"c": data["id_conteneurs"]}).fetchone()
        
        if not container:
            return jsonify({"error": "Conteneur inexistant"}), 404
        
        # Vérifier que le conteneur n'est pas déjà assigné
        existing = db.session.execute(text(
            "SELECT id_boite FROM boite_noir WHERE id_conteneurs = :c AND id_boite != :b"
        ), {"c": data["id_conteneurs"], "b": id_boite}).fetchone()
        
        if existing:
            return jsonify({"error": "Ce conteneur est déjà assigné à une autre boîte"}), 409
        
        # Mettre à jour
        update_fields = ["id_conteneurs = :c"]
        params = {"b": id_boite, "c": data["id_conteneurs"]}
        
        if role == "superadmin" and data.get("id_proprietaire"):
            update_fields.append("id_proprietaire = :p")
            params["p"] = data["id_proprietaire"]
        
        db.session.execute(text(f"""
            UPDATE boite_noir 
            SET {", ".join(update_fields)}
            WHERE id_boite = :b
        """), params)
        # Une fois le conteneur lie, redistribuer le lien de suivi uniquement
        # aux parties qui viennent d'acquerir un droit sur cette boite.
        device_uid = db.session.execute(text("""
            SELECT d.device_uid FROM black_box_devices bbd
            JOIN iot_devices d ON d.id=bbd.device_id
            WHERE bbd.black_box_id=:box AND bbd.status='ACTIVE' LIMIT 1
        """), {"box": id_boite}).scalar()
        if device_uid:
            from app.routes.black_boxes import _announce_single_box_connection
            _announce_single_box_connection(id_boite, device_uid)
        
        db.session.commit()
        
        # Sceller
        _sceller_evenement("CONTENEUR_ATTRIBUE", id_boite, {
            "id_boite": id_boite,
            "id_conteneurs": data["id_conteneurs"],
            "assigned_at": datetime.now().isoformat()
        })

        from app.routes.containers import _send_container_id_to_prototype
        device_assignment = _send_container_id_to_prototype(
            id_boite,
            data["id_conteneurs"],
            f"{role}:{user_id}",
        )
        
        return jsonify({
            "status": "success",
            "message": "Conteneur assigné avec succès",
            "id_boite": id_boite,
            "id_conteneurs": data["id_conteneurs"],
            "device_assignment": device_assignment,
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erreur assignation: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  ARCHIVER UN CONTENEUR (Soft delete)
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/containers/<id_conteneur>/archive", methods=["POST"])
@bn_bp.route("/api/containers/<id_conteneur>", methods=["DELETE"])
def archive_container(id_conteneur):
    """Archive un conteneur (status = 'off')"""
    role, user_id = get_caller_identity()
    
    _ensure_wifi_schema()
    
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès refusé"}), 403
    
    try:
        # Vérifier que le conteneur existe
        container = db.session.execute(text(
            "SELECT id_conteneurs FROM conteneurs WHERE id_conteneurs = :c"
        ), {"c": id_conteneur}).fetchone()
        
        if not container:
            return jsonify({"error": "Conteneur inexistant"}), 404
        
        linked_boxes = db.session.execute(text("""
            SELECT id_boite FROM boite_noir
            WHERE id_conteneurs=:c AND COALESCE(archived,FALSE)=FALSE
        """), {"c": id_conteneur}).fetchall()
        box_ids = [row.id_boite for row in linked_boxes]

        # Archiver (soft delete)
        db.session.execute(text(
            "UPDATE conteneurs SET status = 'off' WHERE id_conteneurs = :c"
        ), {"c": id_conteneur})

        if box_ids:
            box_params = {f"box{i}": value for i, value in enumerate(box_ids)}
            box_placeholders = ",".join(f":box{i}" for i in range(len(box_ids)))
            db.session.execute(text("""
                UPDATE boite_noir
                SET id_conteneurs=NULL, status='unassigned', updated_at=NOW()
                WHERE id_boite IN (""" + box_placeholders + """)
            """), box_params)
        
        db.session.commit()

        _sceller_evenement("CONTENEUR_SUPPRIME", None, {
            "id_conteneurs": id_conteneur,
            "boites_liberees": box_ids,
            "deleted_by": f"{role}:{user_id}",
            "deleted_at": datetime.utcnow().isoformat(),
        })

        cleared_devices = []
        from app.modules.iot.iot_command_service import create_device_command
        for box_id in box_ids:
            try:
                command = create_device_command(
                    box_id,
                    "CLEAR_CONTAINER",
                    {"containerId": id_conteneur},
                    requested_by_user_id=f"{role}:{user_id}",
                    allow_fallback=False,
                )
                cleared_devices.append({
                    "id_boite": box_id,
                    "commandUid": command.get("commandUid"),
                    "status": "published",
                })
            except Exception as exc:
                db.session.rollback()
                cleared_devices.append({
                    "id_boite": box_id,
                    "status": "device_unavailable",
                    "message": str(exc),
                })
        
        return jsonify({
            "status": "success",
            "message": "Conteneur supprimé",
            "id_conteneurs": id_conteneur,
            "boites_liberees": box_ids,
            "device_clear_commands": cleared_devices,
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur archivage: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  RÉCUPÉRER CONTENEURS ARCHIVÉS
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/containers/archived", methods=["GET"])
def get_archived_containers():
    """Retourne tous les conteneurs archivés (status = 'off')"""
    role, user_id = get_caller_identity()
    
    _ensure_wifi_schema()
    
    if role not in ("superadmin", "owner", "company"):
        return jsonify({"error": "Accès refusé"}), 403
    
    try:
        archived = db.session.execute(text("""
            SELECT id_conteneurs, taile_perimetre, type_conteneurs, status, 
                   (SELECT COUNT(*) FROM boite_noir b WHERE b.id_conteneurs = c.id_conteneurs) as in_boites
            FROM conteneurs c
            WHERE c.status = 'off'
            ORDER BY id_conteneurs
        """)).fetchall()
        
        return jsonify([dict(row._mapping) for row in archived]), 200
        
    except Exception as e:
        return jsonify({"error": f"Erreur récupération: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  PARAMÈTRES WiFi - UPDATE
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/wifi/update", methods=["POST"])
def update_wifi_settings():
    """
    Met à jour les paramètres WiFi de l'utilisateur connecté
    
    Body expected:
    {
        "wifi_name": "MonWiFi",
        "wifi_password": "secret123"
    }
    """
    role, user_id = get_caller_identity()
    
    if not role or not user_id:
        return jsonify({"error": "Authentification requise"}), 401
    
    _ensure_wifi_schema()
    data = request.get_json() or {}
    
    if not data.get("wifi_name") or not data.get("wifi_password"):
        return jsonify({"error": "Nom et mot de passe WiFi requis"}), 400
    
    try:
        # Mapper le rôle à la table appropriée
        role_to_table = {
            "superadmin": ("superadmin", "id"),
            "owner": ("proprietaire_conteneur", "id"),
            "company": ("agence_utilisatrice", "niu"),
            "client": ("client", "id_cni"),
            "driver": ("transporteur", "id_cni"),
            "port_authority": ("port_authority_user", "id"),
        }
        
        if role not in role_to_table:
            return jsonify({"error": "Rôle non reconnu"}), 400
        
        table, id_col = role_to_table[role]
        
        # Mettre à jour
        db.session.execute(text(f"""
            UPDATE {table}
            SET wifi_name = :wn, wifi_password = :wp
            WHERE {id_col} = :u
        """), {
            "wn": data.get("wifi_name"),
            "wp": data.get("wifi_password"),
            "u": user_id
        })
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Paramètres WiFi sauvegardés"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erreur mise à jour: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  RESTAURER UN CONTENEUR ARCHIVÉ
# ═══════════════════════════════════════════════════════════════════

@bn_bp.route("/api/containers/<id_conteneur>/restore", methods=["POST"])
def restore_container(id_conteneur):
    """Restaure un conteneur archivé (status = 'ok')"""
    role, user_id = get_caller_identity()
    
    _ensure_wifi_schema()
    
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès refusé"}), 403
    
    try:
        # Vérifier que le conteneur existe
        container = db.session.execute(text(
            "SELECT id_conteneurs, status FROM conteneurs WHERE id_conteneurs = :c"
        ), {"c": id_conteneur}).fetchone()
        
        if not container:
            return jsonify({"error": "Conteneur inexistant"}), 404
        
        # Restaurer (soft undelete)
        db.session.execute(text(
            "UPDATE conteneurs SET status = 'ok' WHERE id_conteneurs = :c"
        ), {"c": id_conteneur})
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Conteneur restauré",
            "id_conteneurs": id_conteneur
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur restauration: {str(e)}"}), 500
