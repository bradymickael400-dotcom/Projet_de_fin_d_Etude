"""Blueprint Flask du module IoT."""

from datetime import datetime, timezone
import uuid
import threading

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import text

from app.modules.iot.iot_command_service import (
    apply_acknowledgement,
    create_device_command,
    get_command,
)
from app.modules.iot.iot_service import (
    IoTAuthError,
    enroll_device,
    get_device_status,
    ingest_telemetry,
    ingest_direct_telemetry,
    provision_device,
    authenticate_device,
)
from app.modules.iot.validator import PayloadValidationError
from app.utils import get_caller_identity, _sceller_evenement, send_email_background
from app.security import current_identity
from app.modules.iot.iot_event_service import _concerned_emails
from app.extensions import db
from app.modules.iot import repository as iot_repo
from app.services.storage_service import resolve_private_document, store_private_document

iot_bp = Blueprint("iot", __name__)


def _device_api_key():
    return request.headers.get("X-Device-Key", "")


def _json_error(message, status):
    return jsonify({"status": "error", "error": message}), status


def _manager_has_box_access(role, user_id, black_box_id):
    if role == "superadmin":
        return True
    if role == "owner":
        return bool(db.session.execute(text("""
            SELECT 1 FROM boite_noir WHERE id_boite=:box
              AND CAST(id_proprietaire AS TEXT)=:uid
        """), {"box": black_box_id, "uid": str(user_id)}).scalar())
    if role == "company":
        return bool(db.session.execute(text("""
            SELECT 1 FROM agence_abonnement WHERE id_boite=:box
              AND CAST(id_agence AS TEXT)=:uid AND COALESCE(status,'actif')='actif'
        """), {"box": black_box_id, "uid": str(user_id)}).scalar())
    return False


@iot_bp.route("/api/iot/devices/provision", methods=["POST"])
def api_provision_device():
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return _json_error("Acces refuse", 403)
    try:
        result = provision_device(request.get_json(silent=True) or {}, role, user_id)
        return jsonify({"status": "success", "device": result}), 201
    except Exception as exc:
        return _json_error(str(exc), 400)


@iot_bp.route("/api/iot/enroll", methods=["POST"])
def api_enroll_device():
    try:
        result = enroll_device(request.get_json(silent=True) or {}, request.remote_addr)
        return jsonify({"status": "success", "credentials": result}), 201
    except (PayloadValidationError, IoTAuthError) as exc:
        return _json_error(str(exc), 400)


@iot_bp.route("/api/iot/time", methods=["GET"])
def api_iot_time():
    """Horloge UTC de secours pour un ESP32 sur un LAN sans accès NTP."""
    now = datetime.now(timezone.utc)
    return jsonify({"epoch": int(now.timestamp()), "timestamp": now.isoformat()}), 200


@iot_bp.route("/api/iot/telemetry", methods=["POST"])
def api_iot_telemetry():
    payload = request.get_json(silent=True) or {}
    try:
        result = ingest_telemetry(payload, _device_api_key(), request.remote_addr)
        code = 200 if result.get("status") == "duplicate" else 201
        return jsonify(result), code
    except PayloadValidationError as exc:
        return _json_error(str(exc), 422)
    except IoTAuthError as exc:
        return _json_error(str(exc), 401)
    except Exception as exc:
        return _json_error(str(exc), 500)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/direct-telemetry", methods=["POST"])
