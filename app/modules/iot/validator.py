"""Validation stricte des messages IoT entrants."""

from datetime import datetime, timezone, timedelta
import math
from uuid import UUID

MAX_CLOCK_SKEW = timedelta(hours=6)


class PayloadValidationError(ValueError):
    pass


def _require_mapping(payload, key):
    value = payload.get(key)
    if not isinstance(value, dict):
        raise PayloadValidationError(f"Champ objet requis: {key}")
    return value


def _require_number(mapping, key, minimum=None, maximum=None):
    if key not in mapping:
        raise PayloadValidationError(f"Champ numerique requis: {key}")
    try:
        value = float(mapping[key])
    except (TypeError, ValueError):
        raise PayloadValidationError(f"Champ numerique invalide: {key}") from None
    if not math.isfinite(value):
        raise PayloadValidationError(f"Champ numerique non fini: {key}")
    if minimum is not None and value < minimum:
        raise PayloadValidationError(f"Champ trop bas: {key}")
    if maximum is not None and value > maximum:
        raise PayloadValidationError(f"Champ trop haut: {key}")
    return value


def _require_bool(mapping, key):
    if key not in mapping or not isinstance(mapping[key], bool):
        raise PayloadValidationError(f"Champ booleen requis: {key}")
    return mapping[key]


def _optional_number(mapping, key, default=0.0, minimum=None, maximum=None):
    if key not in mapping or mapping[key] is None:
        return float(default)
    return _require_number(mapping, key, minimum, maximum)


def _optional_bool(mapping, key, default=True):
    if key not in mapping:
        return bool(default)
    return _require_bool(mapping, key)


def parse_iso_timestamp(value):
    if not value:
        raise PayloadValidationError("timestamp requis")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise PayloadValidationError("timestamp ISO-8601 invalide") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if parsed < now - MAX_CLOCK_SKEW or parsed > now + MAX_CLOCK_SKEW:
        raise PayloadValidationError("timestamp hors fenetre autorisee")
    return parsed


def validate_telemetry_payload(payload):
    if not isinstance(payload, dict):
        raise PayloadValidationError("Payload JSON requis")
    try:
        UUID(str(payload.get("messageId")))
    except (TypeError, ValueError):
        raise PayloadValidationError("messageId UUID invalide") from None
    if payload.get("type") != "telemetry":
        raise PayloadValidationError("type telemetry requis")
    device_uid = str(payload.get("deviceUid") or "").strip()
    if not device_uid:
        raise PayloadValidationError("deviceUid requis")
    try:
        black_box_id = int(payload.get("blackBoxId") or payload.get("black_box_id"))
    except (TypeError, ValueError):
        raise PayloadValidationError("blackBoxId entier requis") from None
    if black_box_id <= 0:
        raise PayloadValidationError("blackBoxId doit etre positif")
    container_id = str(payload.get("containerId") or payload.get("container_id") or "").strip().upper() or None
    timestamp = parse_iso_timestamp(payload.get("timestamp"))
    try:
        sequence = int(payload.get("sequence"))
    except (TypeError, ValueError):
        raise PayloadValidationError("sequence entier requis") from None
    if sequence < 0:
        raise PayloadValidationError("sequence negatif interdit")

    position = _require_mapping(payload, "position")
    sensors = _require_mapping(payload, "sensors")
    modes = _require_mapping(payload, "modes")
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    alert = payload.get("alert") if isinstance(payload.get("alert"), dict) else {}

    normalized = {
        "message_id": str(payload["messageId"]),
        "device_uid": device_uid,
        "black_box_id": black_box_id,
        "container_id": container_id,
        "timestamp": timestamp,
        "sequence": sequence,
        "position": {
            "latitude": _require_number(position, "latitude", -90, 90),
            "longitude": _require_number(position, "longitude", -180, 180),
            "accuracy": _require_number(position, "accuracy", 0, 100000),
            "speed": _require_number(position, "speed", 0, 1000),
            "heading": _require_number(position, "heading", 0, 360),
            "source": str(position.get("source") or payload.get("source") or "ESP32")[:40],
        },
        "sensors": {
            "temperature": _require_number(sensors, "temperature", -80, 120),
            "humidity": _require_number(sensors, "humidity", 0, 100),
            "shock": _require_number(sensors, "shock", 0, 200),
            "pressure": _require_number(sensors, "pressure", 300, 1200),
            "flameDetected": _require_bool(sensors, "flameDetected"),
            "doorOpen": _require_bool(sensors, "doorOpen"),
            "batteryLevel": _require_number(sensors, "batteryLevel", 0, 100),
            "lightLevel": _optional_number(sensors, "lightLevel", 0, 0, 4095),
            "soundLevel": _optional_number(sensors, "soundLevel", 0, 0, 4095),
            "distanceCm": _optional_number(sensors, "distanceCm", 0, 0, 1000),
            "accelerationX": _optional_number(sensors, "accelerationX", 0, -200, 200),
            "accelerationY": _optional_number(sensors, "accelerationY", 0, -200, 200),
            "accelerationZ": _optional_number(sensors, "accelerationZ", 0, -200, 200),
            "securityAlarm": (
                _require_bool(sensors, "securityAlarm")
                if "securityAlarm" in sensors
                else False
            ),
        },
        "modes": {
            "securityEnabled": _require_bool(modes, "securityEnabled"),
            "audioRecordingEnabled": _require_bool(modes, "audioRecordingEnabled"),
            "audioListeningEnabled": _require_bool(modes, "audioListeningEnabled"),
            "flameDetectionEnabled": _require_bool(modes, "flameDetectionEnabled"),
        },
        "quality": {
            "dhtValid": _optional_bool(quality, "dhtValid"),
            "mpuValid": _optional_bool(quality, "mpuValid"),
            "gpsValid": _optional_bool(quality, "gpsValid"),
            "distanceValid": _optional_bool(quality, "distanceValid"),
            "sdReady": _optional_bool(quality, "sdReady"),
            "pressureMeasured": _optional_bool(quality, "pressureMeasured"),
            "batteryMeasured": _optional_bool(quality, "batteryMeasured"),
            "timestampSource": str(quality.get("timestampSource") or "DEVICE")[:40],
        },
        "alert": {
            "raised": bool(alert.get("raised", False)),
            "label": str(alert.get("label") or "")[:80],
            "occurredAt": str(alert.get("occurredAt") or "")[:40],
            "distanceCm": _optional_number(alert, "distanceCm", 0, 0, 1000),
            "thresholdCm": _optional_number(alert, "thresholdCm", 15, 0, 1000),
            "automaticListening": bool(alert.get("automaticListening", False)),
        },
    }
    return normalized


def validate_ack_payload(payload):
    if not isinstance(payload, dict):
        raise PayloadValidationError("Payload JSON requis")
    if not payload.get("commandUid"):
        raise PayloadValidationError("commandUid requis")
    if not payload.get("deviceUid"):
        raise PayloadValidationError("deviceUid requis")
    if not payload.get("status"):
        raise PayloadValidationError("status requis")
    parse_iso_timestamp(payload.get("timestamp"))
    return payload
