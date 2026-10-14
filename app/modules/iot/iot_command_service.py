"""Creation, publication et suivi des commandes ESP32."""

import os
import uuid
from datetime import timedelta

from app.extensions import db
from app.modules.iot import repository as repo
from app.modules.iot.transport import build_transport
from app.modules.iot.types import COMMAND_STATUSES, SUPPORTED_COMMANDS
from app.modules.iot.validator import PayloadValidationError, validate_ack_payload


def create_device_command(
    black_box_id,
    command_type,
    payload,
    requested_by_user_id=None,
    allow_fallback=True,
):
    repo.ensure_iot_schema()
    if command_type not in SUPPORTED_COMMANDS:
        raise PayloadValidationError("Commande non supportee")
    device = repo.find_black_box_device(black_box_id)
    if not device and allow_fallback:
        device = repo.ensure_fallback_device_for_black_box(black_box_id)
    if not repo.is_device_usable(device):
        raise PayloadValidationError("Boite noire sans prototype ESP32 actif")
    ttl = int(os.getenv("IOT_COMMAND_TTL_SECONDS") or "120")
    command_uid = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    expires_at = repo.now_utc() + timedelta(seconds=ttl)
    command = repo.create_command(
        command_uid=command_uid,
        device_id=device.id,
        black_box_id=black_box_id,
        container_id=device.container_id,
        user_id=requested_by_user_id,
        command_type=command_type,
        payload=payload or {},
        expires_at=expires_at,
        correlation_id=correlation_id,
    )
    command_payload = {
        "commandUid": command_uid,
        "deviceUid": device.device_uid,
        "type": command_type,
        "payload": payload or {},
        "requestedAt": command.created_at.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "correlationId": correlation_id,
    }
    build_transport().publish_command(device.device_uid, command_payload)
    command = repo.mark_command_published(command_uid)
    repo.create_audit(
        "IOT_COMMAND_PUBLISHED",
        "device_command",
        command_uid,
        {"black_box_id": black_box_id, "command_type": command_type},
        None,
        requested_by_user_id,
    )
    db.session.commit()
    return serialize_command(command, device.device_uid)


def apply_acknowledgement(payload, api_key):
    repo.ensure_iot_schema()
    ack = validate_ack_payload(payload)
    if ack["status"] not in COMMAND_STATUSES:
        raise PayloadValidationError("Statut de commande invalide")
    from app.modules.iot.iot_service import authenticate_device

    device = authenticate_device(ack["deviceUid"], api_key)
    command = repo.find_command(ack["commandUid"])
    if not command or command.device_id != device.id:
        raise PayloadValidationError("Commande introuvable pour ce prototype")
    updated = repo.update_command_from_ack(
        ack["commandUid"],
        ack["deviceUid"],
        ack["status"],
        ack.get("result"),
        ack.get("errorCode") or ack.get("error_code"),
        ack.get("errorMessage") or ack.get("error_message"),
    )
    repo.create_audit(
        "IOT_COMMAND_ACK",
        "device_command",
        ack["commandUid"],
        {"status": ack["status"]},
    )
    db.session.commit()
    return serialize_command(updated, device.device_uid)


def get_command(command_uid):
    repo.ensure_iot_schema()
    command = repo.find_command(command_uid)
    if not command:
        return None
    return serialize_command(command, command.device_uid)


def serialize_command(command, device_uid=None):
    return {
        "commandUid": str(command.command_uid),
        "deviceUid": device_uid,
        "blackBoxId": command.black_box_id,
        "containerId": command.container_id,
        "type": command.command_type,
        "payload": command.payload,
        "status": command.status,
        "createdAt": command.created_at.isoformat() if command.created_at else None,
        "publishedAt": command.published_at.isoformat() if command.published_at else None,
        "acknowledgedAt": command.acknowledged_at.isoformat() if command.acknowledged_at else None,
        "executedAt": command.executed_at.isoformat() if command.executed_at else None,
        "failedAt": command.failed_at.isoformat() if command.failed_at else None,
        "expiresAt": command.expires_at.isoformat() if command.expires_at else None,
        "errorCode": command.error_code,
        "errorMessage": command.error_message,
        "retryCount": command.retry_count,
    }
