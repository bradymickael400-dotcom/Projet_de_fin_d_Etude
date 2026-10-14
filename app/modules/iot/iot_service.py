"""Service d'enrolement et d'ingestion IoT."""

import uuid
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.modules.iot import repository as repo
from app.modules.iot.normalizer import (
    normalize_telemetry_quality,
    telemetry_to_event_payload,
)
from app.modules.iot.security import generate_secret, hash_secret, verify_secret
from app.modules.iot.types import DEVICE_ACTIVE, DEVICE_PENDING, DEVICE_REVOKED
from app.modules.iot.validator import PayloadValidationError, validate_telemetry_payload
from app.modules.iot.iot_event_service import (
    add_configured_threshold_alerts,
    create_threshold_notifications,
)
from app.modules.iot.telemetry_cache import publish as publish_telemetry


class IoTAuthError(PermissionError):
    pass


def provision_device(data, actor_role=None, actor_id=None, commit=True):
    repo.ensure_iot_schema(commit=commit)
    raw_device_uid = str(data.get("device_uid") or data.get("deviceUid") or "").strip()
    if raw_device_uid:
        device_uid = raw_device_uid if raw_device_uid.startswith("ARGOS-ESP32-") else f"ARGOS-ESP32-{raw_device_uid}"
    else:
        device_uid = f"ARGOS-ESP32-{uuid.uuid4().hex[:8].upper()}"
    raw_token = generate_secret(24)
    expires_at = repo.now_utc() + timedelta(hours=int(data.get("enrollment_ttl_hours") or 24))
    device = repo.create_pending_device(
        device_uid=device_uid,
        token_hash=hash_secret(raw_token),
        hardware_serial=data.get("hardware_serial"),
        firmware_version=data.get("firmware_version"),
        protocol_version=data.get("protocol_version") or "1.0",
        expires_at=expires_at,
    )
    black_box_id = data.get("black_box_id")
    if black_box_id:
        db.session.execute(
            text("INSERT INTO black_box_devices (black_box_id, device_id, assigned_by) VALUES (:bid, :did, :by)"),
            {"bid": black_box_id, "did": device.id, "by": f"{actor_role}:{actor_id}"},
        )
    repo.create_audit(
        "IOT_DEVICE_PROVISIONED",
        "iot_device",
        device_uid,
        {"hardware_serial": data.get("hardware_serial"), "black_box_id": black_box_id},
        actor_role,
        actor_id,
    )
    if commit:
        db.session.commit()
    return {
        "deviceUid": device_uid,
        "enrollmentToken": raw_token,
        "expiresAt": expires_at.isoformat(),
        "status": DEVICE_PENDING,
    }


def enroll_device(payload, remote_addr=None):
    repo.ensure_iot_schema()
    device_uid = (payload.get("deviceUid") or payload.get("device_uid") or "").strip()
    token = payload.get("enrollmentToken") or payload.get("enrollment_token")
    if not device_uid or not token:
        raise PayloadValidationError("deviceUid et enrollmentToken requis")
    device = repo.find_device(device_uid)
    if not device:
        repo.create_audit("IOT_ENROLL_UNKNOWN_DEVICE", "iot_device", device_uid, {}, None, None)
        db.session.commit()
        raise IoTAuthError("Prototype inconnu")
    if device.status == DEVICE_REVOKED:
        raise IoTAuthError("Prototype revoque")
    if device.status == DEVICE_ACTIVE:
        raise IoTAuthError("Prototype deja actif")
    if device.enrollment_expires_at and device.enrollment_expires_at < repo.now_utc():
        raise IoTAuthError("Jeton d'enrolement expire")
    if not verify_secret(token, device.enrollment_token_hash):
        repo.create_audit("IOT_ENROLL_BAD_TOKEN", "iot_device", device_uid, {}, None, None)
        db.session.commit()
        raise IoTAuthError("Jeton d'enrolement invalide")
    api_key = generate_secret(32)
    activated = repo.activate_device(device.id, hash_secret(api_key), remote_addr)
    relation = repo.get_active_black_box_for_device(device.id)
    repo.create_audit("IOT_DEVICE_ENROLLED", "iot_device", device_uid, {}, None, None)
    db.session.commit()
    return {
        "deviceUid": activated.device_uid,
        "apiKey": api_key,
        "status": DEVICE_ACTIVE,
        "blackBoxId": relation.black_box_id if relation else None,
        "containerId": relation.container_id if relation else None,
    }


def authenticate_device(device_uid, api_key):
    device = repo.find_device(device_uid)
    if not device:
        raise IoTAuthError("Prototype inconnu")
    if device.status == DEVICE_REVOKED:
        raise IoTAuthError("Prototype revoque")
    if device.status != DEVICE_ACTIVE:
        raise IoTAuthError("Prototype non actif")
    if not verify_secret(api_key, device.credential_hash):
        raise IoTAuthError("Cle appareil invalide")
    return device


def _validate_binding_and_sequence(validated, device, relation):
    last_sequence = (device.metadata or {}).get("last_sequence") if hasattr(device, "metadata") else None
    if last_sequence is not None and validated["sequence"] <= int(last_sequence):
        raise PayloadValidationError("sequence deja traitee ou obsolete")
    if not relation:
        raise IoTAuthError("Prototype non affecte a une boite noire")
    if int(validated["black_box_id"]) != int(relation.black_box_id):
        raise IoTAuthError("blackBoxId refuse: identite de boite incorrecte")
    if relation.container_id and str(validated["container_id"] or "").upper() != str(relation.container_id).upper():
        raise IoTAuthError("containerId refuse: ce prototype est affecte a un autre conteneur")


