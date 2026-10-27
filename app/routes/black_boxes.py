"""
Routes complètes pour la gestion des boîtes noires (BN) - VERSION 2
✅ Création, génération QR, WiFi settings, archivage complet
"""

import json
import uuid
import qrcode
import io
import os
import socket
import ipaddress
import requests
import threading
from datetime import datetime, timedelta
from flask import Blueprint, current_app, request, jsonify, send_file
from sqlalchemy import text
from urllib.parse import quote, urlsplit, urlunsplit
from app import db
from app.utils import get_caller_identity, _sceller_evenement, send_email_background, get_public_base_url
from app.modules.iot.repository import ensure_iot_schema
from app.modules.iot.iot_service import provision_device
from app.modules.iot.security import generate_secret, hash_secret
from app.services.report_service import generate_container_report_pdf
from app.services.storage_service import resolve_private_document, store_private_document

bb_bp = Blueprint("black_boxes", __name__)


def _duration_days(value, default=30):
    """Normalise une durée reçue en nombre de jours positif."""
    try:
        parsed = int(str(value).strip().split()[0])
        return parsed if parsed > 0 else default
    except (TypeError, ValueError, IndexError):
        return default


def _build_qr_scan_url(qr_uuid):
    """Construit le lien ouvert par un scan téléphone."""
    request_host = request.host.split(":", 1)[0].lower()
    if request_host.endswith(".trycloudflare.com"):
        scheme = request.headers.get("X-Forwarded-Proto", "https")
        return f"{scheme}://{request.host}/?qr={quote(str(qr_uuid))}"
    configured = (current_app.config.get("PUBLIC_BASE_URL") or "").strip()
    if configured:
        base = configured.rstrip("/")
    else:
        base = request.url_root.rstrip("/")
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
    return f"{base}/?qr={quote(str(qr_uuid))}"


def _device_api_base_url(data):
    configured = str(data.get("api_base_url") or current_app.config.get("PUBLIC_BASE_URL") or "").strip()
    base = configured.rstrip("/") if configured else request.url_root.rstrip("/")
    parsed = urlsplit(base)
    host = parsed.hostname or ""
    try:
        is_local_host = host == "localhost" or ipaddress.ip_address(host).is_loopback or host == "0.0.0.0"
    except ValueError:
        is_local_host = False
    if is_local_host:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                lan_ip = sock.getsockname()[0]
            scheme = parsed.scheme or request.headers.get("X-Forwarded-Proto", request.scheme)
            netloc = f"{lan_ip}:{parsed.port}" if parsed.port else lan_ip
            base = urlunsplit((scheme, netloc, parsed.path, parsed.query, parsed.fragment))
        except OSError:
            pass
    return base


def _send_initial_configuration(data, configuration):
    access_point_url = str(data.get("access_point_url") or "http://192.168.4.1").strip().rstrip("/")
    setup_key = str(data.get("setup_key") or os.getenv("IOT_SETUP_KEY", "ARGOS-PROVISION-2026"))
    configuration = dict(configuration)
    configuration["setupKey"] = setup_key
    response = requests.post(
        f"{access_point_url}/api/v1/provision",
        json=configuration,
        # Le corps est un repli pour les versions du firmware qui ne
        # transmettent pas correctement les en-têtes personnalisés.
        headers={"X-ARGOS-Setup-Key": setup_key},
        timeout=(3, 12),
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"ESP32 a refusé la configuration (HTTP {response.status_code})")
    try:
        result = response.json()
    except ValueError:
        raise RuntimeError("Réponse de configuration ESP32 invalide") from None
    if result.get("status") not in ("success", "configured"):
        raise RuntimeError(result.get("error") or "La configuration n'a pas été confirmée par l'ESP32")
    return result


def _box_share_recipients(box_id):
    """Courriels actuellement autorises a consulter la boite."""
    rows = db.session.execute(text("""
        SELECT p.addresse_mail AS email
        FROM boite_noir b JOIN proprietaire_conteneur p ON p.id=b.id_proprietaire
        WHERE b.id_boite=:box
        UNION
        SELECT a.addresse_mail FROM agence_abonnement aa
        JOIN agence_utilisatrice a ON a.niu=aa.id_agence
        WHERE aa.id_boite=:box AND LOWER(COALESCE(aa.status,'actif'))='actif'
        UNION
        SELECT c.address_mail FROM abonner ab JOIN client c ON c.id_cni=ab.id_cni
        WHERE ab.id_boite=:box AND LOWER(COALESCE(ab.status,'actif'))='actif'
    """), {"box": box_id}).fetchall()
    return sorted({str(r.email).strip() for r in rows if r.email and "@" in str(r.email)})


def _announce_single_box_connection(box_id, device_uid):
    box = db.session.execute(text("""
        SELECT uuid_qrcode,numero_serie,id_conteneurs FROM boite_noir WHERE id_boite=:box
    """), {"box": box_id}).fetchone()
    if not box:
        return None, []
    share_url = _build_qr_scan_url(box.uuid_qrcode)
    message = (
        f"Boîte {box.numero_serie or box_id} connectée ({device_uid}). "
        f"Suivi distant : {share_url}"
    )
    # 'all' est ensuite filtre par les restrictions de boite/conteneur de
    # /api/notifications. Une boite libre n'est visible que du superadmin.
    db.session.execute(text("""
        INSERT INTO notifications(type,message,cible_role,id_boite,device_uid)
        VALUES('IOT_DIRECT_CONNECTED',:message,'all',:box,:device_uid)
    """), {"message": message, "box": box_id, "device_uid": device_uid})
    emails = _box_share_recipients(box_id) if box.id_conteneurs else []
    if emails:
        qr_url = f"{get_public_base_url()}/api/black-boxes/{box_id}/qrcode"
        qr_buffer = io.BytesIO()
        qrcode.make(share_url).save(qr_buffer, format="PNG")
        qr_png = qr_buffer.getvalue()
        content = (
            f"La boîte ARGOS {box.numero_serie or box_id} est maintenant connectée.\n\n"
            f"Lien cliquable : {share_url}\n"
            f"QR code en pièce jointe : argos_{box_id}.png\n"
            f"QR code en ligne : {qr_url}\n\n"
            "Une authentification ARGOS et une relation active avec le conteneur restent obligatoires."
        )
        threading.Thread(
            target=send_email_background,
            args=(emails, f"Accès distant ARGOS — {box.numero_serie or box_id}",
                  content, qr_png, f"argos_{box_id}.png"),
            kwargs={
                "severity": "success",
                "action_url": share_url,
                "action_label": "Ouvrir le suivi ARGOS",
            },
            daemon=True,
        ).start()
    return share_url, emails


# ═══════════════════════════════════════════════════════════════════
#  INITIALISATION SCHÉMA - Garantir colonnes pour archivage
# ═══════════════════════════════════════════════════════════════════

def _ensure_archiving_schema():
    """Ajoute les colonnes nécessaires pour l'archivage des boîtes et conteneurs"""
    try:
        db.session.execute(text("""
            ALTER TABLE conteneurs
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ok'
        """))

        db.session.execute(text("""
            ALTER TABLE boite_noir
            ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE
        """))

        db.session.execute(text("""
            ALTER TABLE boite_noir
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'
        """))

        db.session.execute(text("""
            ALTER TABLE boite_noir
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        """))

        db.session.execute(text("""
            UPDATE boite_noir
            SET status = COALESCE(NULLIF(TRIM(status), ''), 'active')
            WHERE status IS NULL OR TRIM(status) = ''
        """))

        db.session.execute(text("""
            ALTER TABLE boite_noir
            ALTER COLUMN status SET DEFAULT 'active'
        """))

        try:
            db.session.execute(text("""
                ALTER TABLE boite_noir
                ALTER COLUMN id_conteneurs DROP NOT NULL
            """))
        except Exception:
            pass

        db.session.commit()
        print("✓ Schéma d'archivage initialisé")
    except Exception as e:
        db.session.rollback()
        print(f"[WARN] Schéma archivage: {e}")