def api_direct_wifi_telemetry(black_box_id):
    """Pont local navigateur: ARGOS-SETUP -> API -> Redis/PostgreSQL."""
    role, user_id = get_caller_identity()
    if not _manager_has_box_access(role, user_id, black_box_id):
        return _json_error("Acces direct refuse", 403)
    try:
        payload = request.get_json(silent=True) or {}
        # Le mode AP peut ne pas disposer de NTP. L'heure du navigateur/API
        # authentifiee sert alors d'horodatage de reception explicite.
        if not payload.get("timestamp"):
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        if not payload.get("messageId"):
            payload["messageId"] = str(uuid.uuid4())
        result = ingest_direct_telemetry(
            payload, black_box_id, role, user_id,
            request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "duplicate" else 201
    except PayloadValidationError as exc:
        return _json_error(str(exc), 422)
    except IoTAuthError as exc:
        return _json_error(str(exc), 401)
    except Exception as exc:
        return _json_error(str(exc), 500)


@iot_bp.route("/api/iot/acknowledgements", methods=["POST"])
def api_iot_acknowledgements():
    try:
        result = apply_acknowledgement(request.get_json(silent=True) or {}, _device_api_key())
        return jsonify({"status": "success", "command": result}), 200
    except PayloadValidationError as exc:
        return _json_error(str(exc), 422)
    except IoTAuthError as exc:
        return _json_error(str(exc), 401)


@iot_bp.route("/api/iot/audio", methods=["POST"])
def api_iot_audio():
    device_uid = (request.form.get("deviceUid") or "").strip()
    audio = request.files.get("audio")
    allowed_types = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/ogg", "audio/webm", "audio/mp4"}
    if not device_uid or not audio:
        return _json_error("deviceUid et fichier audio requis", 400)
    if audio.mimetype not in allowed_types:
        return _json_error("Type audio refuse", 415)
    content = audio.read(int(current_app.config["MAX_AUDIO_BYTES"]) + 1)
    if len(content) > int(current_app.config["MAX_AUDIO_BYTES"]):
        return _json_error("Fichier audio trop volumineux", 413)
    try:
        device = authenticate_device(device_uid, _device_api_key())
        relation = iot_repo.get_active_black_box_for_device(device.id)
        recording_uid = str(uuid.uuid4())
        extension = {"audio/mpeg":"mp3","audio/wav":"wav","audio/x-wav":"wav","audio/ogg":"ogg","audio/webm":"webm","audio/mp4":"m4a"}[audio.mimetype]
        stored = store_private_document(f"audio/{device_uid}/{recording_uid}.{extension}", content)
        started_at = request.form.get("startedAt") or None
        db.session.execute(text("""
            INSERT INTO audio_recordings(recording_uid,device_id,black_box_id,container_id,event_uid,
                duration_seconds,started_at,storage_key,mime_type,size_bytes,checksum_sha256)
            VALUES(CAST(:uid AS uuid),:device,:box,:container,CAST(NULLIF(:event,'') AS uuid),
                :duration,CAST(NULLIF(:started,'') AS timestamptz),:key,:mime,:size,:checksum)
        """), {"uid":recording_uid,"device":device.id,
                "box":relation.black_box_id if relation else None,"container":relation.container_id if relation else None,
                "event":request.form.get("eventUid") or "","duration":request.form.get("durationSeconds") or None,
                "started":started_at or "","key":stored["storage_key"],"mime":audio.mimetype,
                "size":stored["size"],"checksum":stored["checksum"]})
        db.session.commit()
        return jsonify({"status":"success","recordingUid":recording_uid,
                        "blackBoxId":relation.black_box_id if relation else None}), 201
    except IoTAuthError as exc:
        db.session.rollback()
        return _json_error(str(exc),401)
    except Exception:
        db.session.rollback()
        return _json_error("Enregistrement audio impossible",500)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/direct-audio", methods=["POST"])
def api_direct_audio(black_box_id):
    """Stocke un son capturé par le navigateur pendant une session Wi-Fi directe."""
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner", "company") or not _manager_has_box_access(role, user_id, black_box_id):
        return _json_error("Acces audio refuse", 403)
    audio = request.files.get("audio")
    if not audio:
        return _json_error("Fichier audio requis", 400)
    mime_type = str(audio.mimetype or "").split(";", 1)[0].lower()
    extensions = {"audio/mpeg":"mp3", "audio/wav":"wav", "audio/x-wav":"wav",
                  "audio/ogg":"ogg", "audio/webm":"webm", "audio/mp4":"m4a"}
    if mime_type not in extensions:
        return _json_error("Type audio refuse", 415)
    content = audio.read(int(current_app.config["MAX_AUDIO_BYTES"]) + 1)
    if len(content) > int(current_app.config["MAX_AUDIO_BYTES"]):
        return _json_error("Fichier audio trop volumineux", 413)
    device = iot_repo.find_registered_black_box_device(black_box_id)
    if not device:
        return _json_error("ESP32 associe introuvable", 404)
    try:
        recording_uid = str(uuid.uuid4())
        stored = store_private_document(
            f"audio/{device.device_uid}/{recording_uid}.{extensions[mime_type]}", content)
        db.session.execute(text("""
            INSERT INTO audio_recordings(recording_uid,device_id,black_box_id,container_id,
                duration_seconds,started_at,storage_key,mime_type,size_bytes,checksum_sha256)
            VALUES(CAST(:uid AS uuid),:device,:box,:container,:duration,
                CAST(NULLIF(:started,'') AS timestamptz),:key,:mime,:size,:checksum)
        """), {
            "uid": recording_uid, "device": device.id, "box": black_box_id,
            "container": device.container_id,
            "duration": request.form.get("durationSeconds") or None,
            "started": request.form.get("startedAt") or "",
            "key": stored["storage_key"], "mime": mime_type,
            "size": stored["size"], "checksum": stored["checksum"],
        })
        db.session.commit()
        return jsonify({"status":"success", "recordingUid":recording_uid,
                        "audioUrl":f"/api/audio/{recording_uid}"}), 201
    except Exception:
        db.session.rollback()
        return _json_error("Enregistrement audio direct impossible", 500)


@iot_bp.route("/api/audio/<recording_uid>", methods=["GET"])
def api_get_audio(recording_uid):
    role,user_id = get_caller_identity()
    row = db.session.execute(text("SELECT * FROM audio_recordings WHERE recording_uid=CAST(:uid AS uuid)"),{"uid":recording_uid}).fetchone()
    if not row:
        return _json_error("Enregistrement introuvable",404)
    allowed = role == "superadmin"
    if role == "owner":
        allowed = bool(db.session.execute(text("SELECT 1 FROM boite_noir WHERE id_boite=:box AND CAST(id_proprietaire AS TEXT)=:uid"),{"box":row.black_box_id,"uid":user_id}).scalar())
    elif role == "company":
        allowed = _manager_has_box_access(role, user_id, row.black_box_id)
    elif role == "client":
        allowed = bool(db.session.execute(text("SELECT 1 FROM abonner WHERE id_boite=:box AND id_cni=:uid"),{"box":row.black_box_id,"uid":user_id}).scalar())
    elif role == "driver":
        allowed = bool(db.session.execute(text("""SELECT 1 FROM colis co JOIN abonner a ON a.id_cni=co.id_cni_client WHERE co.id_cni_transporteur=:uid AND a.id_boite=:box"""),{"box":row.black_box_id,"uid":user_id}).scalar())
    if not allowed:
        return _json_error("Acces refuse",403)
    path = resolve_private_document(row.storage_key)
    if not path:
        return _json_error("Fichier audio indisponible",410)
    return send_file(path,mimetype=row.mime_type,as_attachment=False)


@iot_bp.route("/api/iot/devices/<device_uid>/commands", methods=["GET"])
def api_iot_device_commands(device_uid):
    try:
        device = authenticate_device(device_uid, _device_api_key())
    except IoTAuthError as exc:
        return _json_error(str(exc), 401)

    commands = []
    for command in iot_repo.list_device_commands(device.id, limit=10):
        commands.append({
            "commandUid": str(command.command_uid),
            "type": command.command_type,
            "payload": command.payload,
            "status": command.status,
            "createdAt": command.created_at.isoformat() if command.created_at else None,
            "expiresAt": command.expires_at.isoformat() if command.expires_at else None,
        })
    return jsonify({"status": "success", "commands": commands}), 200


@iot_bp.route("/api/iot/devices/<device_uid>/status", methods=["GET"])
def api_iot_device_status(device_uid):
    status = get_device_status(device_uid)
    if not status:
        return _json_error("Prototype introuvable", 404)
    return jsonify(status), 200


@iot_bp.route("/api/black-boxes/<int:black_box_id>/commands/security", methods=["POST"])
def api_command_security(black_box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner", "company"):
        return _json_error("Acces refuse", 403)
    if not _manager_has_box_access(role, user_id, black_box_id):
        return _json_error("Cette boite ne fait pas partie de votre perimetre", 403)

    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("enabled"), bool):
        return _json_error("enabled booleen requis", 422)
    enabled = data["enabled"]
    registered_device = iot_repo.find_registered_black_box_device(black_box_id)
    latitude, longitude, accuracy = data.get("latitude"), data.get("longitude"), data.get("accuracy")
    if latitude is not None and longitude is not None:
        try:
            latitude, longitude = float(latitude), float(longitude)
            accuracy = float(accuracy or 0)
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
            if registered_device:
                db.session.execute(text("""
                    INSERT INTO positions(device_id,black_box_id,container_id,latitude,longitude,
                                          accuracy,speed,heading,source,measured_at)
                    VALUES(:device,:box,:container,:lat,:lon,:accuracy,0,0,
                           'BROWSER_FALLBACK',NOW())
                """), {"device": registered_device.id, "box": black_box_id,
                        "container": registered_device.container_id, "lat": latitude,
                        "lon": longitude, "accuracy": accuracy})
        except (TypeError, ValueError):
            return _json_error("Coordonnees navigateur invalides", 400)

    try:
        if str(data.get("delivery") or "remote").lower() == "direct":
            command = {"type": "SET_SECURITY_MODE", "status": "APPLIED_LOCALLY",
                       "blackBoxId": black_box_id, "payload": {"enabled": enabled}}
        else:
            command = create_device_command(
                black_box_id, "SET_SECURITY_MODE", {"enabled": enabled}, user_id
            )
        identity = current_identity()
        actor_name = str(identity.get("display_name") or identity.get("login") or user_id)
        role_names = {"superadmin": "Superadministrateur", "owner": "Gestionnaire propriétaire",
                      "company": "Gestionnaire entreprise"}
        actor_position = role_names.get(role, role)
        action = "activé" if enabled else "désactivé"
        timestamp = datetime.now(timezone.utc)
        message = (f"Mode sécurité {action} par {actor_name} "
                   f"({actor_position}) le {timestamp.strftime('%d/%m/%Y à %H:%M:%S UTC')}")
        db.session.execute(text("""
            INSERT INTO evenement_save
                (id_boite,device_uid,horodatage,log_action,lat,lon)
            VALUES(:box,:device_uid,:ts,:message,:lat,:lon)
        """), {"box": black_box_id, "ts": timestamp, "message": message,
                "lat": latitude, "lon": longitude,
                "device_uid": registered_device.device_uid if registered_device else None})
        db.session.execute(text("""
            INSERT INTO notifications
                (type,message,cible_role,id_boite,initiator_id,device_uid)
            VALUES('SECURITY_MODE',:message,'all',:box,:actor,:device_uid)
        """), {"message": message, "box": black_box_id,
                "actor": f"{role}:{user_id}",
                "device_uid": registered_device.device_uid if registered_device else None})
        seal_payload = {
            "enabled": enabled, "actor_id": user_id, "actor_name": actor_name,
            "actor_role": role, "actor_position": actor_position,
            "timestamp": timestamp.isoformat(), "latitude": latitude, "longitude": longitude,
        }
        # L'événement et la notification restent durables même si l'ancrage
        # cryptographique externe rencontre ensuite une panne indépendante.
        db.session.commit()
        _sceller_evenement("SECURITY_MODE_CHANGED", black_box_id, seal_payload)
        emails = _concerned_emails(black_box_id)
        if emails:
            threading.Thread(target=send_email_background,
                             args=(emails, "Changement du mode sécurité ARGOS", message),
                             daemon=True).start()
        return jsonify({"status": "success", "command": command,
                        "event": {"message": message, "timestamp": timestamp.isoformat()}}), 202
    except PayloadValidationError as exc:
        db.session.rollback()
        return _json_error(str(exc), 400)
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/commands/listening", methods=["POST"])
def api_command_listening(black_box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return _json_error("Acces refuse", 403)
    return _audited_audio_command(black_box_id, "SET_AUDIO_LISTENING", "ECOUTE_AUDIO", role, user_id)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/commands/recording", methods=["POST"])
def api_command_recording(black_box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return _json_error("Acces refuse", 403)
    return _audited_audio_command(black_box_id, "SET_AUDIO_RECORDING", "ENREGISTREMENT_AUDIO", role, user_id)


def _audited_audio_command(black_box_id, command_type, event_type, role, user_id):
    if not _manager_has_box_access(role, user_id, black_box_id):
        return _json_error("Cette boite ne fait pas partie de votre perimetre", 403)
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("enabled"), bool):
        return _json_error("enabled booleen requis", 422)
    enabled = data["enabled"]
    try:
        duration = max(0, min(int(data.get("durationSeconds") or 0), 86400))
    except (TypeError, ValueError):
        return _json_error("durationSeconds invalide", 422)
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if latitude is not None and longitude is not None:
        try:
            latitude, longitude = float(latitude), float(longitude)
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
        except (TypeError, ValueError):
            return _json_error("Coordonnees invalides", 422)
    payload = {"enabled": enabled, "durationSeconds": duration,
               "latitude": latitude, "longitude": longitude}
    try:
        command = create_device_command(black_box_id, command_type, payload, user_id)
        identity = current_identity()
        actor_name = str(identity.get("display_name") or identity.get("login") or user_id)
        timestamp = datetime.now(timezone.utc)
        action = "active" if enabled else "desactive"
        message = (f"{event_type.replace('_', ' ').title()} {action} par {actor_name}"
                   f" le {timestamp.strftime('%d/%m/%Y à %H:%M:%S UTC')}"
                   + (f" pour {duration} seconde(s)" if enabled and duration else ""))
        db.session.execute(text("""
            INSERT INTO evenement_save(id_boite,horodatage,log_action,lat,lon)
            VALUES(:box,:ts,:message,:lat,:lon)
        """), {"box": black_box_id, "ts": timestamp, "message": message,
                "lat": latitude, "lon": longitude})
        db.session.commit()
        _sceller_evenement(f"{event_type}_{'ACTIVEE' if enabled else 'DESACTIVEE'}", black_box_id, {
            "actor_id": user_id, "actor_name": actor_name, "actor_role": role,
            "enabled": enabled, "duration_seconds": duration,
            "latitude": latitude, "longitude": longitude,
            "timestamp": timestamp.isoformat(),
        })
        return jsonify({"status": "success", "command": command,
                        "event": {"message": message, "timestamp": timestamp.isoformat()}}), 202
    except PayloadValidationError as exc:
        db.session.rollback()
        return _json_error(str(exc), 400)
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/commands/flame-detection", methods=["POST"])
def api_command_flame_detection(black_box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return _json_error("Acces refuse", 403)
    enabled = bool((request.get_json(silent=True) or {}).get("enabled"))
    return _command(black_box_id, "SET_FLAME_DETECTION", {"enabled": enabled}, user_id)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/commands/request-position", methods=["POST"])
def api_command_request_position(black_box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner", "client", "driver"):
        return _json_error("Acces refuse", 403)
    return _command(black_box_id, "REQUEST_POSITION", {}, user_id)


@iot_bp.route("/api/black-boxes/<int:black_box_id>/commands/distance-threshold", methods=["POST"])
def api_command_distance_threshold(black_box_id):
    role, user_id = get_caller_identity()
    if role not in ("superadmin", "owner"):
        return _json_error("Acces refuse", 403)
    value = (request.get_json(silent=True) or {}).get("distanceCm")
    try:
        distance_cm = float(value)
    except (TypeError, ValueError):
        return _json_error("distanceCm numerique requis", 400)
    if distance_cm < 5 or distance_cm > 400:
        return _json_error("distanceCm doit etre compris entre 5 et 400 cm", 400)
    return _command(
        black_box_id,
        "SET_DISTANCE_THRESHOLD",
        {"distanceCm": distance_cm},
        user_id,
    )


@iot_bp.route("/api/commands/<command_uid>", methods=["GET"])
def api_get_command(command_uid):
    command = get_command(command_uid)
    if not command:
        return _json_error("Commande introuvable", 404)
    return jsonify(command), 200


def _command(black_box_id, command_type, payload, user_id):
    try:
        command = create_device_command(black_box_id, command_type, payload, user_id)
        return jsonify({"status": "success", "command": command}), 202
    except PayloadValidationError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        return _json_error(str(exc), 500)