def _persist_validated_telemetry(validated, raw_id, device, relation, remote_addr=None,
                                 audit_action="IOT_TELEMETRY_RECEIVED", actor_role=None,
                                 actor_id=None):
    """Pipeline commun : Redis temps reel, evenements, alertes, PostgreSQL."""
    _validate_binding_and_sequence(validated, device, relation)
    repo.apply_fallback_position(validated, relation)
    validated = normalize_telemetry_quality(validated)
    event_payload = telemetry_to_event_payload(validated)
    add_configured_threshold_alerts(
        event_payload, repo.get_alert_thresholds(relation.black_box_id)
    )
    cache_result = publish_telemetry(
        validated, event_payload, relation.black_box_id, relation.container_id
    )
    repo.insert_sensor_and_position(raw_id, device, relation, event_payload, validated)
    repo.touch_device(device.id, validated["sequence"], remote_addr)
    if event_payload.get("notif"):
        create_threshold_notifications(
            relation.black_box_id, event_payload["notif"],
            device.device_uid, validated["sequence"],
        )
    repo.create_audit(
        audit_action, "iot_device", device.device_uid,
        {"message_id": validated["message_id"], "sequence": validated["sequence"],
         "assignment_status": "ASSIGNED" if relation.container_id else "UNASSIGNED",
         "source": validated["position"].get("source", "ESP32")},
        actor_role, actor_id,
    )
    db.session.commit()
    opening_alert = event_payload.get("alert") or {}
    if opening_alert.get("raised") and opening_alert.get("label") == "OUVERTURE_CONTENEUR":
        from app.utils import _sceller_evenement
        _sceller_evenement("CONTAINER_OPENED", relation.black_box_id, {
            "device_uid": device.device_uid,
            "sequence": validated["sequence"],
            "label": opening_alert.get("label"),
            "occurred_at": opening_alert.get("occurredAt") or validated["timestamp"].isoformat(),
            "distance_cm": opening_alert.get("distanceCm"),
            "threshold_cm": opening_alert.get("thresholdCm"),
            "latitude": validated["position"].get("latitude"),
            "longitude": validated["position"].get("longitude"),
            "automatic_listening": opening_alert.get("automaticListening", False),
        })
    return {
        "status": "success", "rawMessageId": raw_id, "deviceUid": device.device_uid,
        "blackBoxId": relation.black_box_id, "containerId": relation.container_id,
        "assignmentStatus": "ASSIGNED" if relation.container_id else "UNASSIGNED",
        "events": event_payload.get("notif") or [], "realtime": cache_result,
        "source": "DIRECT_WIFI" if audit_action == "IOT_DIRECT_TELEMETRY_RECEIVED" else "ESP32",
    }


def ingest_telemetry(payload, api_key, remote_addr=None):
    repo.ensure_iot_schema()
    raw_id = None
    try:
        validated = validate_telemetry_payload(payload)
        raw_id = repo.insert_raw_message(payload, "telemetry", remote_addr, "VALIDATED")
        device = authenticate_device(validated["device_uid"], api_key)
        relation = repo.get_active_black_box_for_device(device.id)
        return _persist_validated_telemetry(
            validated, raw_id, device, relation, remote_addr
        )
    except IntegrityError:
        db.session.rollback()
        return {"status": "duplicate", "message": "messageId deja traite"}
    except Exception:
        db.session.rollback()
        if raw_id is None:
            try:
                repo.insert_raw_message(payload or {}, "telemetry", remote_addr, "REJECTED", "validation/auth failed")
                db.session.commit()
            except Exception:
                db.session.rollback()
        raise


def ingest_direct_telemetry(payload, black_box_id, actor_role, actor_id, remote_addr=None):
    """Ingestion depuis le pont navigateur connecte a ARGOS-SETUP.

    Le navigateur doit etre authentifie dans ARGOS et le deviceUid local doit
    correspondre a l'association serveur. La cle appareil n'est jamais exposee
    au navigateur.
    """
    repo.ensure_iot_schema()
    raw_id = None
    try:
        validated = validate_telemetry_payload(payload)
        reported_position_source = str(
            (payload.get("position") or {}).get("source")
            or payload.get("positionSource")
            or ""
        ).upper()
        validated["position"]["source"] = (
            "BROWSER_FALLBACK"
            if reported_position_source == "BROWSER_FALLBACK"
            else "DIRECT_WIFI"
        )
        if int(validated["black_box_id"]) != int(black_box_id):
            raise IoTAuthError("Boite directe incorrecte")
        device = repo.find_device(validated["device_uid"])
        if not device or device.status == DEVICE_REVOKED:
            raise IoTAuthError("Prototype direct inconnu ou revoque")
        relation = repo.get_active_black_box_for_device(device.id)
        _validate_binding_and_sequence(validated, device, relation)
        raw_id = repo.insert_raw_message(payload, "direct_wifi_telemetry", remote_addr, "VALIDATED")
        return _persist_validated_telemetry(
            validated, raw_id, device, relation, remote_addr,
            "IOT_DIRECT_TELEMETRY_RECEIVED", actor_role, actor_id,
        )
    except IntegrityError:
        db.session.rollback()
        return {"status": "duplicate", "message": "messageId deja traite"}
    except Exception:
        db.session.rollback()
        raise


def get_device_status(device_uid):
    repo.ensure_iot_schema()
    device = repo.find_device(device_uid)
    if not device:
        return None
    relation = repo.get_active_black_box_for_device(device.id)
    return {
        "deviceUid": device.device_uid,
        "status": device.status,
        "lastSeenAt": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "firmwareVersion": device.firmware_version,
        "protocolVersion": device.protocol_version,
        "blackBoxId": relation.black_box_id if relation else None,
        "containerId": relation.container_id if relation else None,
    }