# ═══════════════════════════════════════════════════════════════════
#  1️⃣ CRÉER UNE NOUVELLE BOÎTE NOIRE
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/black-boxes/create", methods=["POST"])
def create_black_box():
    """
    Crée une nouvelle boîte noire avec tous les paramètres.
    Le conteneur est optionnel lors de la création ; il peut être assigné ensuite via QR.
    """
    role, user_id = get_caller_identity()

    if role not in ["superadmin", "owner"]:
        return jsonify({"error": "Accès réservé au superadmin et propriétaires"}), 403

    data = request.get_json() or {}

    required_fields = ["type_boite"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Champ manquant: {field}"}), 400

    try:
        device_uid = str(data.get("device_uid") or data.get("deviceUid") or "").strip()
        if device_uid:
            registered = db.session.execute(text("""
                SELECT d.status, bbd.black_box_id
                FROM iot_devices d
                LEFT JOIN black_box_devices bbd
                  ON bbd.device_id=d.id AND bbd.status='ACTIVE'
                WHERE d.device_uid=:uid
                LIMIT 1
            """), {"uid": device_uid}).fetchone()
            if registered:
                if registered.black_box_id:
                    return jsonify({
                        "error": "Cet ESP32 est déjà associé à une boîte noire",
                        "deviceUid": device_uid,
                        "blackBoxId": registered.black_box_id,
                        "action": "reconfigure",
                    }), 409
                return jsonify({
                    "error": "Cet identifiant ESP32 existe déjà dans le registre IoT et doit être réparé avant une nouvelle création",
                    "deviceUid": device_uid,
                    "action": "repair",
                }), 409

        container_value = data.get("container_id") or None
        # Une boîte sans conteneur reste disponible pour l'association
        # ultérieure ; une boîte créée avec un conteneur est immédiatement active.
        box_status = "active" if container_value else "unassigned"
        if container_value:
            container_check = db.session.execute(text(
                "SELECT id_conteneurs FROM conteneurs WHERE id_conteneurs = :id LIMIT 1"
            ), {"id": container_value}).fetchone()
            if not container_check:
                return jsonify({"error": f"Conteneur {container_value} inexistant"}), 404

            existing_bn = db.session.execute(text(
                "SELECT id_boite FROM boite_noir WHERE id_conteneurs = :id AND COALESCE(archived, FALSE) = FALSE LIMIT 1"
            ), {"id": container_value}).fetchone()
            if existing_bn:
                return jsonify({"error": "Ce conteneur a déjà une boîte noire active"}), 409

        bn_uuid = str(uuid.uuid4())
        serial_number = f"BN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        db.session.execute(text("""
            INSERT INTO boite_noir
            (id_conteneurs, id_proprietaire, type_boite, versions, uuid_qrcode,
             deployment_date, battery_level, expected_duration, status, numero_serie,
             created_at, log_action)
            VALUES (:container, :owner, :type, :version, :uuid, :deploy, :battery, :duration, :status, :serial, NOW(), :log)
        """), {
            "container": container_value,
            "owner": data.get("proprietaire_id") or None,
            "type": data.get("type_boite", "monthly"),
            "version": data.get("version", "v2.1"),
            "uuid": bn_uuid,
            "deploy": datetime.fromisoformat(data.get("deployment_date", datetime.now().isoformat())),
            "battery": data.get("battery_capacity", 100),
            "duration": _duration_days(data.get("expected_duration")),
            "status": box_status,
            "serial": serial_number,
            "log": f"Création par {role} #{user_id}"
        })

        bn_id = db.session.execute(text(
            "SELECT id_boite FROM boite_noir WHERE uuid_qrcode = :u LIMIT 1"
        ), {"u": bn_uuid}).scalar()

        try:
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
        except Exception as e:
            print(f"Avertissement seuils_alerte: {e}")

        identity = provision_device({
            "device_uid": data.get("device_uid"),
            "black_box_id": bn_id,
            "hardware_serial": serial_number,
            "firmware_version": data.get("version", "v2.1"),
        }, actor_role=role, actor_id=user_id, commit=False)

        connection_mode = str(data.get("connection_mode") or "network").strip().lower()
        if connection_mode not in ("network", "direct"):
            raise ValueError("Mode de communication ESP32 invalide")
        configuration = {
            "blackBoxId": bn_id,
            "containerId": container_value,
            "deviceUid": identity["deviceUid"],
            "enrollmentToken": identity["enrollmentToken"],
            "apiBaseUrl": "" if connection_mode == "direct" else _device_api_base_url(data),
            "wifi": {
                "ssid": "" if connection_mode == "direct" else str(data.get("wifi_ssid") or "").strip(),
                "password": "" if connection_mode == "direct" else str(data.get("wifi_password") or ""),
            },
            "thresholds": {
                "temperatureMax": data.get("temp_max", 32),
                "temperatureMin": data.get("temp_min", -10),
                "humidityMax": data.get("humi_max", 75),
                "shockMax": data.get("choc_max", 5),
                "pressureMin": data.get("pression_min", 995),
                "speedMax": data.get("vitesse_max", 90),
                "angleMax": data.get("angle_max", 30),
                "distanceCm": data.get("distance_cm", 15),
            },
        }
        if connection_mode == "network" and not configuration["wifi"]["ssid"]:
            raise ValueError("Le nom du réseau Wi-Fi destiné à la boîte est requis")

        db.session.commit()

        _sceller_evenement("BOITE_NOIRE_CREEE", bn_id, {
            "id_boite": bn_id,
            "container": container_value,
            "created_by": f"{role}#{user_id}",
            "timestamp": datetime.now().isoformat()
        })

        return jsonify({
            "status": "success",
            "id_boite": bn_id,
            "uuid_qrcode": bn_uuid,
            "numero_serie": serial_number,
            "device_uid": identity["deviceUid"],
            "configuration_status": "ready_for_browser_delivery",
            "connection_mode": connection_mode,
            "device_configuration": {**configuration, "setupKey": str(
                data.get("setup_key") or os.getenv("IOT_SETUP_KEY", "ARGOS-PROVISION-2026")
            )},
            "message": "Boîte créée. La configuration doit maintenant être transmise localement à l’ESP32."
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Création BN: {e}")
        import traceback; traceback.print_exc()
        status_code = 502 if isinstance(e, (requests.RequestException, RuntimeError)) else 400 if isinstance(e, ValueError) else 500
        message = (
            "Impossible de configurer l’ESP32. Connectez cet ordinateur au point d’accès "
            f"ARGOS-SETUP du boîtier, puis recommencez. Détail : {e}"
            if status_code == 502 else f"Erreur: {str(e)}"
        )
        return jsonify({"error": message}), status_code


@bb_bp.route("/api/black-boxes/<int:box_id>/reprovision", methods=["POST"])
def reprovision_black_box(box_id):
    """Réémet un jeton et renvoie la configuration à un ESP32 déjà lié."""
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès réservé"}), 403
    data = request.get_json(silent=True) or {}
    try:
        ensure_iot_schema(commit=False)
        row = db.session.execute(text("""
            SELECT b.id_boite, b.id_conteneurs, b.id_proprietaire,
                   d.id AS device_id, d.device_uid
            FROM boite_noir b
            JOIN black_box_devices bbd
              ON bbd.black_box_id=b.id_boite AND bbd.status='ACTIVE'
            JOIN iot_devices d ON d.id=bbd.device_id
            WHERE b.id_boite=:box
            LIMIT 1
        """), {"box": box_id}).fetchone()
        if not row:
            return jsonify({"error": "Aucun dispositif n’est lié à cette boîte"}), 404
        if role == "owner" and str(row.id_proprietaire or "") != str(user_id):
            return jsonify({"error": "Accès refusé"}), 403
        wifi_ssid = str(data.get("wifi_ssid") or "").strip()
        if not wifi_ssid:
            return jsonify({"error": "Le nom du réseau Wi-Fi est requis"}), 400
        connection_mode = str(data.get("connection_mode") or "multiple").strip().lower()
        if connection_mode not in ("multiple", "single"):
            return jsonify({"error": "Mode de connexion invalide"}), 400
        detected_uid = str(data.get("detected_device_uid") or "").strip()
        if not detected_uid:
            return jsonify({"error": "Identité locale ESP32 non vérifiée"}), 409
        if detected_uid != str(row.device_uid):
            return jsonify({
                "error": "L’ESP32 connecté ne correspond pas à cette boîte",
                "expectedDeviceUid": row.device_uid,
                "detectedDeviceUid": detected_uid,
            }), 409

        raw_token = generate_secret(24)
        db.session.execute(text("""
            UPDATE iot_devices
            SET enrollment_token_hash=:token,
                enrollment_expires_at=NOW() + INTERVAL '24 hours',
                credential_hash=NULL,
                status='PENDING_ENROLLMENT', updated_at=NOW()
            WHERE id=:device
        """), {"token": hash_secret(raw_token), "device": row.device_id})
        configuration = {
            "blackBoxId": row.id_boite,
            "containerId": row.id_conteneurs,
            "deviceUid": row.device_uid,
            "enrollmentToken": raw_token,
            "apiBaseUrl": _device_api_base_url(data),
            "wifi": {"ssid": wifi_ssid, "password": str(data.get("wifi_password") or "")},
            "thresholds": {"distanceCm": data.get("distance_cm", 15)},
        }
        share_url, recipients = (None, [])
        if connection_mode == "single":
            share_url, recipients = _announce_single_box_connection(box_id, row.device_uid)
        db.session.commit()
        return jsonify({
            "status": "success", "device_uid": row.device_uid,
            "device_configuration": {**configuration, "setupKey": str(
                data.get("setup_key") or os.getenv("IOT_SETUP_KEY", "ARGOS-PROVISION-2026")
            )},
            "connection_mode": connection_mode,
            "share_url": share_url,
            "notified_emails": len(recipients),
            "message": "Jeton renouvelé. La configuration est prête pour l’envoi local."
        }), 200
    except Exception as exc:
        db.session.rollback()
        status_code = 502 if isinstance(exc, (requests.RequestException, RuntimeError)) else 500
        return jsonify({"error": f"Reconnexion impossible : {exc}"}), status_code


@bb_bp.route("/api/black-boxes/<int:box_id>/direct-session", methods=["POST"])
def start_direct_black_box_session(box_id):
    """Annonce une session AP après vérification stricte de la boîte et du rôle."""
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner", "company"):
        return jsonify({"error": "Connexion directe réservée aux gestionnaires"}), 403
    data = request.get_json(silent=True) or {}
    supplied_uid = str(data.get("deviceUid") or data.get("device_uid") or "").strip()
    if not supplied_uid:
        return jsonify({"error": "deviceUid requis"}), 422

    try:
        ensure_iot_schema(commit=False)
        row = db.session.execute(text("""
            SELECT b.id_boite,b.id_conteneurs,b.id_proprietaire,b.uuid_qrcode,
                   b.numero_serie,d.device_uid
            FROM boite_noir b
            JOIN black_box_devices bbd
              ON bbd.black_box_id=b.id_boite AND bbd.status='ACTIVE'
            JOIN iot_devices d ON d.id=bbd.device_id
            WHERE b.id_boite=:box AND COALESCE(b.archived,FALSE)=FALSE
            LIMIT 1
        """), {"box": box_id}).fetchone()
        if not row:
            return jsonify({"error": "Boîte ou association ESP32 introuvable"}), 404
        if supplied_uid != str(row.device_uid):
            return jsonify({
                "error": "L’ESP32 connecté ne correspond pas à cette boîte",
                "expectedDeviceUid": row.device_uid,
                "detectedDeviceUid": supplied_uid,
            }), 409

        allowed = role == "superadmin"
        if role == "owner":
            allowed = str(row.id_proprietaire or "") == str(user_id)
        elif role == "company":
            allowed = bool(db.session.execute(text("""
                SELECT 1 FROM agence_abonnement
                WHERE id_boite=:box AND CAST(id_agence AS TEXT)=:uid
                  AND LOWER(COALESCE(status,'actif'))='actif'
                LIMIT 1
            """), {"box": box_id, "uid": str(user_id)}).scalar())
        if not allowed:
            return jsonify({"error": "Cette boîte ne fait pas partie de votre périmètre"}), 403

        # Une reprise automatique de l'onglet ne doit pas renvoyer le même mail
        # ni recréer une notification à chaque rafraîchissement.
        recently_announced = bool(db.session.execute(text("""
            SELECT 1 FROM audit_logs
            WHERE action='IOT_DIRECT_SESSION_STARTED'
              AND entity_type='black_box' AND entity_id=:box
              AND actor_role=:role AND actor_id=:actor
              AND created_at >= NOW() - INTERVAL '5 minutes'
            LIMIT 1
        """), {"box": str(box_id), "role": role, "actor": str(user_id)}).scalar())
        share_url = _build_qr_scan_url(row.uuid_qrcode)
        recipients = []
        if not recently_announced:
            share_url, recipients = _announce_single_box_connection(box_id, supplied_uid)
            db.session.execute(text("""
                INSERT INTO audit_logs
                    (actor_role,actor_id,action,entity_type,entity_id,details)
                VALUES(:role,:actor,'IOT_DIRECT_SESSION_STARTED','black_box',:box,
                       CAST(:details AS jsonb))
            """), {
                "role": role, "actor": str(user_id), "box": str(box_id),
                "details": json.dumps({
                    "deviceUid": supplied_uid,
                    "containerId": row.id_conteneurs,
                    "shareUrl": share_url,
                    "notifiedEmails": len(recipients),
                }),
            })
        db.session.commit()
        return jsonify({
            "status": "success",
            "blackBoxId": box_id,
            "deviceUid": supplied_uid,
            "shareUrl": share_url,
            "notifiedEmails": len(recipients),
            "announcement": "recent" if recently_announced else "created",
        }), 200 if recently_announced else 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Session directe impossible : {exc}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  2️⃣ RÉCUPÉRER TOUTES LES BOÎTES NOIRES DE L'UTILISATEUR
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/black-boxes/my-boxes", methods=["GET"])
def get_my_black_boxes():
    """
    Récupère toutes les boîtes noires de l'utilisateur connecté
    Avec tous les détails: batterie, date déploiement, état, etc.
    """
    role, user_id = get_caller_identity()
    
    # Vérifie l'accès
    if role not in ["superadmin", "owner"]:
        return jsonify({"error": "Accès réservé"}), 403
    
    try:
        ensure_iot_schema()
        if role == "superadmin":
            query = """
                SELECT b.id_boite, b.id_conteneurs, b.uuid_qrcode, b.numero_serie,
                       b.type_boite, b.versions, b.battery_level, b.expected_duration,
                       b.deployment_date, b.status, b.archived,
                       b.created_at, b.updated_at,
                       p.nom_agence as proprietaire_name,
                       c.taile_perimetre, c.type_conteneurs,
                       d.device_uid, d.hardware_serial, d.firmware_version,
                       d.protocol_version, d.status AS device_status, d.last_seen_at, d.last_ip,
                       sr.temperature, sr.humidity, sr.pressure, sr.shock, sr.distance_cm,
                       sr.acceleration_x, sr.acceleration_y, sr.acceleration_z,
                       sr.battery_level AS telemetry_battery, sr.light_level,
                       sr.sound_level, sr.flame_detected, sr.door_open, sr.modes,
                       sr.quality,
                       pos.latitude, pos.longitude, sr.sequence, sr.security_alarm,
                       sr.measured_at AS telemetry_at
                FROM boite_noir b
                LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
                LEFT JOIN conteneurs c ON b.id_conteneurs = c.id_conteneurs
                LEFT JOIN black_box_devices bbd ON bbd.black_box_id = b.id_boite AND bbd.status = 'ACTIVE'
                LEFT JOIN iot_devices d ON d.id = bbd.device_id
                LEFT JOIN LATERAL (
                    SELECT temperature, humidity, pressure, shock, distance_cm,
                           acceleration_x, acceleration_y, acceleration_z, sequence,
                           battery_level, light_level, sound_level, flame_detected,
                           door_open, security_alarm, modes, quality, measured_at
                    FROM sensor_readings
                    WHERE black_box_id = b.id_boite
                    ORDER BY measured_at DESC LIMIT 1
                ) sr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT latitude, longitude FROM positions
                    WHERE device_id=d.id ORDER BY measured_at DESC LIMIT 1
                ) pos ON TRUE
                WHERE COALESCE(b.archived, FALSE) = FALSE
                ORDER BY b.created_at DESC
            """
            result = db.session.execute(text(query))
        else:
            query = """
                SELECT b.id_boite, b.id_conteneurs, b.uuid_qrcode, b.numero_serie,
                       b.type_boite, b.versions, b.battery_level, b.expected_duration,
                       b.deployment_date, b.status, b.archived,
                       b.created_at, b.updated_at,
                       p.nom_agence as proprietaire_name,
                       c.taile_perimetre, c.type_conteneurs,
                       d.device_uid, d.hardware_serial, d.firmware_version,
                       d.protocol_version, d.status AS device_status, d.last_seen_at, d.last_ip,
                       sr.temperature, sr.humidity, sr.pressure, sr.shock, sr.distance_cm,
                       sr.acceleration_x, sr.acceleration_y, sr.acceleration_z,
                       sr.battery_level AS telemetry_battery, sr.light_level,
                       sr.sound_level, sr.flame_detected, sr.door_open, sr.modes,
                       sr.quality,
                       pos.latitude, pos.longitude, sr.sequence, sr.security_alarm,
                       sr.measured_at AS telemetry_at
                FROM boite_noir b
                LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
                LEFT JOIN conteneurs c ON b.id_conteneurs = c.id_conteneurs
                LEFT JOIN black_box_devices bbd ON bbd.black_box_id = b.id_boite AND bbd.status = 'ACTIVE'
                LEFT JOIN iot_devices d ON d.id = bbd.device_id
                LEFT JOIN LATERAL (
                    SELECT temperature, humidity, pressure, shock, distance_cm,
                           acceleration_x, acceleration_y, acceleration_z, sequence,
                           battery_level, light_level, sound_level, flame_detected,
                           door_open, security_alarm, modes, quality, measured_at
                    FROM sensor_readings
                    WHERE black_box_id = b.id_boite
                    ORDER BY measured_at DESC LIMIT 1
                ) sr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT latitude, longitude FROM positions
                    WHERE device_id=d.id ORDER BY measured_at DESC LIMIT 1
                ) pos ON TRUE
                WHERE b.id_proprietaire = :owner_id AND COALESCE(b.archived, FALSE) = FALSE
                ORDER BY b.created_at DESC
            """
            result = db.session.execute(text(query), {"owner_id": user_id})

        boxes = []
        for row in result:
            deployment = row.deployment_date
            duration_days = 30
            if row.expected_duration:
                try:
                    duration_str = str(row.expected_duration).split()[0]
                    duration_days = int(duration_str)
                except Exception:
                    pass

            end_date = deployment + timedelta(days=duration_days) if deployment else None
            if end_date and getattr(end_date, 'tzinfo', None) is None:
                end_date = end_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
            now_dt = datetime.now(end_date.tzinfo) if end_date else datetime.now()
            # Une configuration ancienne/incomplète sans date ne doit jamais
            # être présentée comme expirée. Les nouvelles créations reçoivent
            # désormais une date et une durée dès leur enregistrement.
            days_remaining = max(0, (end_date.date() - now_dt.date()).days) if end_date else None

            boxes.append({
                "id_boite": row.id_boite,
                "container_id": row.id_conteneurs,
                "uuid": row.uuid_qrcode,
                "numero_serie": row.numero_serie,
                "type": row.type_boite,
                "version": row.versions,
                "battery": row.battery_level,
                "expected_duration": row.expected_duration,
                "deployment_date": row.deployment_date.isoformat() if row.deployment_date else None,
                "end_of_life_date": end_date.isoformat() if end_date else None,
                "status": row.status,
                "proprietaire": row.proprietaire_name,
                "container_type": row.type_conteneurs,
                "container_size": row.taile_perimetre,
                "device_uid": row.device_uid,
                "device_hardware_serial": row.hardware_serial,
                "device_firmware": row.firmware_version,
                "device_protocol": row.protocol_version,
                "device_status": row.device_status,
                "device_last_ip": row.last_ip,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "device_connected": bool(
                    row.device_status != "REVOKED" and row.last_seen_at
                    and (datetime.now(row.last_seen_at.tzinfo) - row.last_seen_at).total_seconds() <= 90
                ),
                "assignment_status": "assigned" if row.id_conteneurs else "unassigned",
                "telemetry_label": "Assignée" if row.id_conteneurs else "Non assignée",
                "telemetry": {
                    "temperature": row.temperature if role == "superadmin" or row.id_conteneurs else None,
                    "humidity": row.humidity if role == "superadmin" or row.id_conteneurs else None,
                    "pressure": row.pressure if role == "superadmin" or row.id_conteneurs else None,
                    "shock": row.shock if role == "superadmin" or row.id_conteneurs else None,
                    "distance_cm": row.distance_cm if role == "superadmin" or row.id_conteneurs else None,
                    "acceleration_x": row.acceleration_x if role == "superadmin" or row.id_conteneurs else None,
                    "acceleration_y": row.acceleration_y if role == "superadmin" or row.id_conteneurs else None,
                    "acceleration_z": row.acceleration_z if role == "superadmin" or row.id_conteneurs else None,
                    "battery_level": row.telemetry_battery if role == "superadmin" or row.id_conteneurs else None,
                    "light_level": row.light_level if role == "superadmin" or row.id_conteneurs else None,
                    "sound_level": row.sound_level if role == "superadmin" or row.id_conteneurs else None,
                    "flame_detected": bool(row.flame_detected) if role == "superadmin" or row.id_conteneurs else None,
                    "door_open": bool(row.door_open) if role == "superadmin" or row.id_conteneurs else None,
                    "latitude": row.latitude if role == "superadmin" or row.id_conteneurs else None,
                    "longitude": row.longitude if role == "superadmin" or row.id_conteneurs else None,
                    "device_uid": row.device_uid,
                    "sequence": row.sequence if role == "superadmin" or row.id_conteneurs else None,
                    "security_alarm": row.security_alarm if role == "superadmin" or row.id_conteneurs else None,
                    "security_enabled": bool((row.modes or {}).get("securityEnabled"))
                    if isinstance(row.modes, dict) and (role == "superadmin" or row.id_conteneurs) else None,
                    "modes": (row.modes or {})
                    if isinstance(row.modes, dict) and (role == "superadmin" or row.id_conteneurs) else {},
                    "quality": (row.quality or {})
                    if isinstance(row.quality, dict) and (role == "superadmin" or row.id_conteneurs) else {},
                    "measured_at": row.telemetry_at.isoformat() if row.telemetry_at and (role == "superadmin" or row.id_conteneurs) else None,
                },
                "days_remaining": days_remaining,
                "is_dead": bool(end_date and end_date <= now_dt)
            })
        
        return jsonify({
            "status": "success",
            "count": len(boxes),
            "boxes": boxes
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Récupérer boîtes: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


@bb_bp.route("/api/black-boxes/<int:box_id>/history", methods=["GET"])
def get_black_box_history(box_id):
    """Trajet chronologique et événements détaillés d'une boîte autorisée."""
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner", "company", "client", "driver"):
        return jsonify({"error": "Accès réservé"}), 403
    ensure_iot_schema()
    box = db.session.execute(text("""
        SELECT b.id_boite,b.numero_serie,b.id_conteneurs,b.id_proprietaire,d.device_uid
        FROM boite_noir b
        LEFT JOIN black_box_devices bbd ON bbd.black_box_id=b.id_boite AND bbd.status='ACTIVE'
        LEFT JOIN iot_devices d ON d.id=bbd.device_id
        WHERE b.id_boite=:box LIMIT 1
    """), {"box": box_id}).fetchone()
    if not box:
        return jsonify({"error": "Boîte inexistante"}), 404
    allowed = role == "superadmin" or (role == "owner" and str(box.id_proprietaire or "") == str(user_id))
    if role == "company":
        allowed = bool(db.session.execute(text("""
            SELECT 1 FROM agence_abonnement WHERE id_boite=:box
              AND CAST(id_agence AS TEXT)=:uid AND LOWER(COALESCE(status,'actif'))='actif'
        """), {"box": box_id, "uid": str(user_id)}).scalar())
    elif role == "client":
        allowed = bool(db.session.execute(text("""
            SELECT 1 FROM abonner WHERE id_boite=:box AND CAST(id_cni AS TEXT)=:uid
              AND LOWER(COALESCE(status,'actif'))='actif'
        """), {"box": box_id, "uid": str(user_id)}).scalar())
    elif role == "driver":
        allowed = bool(db.session.execute(text("""
            SELECT 1 FROM colis co JOIN abonner a ON a.id_cni=co.id_cni_client
            WHERE a.id_boite=:box AND CAST(co.id_cni_transporteur AS TEXT)=:uid LIMIT 1
        """), {"box": box_id, "uid": str(user_id)}).scalar())
    if not allowed:
        return jsonify({"error": "Boîte inexistante ou accès refusé"}), 404
    try:
        limit = min(max(int(request.args.get("limit", 600)), 2), 2000)
    except (TypeError, ValueError):
        limit = 600
    rows = db.session.execute(text("""
        SELECT sr.sequence,sr.measured_at,sr.temperature,sr.humidity,sr.pressure,
               sr.shock,sr.battery_level,sr.light_level,sr.sound_level,sr.distance_cm,
               sr.acceleration_x,sr.acceleration_y,sr.acceleration_z,sr.flame_detected,
               sr.door_open,sr.security_alarm,sr.modes,sr.quality,
               p.latitude,p.longitude,p.speed,p.heading,p.accuracy,p.source,
               e.id_eventinit,e.log_action,e.notif,
               audio.recording_uid,audio.duration_seconds,audio.mime_type
        FROM sensor_readings sr
        LEFT JOIN positions p ON p.raw_message_id=sr.raw_message_id
        LEFT JOIN LATERAL (
            SELECT id_eventinit,log_action,notif
            FROM evenement_save
            WHERE id_boite=sr.black_box_id AND sequence=sr.sequence
            ORDER BY COALESCE(horodatage,created_at) DESC LIMIT 1
        ) e ON TRUE
        LEFT JOIN LATERAL (
            SELECT recording_uid,duration_seconds,mime_type
            FROM audio_recordings ar
            WHERE ar.black_box_id=sr.black_box_id
              AND sr.measured_at >= COALESCE(ar.started_at,ar.created_at)
              AND sr.measured_at <= COALESCE(ar.started_at,ar.created_at)
                  + (COALESCE(ar.duration_seconds,0) * INTERVAL '1 second')
            ORDER BY COALESCE(ar.started_at,ar.created_at) DESC
            LIMIT 1
        ) audio ON TRUE
        WHERE sr.black_box_id=:box
        ORDER BY sr.measured_at ASC,sr.sequence ASC
        LIMIT :limit
    """), {"box": box_id, "limit": limit}).fetchall()
    points = []
    for row in rows:
        item = dict(row._mapping)
        for key in ("measured_at", "recording_uid"):
            if item.get(key) is not None:
                item[key] = str(item[key])
        item["audio_url"] = f"/api/audio/{item['recording_uid']}" if item.get("recording_uid") else None
        points.append(item)
    return jsonify({
        "status": "success",
        "box": {"id": box.id_boite, "serial": box.numero_serie,
                "containerId": box.id_conteneurs, "deviceUid": box.device_uid},
        "points": points,
    }), 200


@bb_bp.route("/api/black-boxes/<int:box_id>/configure", methods=["PUT", "PATCH"])
def configure_black_box(box_id):
    """Modifie la configuration complète d'une boîte existante."""
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès réservé"}), 403
    data = request.get_json(silent=True) or {}
    allowed = {"type_boite":"monthly", "versions":"v2.1", "battery_level":100,
               "expected_duration":30, "deployment_date":None}
    allowed.update({k: data[k] for k in allowed if k in data})
    allowed["expected_duration"] = _duration_days(allowed["expected_duration"])
    try:
        owner_clause = "" if role == "superadmin" else " AND id_proprietaire=:owner"
        params = {"box": box_id, "owner": user_id, **allowed}
        result = db.session.execute(text(f"""
            UPDATE boite_noir SET type_boite=:type_boite, versions=:versions,
                battery_level=:battery_level, expected_duration=:expected_duration,
                deployment_date=COALESCE(:deployment_date, deployment_date), updated_at=NOW()
            WHERE id_boite=:box {owner_clause}
        """), params)
        if result.rowcount == 0:
            return jsonify({"error": "Boîte inexistante ou accès refusé"}), 404
        db.session.commit()
        return jsonify({"status":"success", "id_boite":box_id}), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400


@bb_bp.route("/api/black-boxes/archived", methods=["GET"])
def get_archived_black_boxes():
    """
    Récupère toutes les boîtes noires archivées (status='off' AND archived=TRUE)
    """
    role, user_id = get_caller_identity()

    if role not in ["superadmin", "owner"]:
        return jsonify({"error": "Accès réservé"}), 403

    try:
        if role == "superadmin":
            query = """
                SELECT b.id_boite, b.id_conteneurs, b.uuid_qrcode, b.numero_serie,
                       b.type_boite, b.versions, b.battery_level, b.expected_duration,
                       b.deployment_date, b.status, b.archived,
                       b.created_at, b.updated_at,
                       p.nom_agence as proprietaire_name,
                       c.taile_perimetre, c.type_conteneurs
                FROM boite_noir b
                LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
                LEFT JOIN conteneurs c ON b.id_conteneurs = c.id_conteneurs
                WHERE COALESCE(b.archived, FALSE) = TRUE AND b.status = 'off'
                ORDER BY b.updated_at DESC
            """
            result = db.session.execute(text(query))
        else:
            query = """
                SELECT b.id_boite, b.id_conteneurs, b.uuid_qrcode, b.numero_serie,
                       b.type_boite, b.versions, b.battery_level, b.expected_duration,
                       b.deployment_date, b.status, b.archived,
                       b.created_at, b.updated_at,
                       p.nom_agence as proprietaire_name,
                       c.taile_perimetre, c.type_conteneurs
                FROM boite_noir b
                LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
                LEFT JOIN conteneurs c ON b.id_conteneurs = c.id_conteneurs
                WHERE b.id_proprietaire = :owner_id AND COALESCE(b.archived, FALSE) = TRUE AND b.status = 'off'
                ORDER BY b.updated_at DESC
            """
            result = db.session.execute(text(query), {"owner_id": user_id})

        boxes = []
        for row in result:
            deployment = row.deployment_date
            duration_days = 30
            if row.expected_duration:
                try:
                    duration_str = str(row.expected_duration).split()[0]
                    duration_days = int(duration_str)
                except Exception:
                    pass

            end_date = deployment + timedelta(days=duration_days) if deployment else None
            if end_date and getattr(end_date, 'tzinfo', None) is None:
                end_date = end_date.replace(tzinfo=datetime.now().astimezone().tzinfo)

            boxes.append({
                "id_boite": row.id_boite,
                "container_id": row.id_conteneurs,
                "uuid": row.uuid_qrcode,
                "numero_serie": row.numero_serie,
                "type": row.type_boite,
                "version": row.versions,
                "battery": row.battery_level,
                "expected_duration": row.expected_duration,
                "deployment_date": row.deployment_date.isoformat() if row.deployment_date else None,
                "end_of_life_date": end_date.isoformat() if end_date else None,
                "status": row.status,
                "proprietaire": row.proprietaire_name,
                "container_type": row.type_conteneurs,
                "container_size": row.taile_perimetre,
                "archived": row.archived
            })

        return jsonify({"status": "success", "count": len(boxes), "boxes": boxes}), 200
    except Exception as e:
        print(f"[ERROR] BN archivées: {e}")
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  3️⃣ GÉNÉRER LE QR CODE D'UNE BOÎTE
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/black-boxes/<int:box_id>/assign", methods=["POST"])
def assign_box(box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès refusé"}), 403

    d = request.get_json() or {}
    container_id = d.get("id_conteneurs")
    if not container_id:
        return jsonify({"error": "Conteneur requis"}), 400

    proprietaire_id = user_id if role == "owner" else d.get("id_proprietaire")
    if not proprietaire_id:
        return jsonify({"error": "Entreprise requise"}), 400

    taken = db.session.execute(text("""
        SELECT 1 FROM boite_noir
        WHERE id_conteneurs = :c AND COALESCE(archived, FALSE) = FALSE
    """), {"c": container_id}).fetchone()
    if taken:
        return jsonify({"error": "Conteneur déjà assigné"}), 409

    if role == "owner":
        owner_check = db.session.execute(text(
            "SELECT id_proprietaire FROM boite_noir WHERE id_boite = :bid"
        ), {"bid": box_id}).scalar()
        if str(owner_check) != str(user_id):
            return jsonify({"error": "Accès refusé: boîte d'un autre propriétaire"}), 403

    db.session.execute(text("""
        UPDATE boite_noir
        SET id_conteneurs = :c, id_proprietaire = :p, status = 'active',
            archived = FALSE, deployment_date = NOW(), updated_at = NOW()
        WHERE id_boite = :b
    """), {"c": container_id, "p": proprietaire_id, "b": box_id})
    db.session.execute(text(
        "UPDATE conteneurs SET status = 'ok' WHERE id_conteneurs = :c"
    ), {"c": container_id})
    device_uid = db.session.execute(text("""
        SELECT d.device_uid FROM black_box_devices bbd
        JOIN iot_devices d ON d.id=bbd.device_id
        WHERE bbd.black_box_id=:box AND bbd.status='ACTIVE' LIMIT 1
    """), {"box": box_id}).scalar()
    if device_uid:
        _announce_single_box_connection(box_id, device_uid)
    db.session.commit()

    _sceller_evenement("BOITE_ASSIGNEE", box_id, {
        "id_conteneurs": container_id,
        "id_proprietaire": proprietaire_id
    })
    return jsonify({"status": "success"}), 200


@bb_bp.route("/api/black-boxes/available-for-assignment", methods=["GET"])
def available_black_boxes_for_assignment():
    """Boites disponibles pour une affectation a un conteneur ou une entreprise."""
    _ensure_archiving_schema()
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès refusé"}), 403

    company_id = request.args.get("company_id") or request.args.get("id_proprietaire")
    assignment_target = (request.args.get("target") or "container").strip().lower()
    if role == "owner":
        company_id = user_id

    # Une boîte peut déjà équiper un conteneur tout en restant sans entreprise.
    # Le formulaire de création d'entreprise doit donc filtrer sur le propriétaire,
    # et non sur le conteneur. Les autres écrans conservent le comportement historique.
    if assignment_target == "company":
        where = ["b.id_proprietaire IS NULL", "COALESCE(b.archived, FALSE) = FALSE"]
    else:
        where = ["b.id_conteneurs IS NULL", "COALESCE(b.archived, FALSE) = FALSE"]
    params = {}
    if role == "owner":
        where.append("CAST(b.id_proprietaire AS TEXT) = :company_id")
        params["company_id"] = str(company_id)
    elif company_id:
        where.append("(CAST(b.id_proprietaire AS TEXT) = :company_id OR b.id_proprietaire IS NULL)")
        params["company_id"] = str(company_id)

    rows = db.session.execute(text(f"""
        SELECT b.id_boite, b.numero_serie, b.id_proprietaire, b.status, b.archived,
               p.nom_agence
        FROM boite_noir b
        LEFT JOIN proprietaire_conteneur p ON p.id = b.id_proprietaire
        WHERE {" AND ".join(where)}
        ORDER BY b.id_proprietaire NULLS FIRST, b.id_boite
    """), params).fetchall()

    return jsonify([{
        "id_boite": r.id_boite,
        "numero_serie": r.numero_serie,
        "id_proprietaire": r.id_proprietaire,
        "proprietaire": r.nom_agence,
        "status": r.status,
        "archived": bool(r.archived),
        "unassigned_company": r.id_proprietaire is None,
        "label": f"{r.numero_serie or r.id_boite}"
                 f"{' - sans entreprise' if r.id_proprietaire is None else ''}"
                 f"{' - archivee' if r.archived else ''}",
    } for r in rows]), 200


@bb_bp.route("/api/containers/<container_id>/assign-black-box", methods=["POST"])
def assign_black_box_to_container(container_id):
    """Affecte une boite libre a un conteneur libre avec controle role/entreprise."""
    _ensure_archiving_schema()
    ensure_iot_schema()
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès refusé"}), 403
    data = request.get_json(silent=True) or {}
    box_id = data.get("box_id") or data.get("id_boite")
    company_id = data.get("company_id") or data.get("id_proprietaire")
    if role == "owner":
        company_id = user_id
    if not box_id:
        return jsonify({"error": "Boîte noire requise"}), 400

    try:
        with db.session.begin_nested():
            taken = db.session.execute(text("""
                SELECT 1 FROM boite_noir
                WHERE id_conteneurs = :container_id AND COALESCE(archived, FALSE) = FALSE
                LIMIT 1
            """), {"container_id": container_id}).fetchone()
            if taken:
                return jsonify({"error": "Ce conteneur possède déjà une boîte active"}), 409

            box = db.session.execute(text("""
                SELECT id_boite, id_conteneurs, id_proprietaire, archived
                FROM boite_noir
                WHERE id_boite = :box_id
                FOR UPDATE
            """), {"box_id": box_id}).fetchone()
            if not box:
                return jsonify({"error": "Boîte noire inexistante"}), 404
            if box.id_conteneurs:
                return jsonify({"error": "Cette boîte est déjà liée à un conteneur"}), 409
            if role == "owner" and str(box.id_proprietaire) != str(user_id):
                return jsonify({"error": "Boîte non attribuée à votre entreprise"}), 403
            if role == "superadmin" and box.id_proprietaire and company_id and str(box.id_proprietaire) != str(company_id):
                return jsonify({"error": "Boîte attribuée à une autre entreprise"}), 409

            db.session.execute(text("""
                UPDATE boite_noir
                SET id_conteneurs = :container_id,
                    id_proprietaire = COALESCE(id_proprietaire, :company_id),
                    status = 'active',
                    archived = FALSE,
                    deployment_date = COALESCE(deployment_date, NOW()),
                    updated_at = NOW()
                WHERE id_boite = :box_id
            """), {"container_id": container_id, "company_id": company_id, "box_id": box_id})
            db.session.execute(text("""
                UPDATE conteneurs SET status = 'ok' WHERE id_conteneurs = :container_id
            """), {"container_id": container_id})
            db.session.execute(text("""
                INSERT INTO black_box_container_assignments
                    (black_box_id, container_id, assigned_by, assigned_at, status)
                VALUES (:box_id, :container_id, :assigned_by, NOW(), 'ACTIVE')
            """), {"box_id": box_id, "container_id": container_id, "assigned_by": f"{role}:{user_id}"})
            device_uid = db.session.execute(text("""
                SELECT d.device_uid FROM black_box_devices bbd
                JOIN iot_devices d ON d.id=bbd.device_id
                WHERE bbd.black_box_id=:box AND bbd.status='ACTIVE' LIMIT 1
            """), {"box": box_id}).scalar()
            if device_uid:
                _announce_single_box_connection(box_id, device_uid)
        db.session.commit()
        _sceller_evenement("BOITE_CONTENEUR_ASSIGNEE", box_id, {
            "container_id": container_id,
            "company_id": company_id,
            "assigned_by": f"{role}:{user_id}",
        })
        return jsonify({"status": "success", "box_id": box_id, "container_id": container_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur assignation: {str(e)}"}), 500


@bb_bp.route("/api/black-boxes/<int:box_id>/detach-container", methods=["POST"])
def detach_black_box_container(box_id):
    """Detache une boite, garde le conteneur visible 48h et genere un rapport."""
    ensure_iot_schema()
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return jsonify({"error": "Accès refusé"}), 403
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") or "DETACHMENT"
    try:
        box = db.session.execute(text("""
            SELECT id_boite, id_conteneurs, id_proprietaire
            FROM boite_noir
            WHERE id_boite = :box_id
            FOR UPDATE
        """), {"box_id": box_id}).fetchone()
        if not box:
            return jsonify({"error": "Boîte inexistante"}), 404
        if role == "owner" and str(box.id_proprietaire) != str(user_id):
            return jsonify({"error": "Accès refusé"}), 403
        if not box.id_conteneurs:
            return jsonify({"error": "Boîte déjà détachée"}), 409

        container_id = box.id_conteneurs
        doc_uid = str(uuid.uuid4())
        from app.regulatory.history import record_decision
        identity = {"role": role, "user_id": user_id}
        record_decision(
            identity=identity, black_box_id=int(box_id), container_id=str(container_id),
            subject_type="report", subject_id=doc_uid, event_type="REPORT_GENERATED",
            action="Rapport de situation généré avant détachement",
            reaction="Le rapport conserve les mesures, l’historique et les références de source disponibles.",
            remarks={"report_uid": doc_uid, "reason": reason},
            source_keys=["ARGOS_AGENT_RULES"], applicability_status="NOT_ASSESSED",
        )
        pdf_bytes = generate_container_report_pdf(container_id)
        storage_key = f"generated_reports/container_{container_id}_{doc_uid}.pdf"
        stored = store_private_document(storage_key, pdf_bytes)

        db.session.execute(text("""
            INSERT INTO generated_reports
                (report_uid, category, title, container_id, black_box_id, storage_key, mime_type, size, created_at)
            VALUES
                (:uid, 'RAPPORT', :title, :container_id, :box_id, :storage_key, 'application/pdf', :size, NOW())
        """), {
            "uid": doc_uid,
            "title": f"Rapport avant detachement {container_id}",
            "container_id": container_id,
            "box_id": box_id,
            "storage_key": stored["storage_key"],
            "size": stored["size"],
        })
        db.session.execute(text("""
            UPDATE generated_reports SET checksum=:checksum WHERE report_uid=CAST(:uid AS uuid)
        """), {"checksum": stored["checksum"], "uid": doc_uid})
        db.session.execute(text("""
            UPDATE boite_noir SET id_conteneurs = NULL, status = 'unassigned', updated_at = NOW()
            WHERE id_boite = :box_id
        """), {"box_id": box_id})
        db.session.execute(text("""
            UPDATE black_box_container_assignments
            SET detached_at = NOW(), detached_by = :detached_by, reason = :reason,
                status = 'DETACHED', visibility_until = NOW() + INTERVAL '48 hours'
            WHERE black_box_id = :box_id AND container_id = :container_id AND status = 'ACTIVE'
        """), {
            "detached_by": f"{role}:{user_id}",
            "reason": reason,
            "box_id": box_id,
            "container_id": container_id,
        })
        db.session.execute(text("""
            INSERT INTO background_jobs (job_uid, job_type, payload, run_at)
            VALUES (CAST(:job_uid AS uuid), 'REVOKE_DETACHED_CONTAINER_ACCESS',
                    CAST(:payload AS jsonb), NOW() + INTERVAL '48 hours')
        """), {
            "job_uid": str(uuid.uuid4()),
            "payload": json.dumps({"container_id": container_id, "black_box_id": box_id, "report_uid": doc_uid}),
        })
        db.session.execute(text("""
            INSERT INTO notifications (type, message, cible_role, id_boite)
            VALUES ('CONTAINER_DETACHED', :message, 'all', :box_id)
        """), {"message": f"Conteneur {container_id} détaché. Rapport disponible.", "box_id": box_id})
        record_decision(
            identity=identity, black_box_id=int(box_id), container_id=str(container_id),
            subject_type="container_assignment", subject_id=str(box_id), event_type="CONTAINER_DETACHED",
            action="Boîte noire détachée du conteneur par un utilisateur autorisé",
            reaction=str(reason), remarks={"report_uid": doc_uid, "access_revocation": "scheduled_48h"},
            source_keys=["ARGOS_AGENT_RULES"], applicability_status="NOT_ASSESSED",
        )
        db.session.commit()
        return jsonify({
            "status": "success",
            "container_id": container_id,
            "report_uid": doc_uid,
            "access_revocation": "scheduled_48h",
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur détachement: {str(e)}"}), 500


@bb_bp.route("/api/reports/<report_uid>/download", methods=["GET"])
def download_generated_report(report_uid):
    role, user_id = get_caller_identity()
    report = db.session.execute(text("""
        SELECT r.*,b.id_proprietaire
        FROM generated_reports r
        LEFT JOIN boite_noir b ON b.id_boite=r.black_box_id
        WHERE r.report_uid=CAST(:uid AS uuid)
    """), {"uid": report_uid}).fetchone()
    if not report:
        return jsonify({"error": "Rapport introuvable"}), 404
    allowed = role == "superadmin" or (role == "owner" and str(report.id_proprietaire) == str(user_id))
    if not allowed and role in ("client", "driver", "company"):
        if role == "client":
            allowed = bool(db.session.execute(text("""
                SELECT 1 FROM abonner a WHERE a.id_cni=:uid AND a.id_boite=:box LIMIT 1
            """), {"uid": user_id, "box": report.black_box_id}).scalar())
        elif role == "driver":
            allowed = bool(db.session.execute(text("""
                SELECT 1 FROM colis co JOIN abonner a ON a.id_cni=co.id_cni_client
                WHERE co.id_cni_transporteur=:uid AND a.id_boite=:box LIMIT 1
            """), {"uid": user_id, "box": report.black_box_id}).scalar())
        else:
            allowed = bool(db.session.execute(text("""
                SELECT 1 FROM agence_abonnement WHERE CAST(id_agence AS TEXT)=:uid AND id_boite=:box LIMIT 1
            """), {"uid": user_id, "box": report.black_box_id}).scalar())
    if not allowed:
        return jsonify({"error": "Acces refuse"}), 403
    path = resolve_private_document(report.storage_key)
    if not path:
        return jsonify({"error": "Fichier du rapport indisponible"}), 410
    return send_file(path, mimetype=report.mime_type, as_attachment=True,
                     download_name=f"rapport_{report.container_id or report_uid}.pdf")


@bb_bp.route("/api/containers/<container_id>/report", methods=["GET"])
def export_container_report(container_id):
    """Export PDF complet d'un conteneur."""
    role, user_id = get_caller_identity()
    if not role:
        return jsonify({"error": "Authentification requise"}), 401
    try:
        from app.routes.workflows import _can_access_container
        if not _can_access_container(role, str(user_id), str(container_id)):
            return jsonify({"error": "Accès refusé à ce dossier"}), 403
        from app.extensions import db
        from app.regulatory.history import record_decision
        box_id = db.session.execute(text("""
            SELECT id_boite FROM boite_noir WHERE id_conteneurs=:container
            ORDER BY created_at DESC NULLS LAST LIMIT 1
        """), {"container": container_id}).scalar()
        report_uid = str(uuid.uuid4())
        record_decision(
            identity={"role": role, "user_id": user_id},
            black_box_id=int(box_id) if box_id else None,
            container_id=str(container_id), subject_type="report", subject_id=report_uid,
            event_type="REPORT_GENERATED", action="Rapport opérationnel conteneur généré",
            reaction="Le PDF inclut l’historique disponible et les références de source; aucune applicabilité juridique n’est inférée.",
            remarks={"report_uid": report_uid, "format": "application/pdf"},
            source_keys=["ARGOS_AGENT_RULES"], applicability_status="NOT_ASSESSED",
        )
        db.session.commit()
        pdf_bytes = generate_container_report_pdf(container_id)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"rapport_conteneur_{container_id}.pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Erreur rapport: {str(e)}"}), 500


@bb_bp.route("/api/black-boxes/resolve-qr", methods=["POST", "OPTIONS"])
def resolve_qr_box_access():
    """Résout l'accès QR après connexion et retourne l'action à exécuter."""
    if request.method == "OPTIONS":
        return jsonify({"status": "CORS_OK"}), 200

    role, user_id = get_caller_identity()
    if not role or not user_id:
        return jsonify({"error": "Authentification requise"}), 401
    if role not in ["superadmin", "owner"]:
        return jsonify({"error": "Accès réservé au superadmin ou propriétaire"}), 403

    data = request.get_json() or {}
    qr_uuid = (data.get("qr_uuid") or data.get("uuid") or "").strip()
    if not qr_uuid:
        return jsonify({"error": "UUID QR manquant"}), 400

    try:
        from uuid import UUID
        UUID(qr_uuid)
    except (ValueError, TypeError):
        if role == "superadmin":
            return jsonify({
                "status": "success",
                "action": "create",
                "context": {"container_id": None, "proprietaire_id": None}
            }), 200
        return jsonify({"error": "QR code invalide"}), 404

    try:
        box_data = db.session.execute(text("""
            SELECT b.id_boite, b.uuid_qrcode, b.numero_serie, b.id_conteneurs,
                   b.id_proprietaire, b.type_boite, b.versions, b.status, b.archived,
                   b.deployment_date, b.battery_level, b.expected_duration,
                   p.nom_agence
            FROM boite_noir b
            LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
            WHERE b.uuid_qrcode = :u LIMIT 1
        """), {"u": qr_uuid}).fetchone()

        if not box_data:
            if role == "superadmin":
                return jsonify({
                    "status": "success",
                    "action": "create",
                    "context": {"container_id": None, "proprietaire_id": None}
                }), 200
            return jsonify({"error": "Aucune boîte associée à ce QR code"}), 404

        if role == "owner" and str(box_data.id_proprietaire) != str(user_id):
            return jsonify({"error": "Vous n'êtes pas propriétaire de cette boîte"}), 403

        if box_data.status == "off" or box_data.archived:
            return jsonify({
                "status": "success",
                "action": "archived",
                "box": {
                    "id_boite": box_data.id_boite,
                    "numero_serie": box_data.numero_serie,
                    "container_id": box_data.id_conteneurs,
                    "status": box_data.status,
                    "archived": bool(box_data.archived),
                    "proprietaire": box_data.nom_agence,
                }
            }), 200

        if not box_data.id_conteneurs:
            companies = []
            if role == "superadmin":
                companies = [dict(r._mapping) for r in db.session.execute(text(
                    "SELECT id, nom_agence FROM proprietaire_conteneur ORDER BY nom_agence"
                )).fetchall()]
            containers = db.session.execute(text("""
                SELECT c.id_conteneurs, c.taile_perimetre, c.type_conteneurs
                FROM conteneurs c
                WHERE c.status = 'ok'
                  AND NOT EXISTS (
                      SELECT 1 FROM boite_noir b2
                      WHERE b2.id_conteneurs = c.id_conteneurs AND COALESCE(b2.archived, FALSE) = FALSE
                  )
            """)).fetchall()
            return jsonify({
                "status": "success",
                "action": "assign",
                "box": {"id_boite": box_data.id_boite, "numero_serie": box_data.numero_serie},
                "companies": companies,
                "containers": [{"id": r[0], "taile_perimetre": r[1], "type_conteneurs": r[2]} for r in containers],
                "is_owner": role == "owner",
            }), 200

        return jsonify({
            "status": "success",
            "action": "edit",
            "box": {
                "id_boite": box_data.id_boite,
                "numero_serie": box_data.numero_serie,
                "container_id": box_data.id_conteneurs,
                "status": box_data.status,
                "archived": bool(box_data.archived),
                "proprietaire": box_data.nom_agence,
                "type": box_data.type_boite,
                "version": box_data.versions,
                "deployment_date": box_data.deployment_date.isoformat() if box_data.deployment_date else None,
                "battery": box_data.battery_level,
                "expected_duration": box_data.expected_duration,
            }
        }), 200
    except Exception as e:
        print(f"[ERROR] QR resolution: {e}")
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


@bb_bp.route("/api/black-boxes/<int:box_id>/qrcode", methods=["GET"])
def get_qrcode(box_id):
    """
    Génère et retourne le QR code PNG d'une boîte noire
    """
    role, user_id = get_caller_identity()
    
    try:
        # Récupérer la boîte
        box_data = db.session.execute(text("""
            SELECT b.id_boite, b.uuid_qrcode, b.numero_serie, b.id_conteneurs,
                   b.id_proprietaire, b.type_boite, b.deployment_date,
                   p.nom_agence
            FROM boite_noir b
            LEFT JOIN proprietaire_conteneur p ON b.id_proprietaire = p.id
            WHERE b.id_boite = :id LIMIT 1
        """), {"id": box_id}).fetchone()
        
        if not box_data:
            return jsonify({"error": "Boîte noire inexistante"}), 404
        
        # Vérifier l'accès
        if role == "owner" and box_data.id_proprietaire != user_id:
            return jsonify({"error": "Accès refusé"}), 403
        
        scan_url = _build_qr_scan_url(box_data.uuid_qrcode)
        
        # Générer le QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(scan_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        response = send_file(
            img_io,
            mimetype='image/png',
            as_attachment=False,
            download_name=f'qrcode_{box_data.numero_serie}.png'
        )
        response.headers["X-QR-Scan-URL"] = scan_url
        response.headers["Cache-Control"] = "no-store"
        return response
        
    except Exception as e:
        print(f"[ERROR] QR Code: {e}")
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  4️⃣ WIFI SETTINGS - UPDATE
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/wifi/settings", methods=["POST"])
def update_wifi_settings():
    """
    Met à jour les paramètres WiFi de l'utilisateur
    Accepte: SSID + Password
    """
    role, user_id = get_caller_identity()
    data = request.get_json() or {}
    
    if not data.get("ssid") or not data.get("password"):
        return jsonify({"error": "SSID et mot de passe requis"}), 400
    
    try:
        # Mapper le rôle à la table correspondante
        table_mapping = {
            "superadmin": "superadmin",
            "owner": "proprietaire_conteneur",
            "company": "agence_utilisatrice",
            "client": "client",
            "driver": "transporteur",
            "port_authority": "port_authority_user"
        }
        
        table = table_mapping.get(role)
        if not table:
            return jsonify({"error": "Rôle non reconnu"}), 403
        
        # Mettre à jour
        db.session.execute(text(f"""
            UPDATE {table}
            SET wifi_name = :ssid, wifi_password = :pwd
            WHERE id = :uid
        """), {
            "ssid": data["ssid"],
            "pwd": data["password"],
            "uid": user_id
        })
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"✓ WiFi configuré: {data['ssid']}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] WiFi Update: {e}")
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  5️⃣ WIFI SETTINGS - GET
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/wifi/settings", methods=["GET"])
def get_wifi_settings():
    """
    Récupère les paramètres WiFi de l'utilisateur
    """
    role, user_id = get_caller_identity()
    
    try:
        table_mapping = {
            "superadmin": "superadmin",
            "owner": "proprietaire_conteneur",
            "company": "agence_utilisatrice",
            "client": "client",
            "driver": "transporteur",
            "port_authority": "port_authority_user"
        }
        
        table = table_mapping.get(role)
        if not table:
            return jsonify({"error": "Rôle non reconnu"}), 403
        
        # Récupérer
        result = db.session.execute(text(f"""
            SELECT wifi_name, wifi_password FROM {table}
            WHERE id = :uid LIMIT 1
        """), {"uid": user_id}).fetchone()
        
        if not result:
            return jsonify({
                "status": "success",
                "ssid": None,
                "password": None,
                "configured": False
            }), 200
        
        return jsonify({
            "status": "success",
            "ssid": result.wifi_name,
            "password": result.wifi_password,
            "configured": bool(result.wifi_name)
        }), 200
        
    except Exception as e:
        print(f"[ERROR] WiFi Get: {e}")
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  6️⃣ ARCHIVER UNE BOÎTE NOIRE
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/black-boxes/<int:box_id>/archive", methods=["POST"])
@bb_bp.route("/api/black-boxes/<int:box_id>", methods=["DELETE"])
def archive_black_box(box_id):
    """
    Archive une boîte noire et libère le conteneur lié
    - Marque la boîte comme archived=TRUE, status='off'
    - Libère le conteneur lié (status='ok' = en attente d'assignement)
    - Scelle l'événement dans la blockchain
    """
    # Initialiser schéma archivage
    _ensure_archiving_schema()
    
    role, user_id = get_caller_identity()
    
    if role not in ["superadmin", "owner"]:
        return jsonify({"error": "Accès refusé"}), 403
    
    try:
        # Vérifier accès owner
        if role == "owner":
            owner_check = db.session.execute(text("""
                SELECT id_proprietaire FROM boite_noir WHERE id_boite = :bid
            """), {"bid": box_id}).scalar()
            
            if str(owner_check) != str(user_id):
                return jsonify({"error": "Accès refusé: boîte d'un autre propriétaire"}), 403
        
        # Récupérer la boîte noire
        box_data = db.session.execute(text("""
            SELECT id_boite, id_conteneurs, numero_serie FROM boite_noir WHERE id_boite = :bid
        """), {"bid": box_id}).fetchone()
        
        if not box_data:
            return jsonify({"error": "Boîte noire inexistante"}), 404
        
        container_id = box_data.id_conteneurs
        numero_serie = box_data.numero_serie
        
        # Archiver la boîte: status='off' + archived=TRUE
        update_result = db.session.execute(text("""
            UPDATE boite_noir
            SET archived = TRUE, status = 'off', updated_at = NOW()
            WHERE id_boite = :bid
        """), {"bid": box_id})

        if update_result.rowcount == 0:
            db.session.rollback()
            return jsonify({"error": "Aucune boîte archivée: identifiant non modifié"}), 404
        
        # Libérer le conteneur: status='ok' (en attente d'assignement)
        if container_id:
            db.session.execute(text("""
                UPDATE conteneurs 
                SET status = 'ok'
                WHERE id_conteneurs = :cid
            """), {"cid": container_id})
        
        db.session.commit()

        # Sceller l'événement dans la blockchain après validation métier.
        try:
            _sceller_evenement("BOITE_SUPPRIMEE", box_id, {
                "id_boite": box_id,
                "numero_serie": numero_serie,
                "id_conteneurs": container_id,
                "deleted_by": f"{role}:{user_id}",
                "deleted_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"[WARN] Blockchain seal failed: {e}")
        
        return jsonify({
            "status": "success",
            "message": f"✓ Boîte '{numero_serie}' supprimée - Conteneur '{container_id}' libéré",
            "box_id": box_id,
            "numero_serie": numero_serie,
            "container_freed": container_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Archive boîte {box_id}: {e}")
        return jsonify({"error": f"Erreur archivage: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════
#  7️⃣ RESTAURER UNE BOÎTE NOIRE
# ═══════════════════════════════════════════════════════════════════

@bb_bp.route("/api/black-boxes/<int:box_id>/restore", methods=["POST"])
def restore_black_box(box_id):
    """
    Restaure une boîte noire archivée
    - Marque la boîte comme archived=FALSE, status='active'
    """
    role, user_id = get_caller_identity()
    
    if role not in ["superadmin", "owner"]:
        return jsonify({"error": "Accès refusé"}), 403
    
    try:
        # Vérifier accès
        if role == "owner":
            owner_check = db.session.execute(text(
                "SELECT id_proprietaire FROM boite_noir WHERE id_boite = :bid"
            ), {"bid": box_id}).scalar()
            
            if owner_check != user_id:
                return jsonify({"error": "Accès refusé"}), 403
        
        # Restaurer
        db.session.execute(text("""
            UPDATE boite_noir
            SET archived = FALSE, status = 'active', updated_at = NOW()
            WHERE id_boite = :bid
        """), {"bid": box_id})
        
        # Log: Sceller l'événement
        _sceller_evenement("BOITE_RESTAUREE", box_id, {
            "id_boite": box_id,
            "restored_at": datetime.now().isoformat()
        })
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "✓ Boîte restaurée"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Restore: {e}")
        return jsonify({"error": f"Erreur: {str(e)}"}), 500
