"""Acces SQL du module IoT."""

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text

from app.extensions import db
from app.modules.iot.normalizer import normalize_telemetry_quality
from app.modules.iot.types import DEVICE_ACTIVE, DEVICE_PENDING, DEVICE_REVOKED


def ensure_iot_schema(commit=True):
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS iot_devices (
            id SERIAL PRIMARY KEY,
            device_uid VARCHAR(80) NOT NULL UNIQUE,
            hardware_serial VARCHAR(120) UNIQUE,
            mac_address VARCHAR(80),
            firmware_version VARCHAR(80),
            protocol_version VARCHAR(40),
            credential_hash TEXT,
            enrollment_token_hash TEXT,
            enrollment_expires_at TIMESTAMPTZ,
            status VARCHAR(40) NOT NULL DEFAULT 'PENDING_ENROLLMENT',
            last_seen_at TIMESTAMPTZ,
            last_ip VARCHAR(80),
            registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            activated_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS black_box_devices (
            id SERIAL PRIMARY KEY,
            black_box_id INTEGER NOT NULL,
            device_id INTEGER NOT NULL REFERENCES iot_devices(id),
            assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            assigned_by VARCHAR(80),
            detached_at TIMESTAMPTZ,
            detached_by VARCHAR(80),
            reason TEXT,
            status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE'
        )
    """))
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_black_box_devices_active_device
        ON black_box_devices(device_id) WHERE status = 'ACTIVE'
    """))
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_black_box_devices_active_box
        ON black_box_devices(black_box_id) WHERE status = 'ACTIVE'
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS iot_raw_messages (
            id BIGSERIAL PRIMARY KEY,
            message_id UUID,
            device_uid VARCHAR(80),
            direction VARCHAR(20) NOT NULL DEFAULT 'INBOUND',
            message_type VARCHAR(60) NOT NULL,
            payload JSONB NOT NULL,
            validation_status VARCHAR(30) NOT NULL DEFAULT 'RECEIVED',
            error_message TEXT,
            remote_addr VARCHAR(80),
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_iot_raw_messages_message_id
        ON iot_raw_messages(message_id) WHERE message_id IS NOT NULL
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id BIGSERIAL PRIMARY KEY,
            raw_message_id BIGINT REFERENCES iot_raw_messages(id),
            device_id INTEGER REFERENCES iot_devices(id),
            black_box_id INTEGER,
            container_id VARCHAR(80),
            sequence BIGINT,
            temperature DOUBLE PRECISION,
            humidity DOUBLE PRECISION,
            shock DOUBLE PRECISION,
            pressure DOUBLE PRECISION,
            flame_detected BOOLEAN,
            door_open BOOLEAN,
            battery_level DOUBLE PRECISION,
            light_level DOUBLE PRECISION,
            sound_level DOUBLE PRECISION,
            distance_cm DOUBLE PRECISION,
            acceleration_x DOUBLE PRECISION,
            acceleration_y DOUBLE PRECISION,
            acceleration_z DOUBLE PRECISION,
            security_alarm BOOLEAN NOT NULL DEFAULT FALSE,
            modes JSONB NOT NULL DEFAULT '{}'::jsonb,
            quality JSONB NOT NULL DEFAULT '{}'::jsonb,
            measured_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    for column_sql in (
        "ADD COLUMN IF NOT EXISTS light_level DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS sound_level DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS distance_cm DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS acceleration_x DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS acceleration_y DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS acceleration_z DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS security_alarm BOOLEAN NOT NULL DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS quality JSONB NOT NULL DEFAULT '{}'::jsonb",
    ):
        db.session.execute(text(f"ALTER TABLE sensor_readings {column_sql}"))
    for column_sql in (
        "ADD COLUMN IF NOT EXISTS device_uid VARCHAR(80)",
        "ADD COLUMN IF NOT EXISTS sequence BIGINT",
        "ADD COLUMN IF NOT EXISTS acceleration_x DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS acceleration_y DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS acceleration_z DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS battery_level DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS heading DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS quality JSONB NOT NULL DEFAULT '{}'::jsonb",
    ):
        db.session.execute(text(f"ALTER TABLE evenement_save {column_sql}"))
    for column_sql in (
        "ADD COLUMN IF NOT EXISTS device_uid VARCHAR(80)",
        "ADD COLUMN IF NOT EXISTS sequence BIGINT",
    ):
        db.session.execute(text(f"ALTER TABLE notifications {column_sql}"))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS positions (
            id BIGSERIAL PRIMARY KEY,
            raw_message_id BIGINT REFERENCES iot_raw_messages(id),
            device_id INTEGER REFERENCES iot_devices(id),
            black_box_id INTEGER,
            container_id VARCHAR(80),
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            accuracy DOUBLE PRECISION,
            speed DOUBLE PRECISION,
            heading DOUBLE PRECISION,
            source VARCHAR(40) NOT NULL DEFAULT 'ESP32',
            measured_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS device_commands (
            id BIGSERIAL PRIMARY KEY,
            command_uid UUID NOT NULL UNIQUE,
            device_id INTEGER NOT NULL REFERENCES iot_devices(id),
            black_box_id INTEGER,
            container_id VARCHAR(80),
            requested_by_user_id VARCHAR(80),
            command_type VARCHAR(80) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
            priority INTEGER NOT NULL DEFAULT 5,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            published_at TIMESTAMPTZ,
            acknowledged_at TIMESTAMPTZ,
            executed_at TIMESTAMPTZ,
            failed_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ NOT NULL,
            error_code VARCHAR(80),
            error_message TEXT,
            correlation_id UUID,
            retry_count INTEGER NOT NULL DEFAULT 0
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS device_command_acknowledgements (
            id BIGSERIAL PRIMARY KEY,
            command_uid UUID NOT NULL,
            device_uid VARCHAR(80) NOT NULL,
            status VARCHAR(40) NOT NULL,
            result JSONB,
            error_code VARCHAR(80),
            error_message TEXT,
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS audio_recordings (
            id BIGSERIAL PRIMARY KEY,
            recording_uid UUID NOT NULL UNIQUE,
            device_id INTEGER REFERENCES iot_devices(id),
            black_box_id INTEGER,
            container_id VARCHAR(80),
            event_uid UUID,
            duration_seconds DOUBLE PRECISION,
            started_at TIMESTAMPTZ,
            storage_key TEXT NOT NULL,
            mime_type VARCHAR(120) NOT NULL,
            size_bytes BIGINT NOT NULL,
            checksum_sha256 VARCHAR(128),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_audio_recordings_box_started
        ON audio_recordings(black_box_id, started_at DESC)
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            actor_role VARCHAR(40),
            actor_id VARCHAR(80),
            action VARCHAR(120) NOT NULL,
            entity_type VARCHAR(80),
            entity_id VARCHAR(120),
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS background_jobs (
            id BIGSERIAL PRIMARY KEY,
            job_uid UUID NOT NULL UNIQUE,
            job_type VARCHAR(100) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
            run_at TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS black_box_container_assignments (
            id BIGSERIAL PRIMARY KEY,
            black_box_id INTEGER NOT NULL,
            container_id VARCHAR(80) NOT NULL,
            assigned_by VARCHAR(80),
            assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            detached_by VARCHAR(80),
            detached_at TIMESTAMPTZ,
            reason TEXT,
            status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE'
        )
    """))
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_bb_container_assignments_active_box
        ON black_box_container_assignments(black_box_id) WHERE status = 'ACTIVE'
    """))
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_bb_container_assignments_active_container
        ON black_box_container_assignments(container_id) WHERE status = 'ACTIVE'
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS generated_reports (
            id BIGSERIAL PRIMARY KEY,
            report_uid UUID NOT NULL UNIQUE,
            category VARCHAR(80) NOT NULL,
            title TEXT NOT NULL,
            company_id VARCHAR(80),
            container_id VARCHAR(80),
            black_box_id INTEGER,
            storage_key TEXT NOT NULL,
            mime_type VARCHAR(120) NOT NULL DEFAULT 'application/pdf',
            size BIGINT,
            checksum TEXT,
            visibility_scope VARCHAR(40) NOT NULL DEFAULT 'RELATED',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archived_at TIMESTAMPTZ
        )
    """))
    if commit:
        db.session.commit()


def insert_raw_message(payload, message_type, remote_addr=None, status="RECEIVED", error=None):
    message_id = payload.get("messageId") or payload.get("message_id")
    try:
        message_id = str(UUID(str(message_id))) if message_id else None
    except (TypeError, ValueError):
        message_id = None
    device_uid = payload.get("deviceUid") or payload.get("device_uid")
    return db.session.execute(text("""
        INSERT INTO iot_raw_messages
            (message_id, device_uid, message_type, payload, validation_status, error_message, remote_addr)
        VALUES
            (CAST(:message_id AS uuid), :device_uid, :message_type, CAST(:payload AS jsonb), :status, :error, :remote_addr)
        RETURNING id
    """), {
        "message_id": message_id,
        "device_uid": device_uid,
        "message_type": message_type,
        "payload": json.dumps(payload, default=str),
        "status": status,
        "error": error,
        "remote_addr": remote_addr,
    }).scalar()


def find_device(device_uid):
    return db.session.execute(text("SELECT * FROM iot_devices WHERE device_uid = :uid LIMIT 1"), {"uid": device_uid}).fetchone()


def create_pending_device(device_uid, token_hash, hardware_serial=None, firmware_version=None, protocol_version=None, expires_at=None):
    return db.session.execute(text("""
        INSERT INTO iot_devices
            (device_uid, hardware_serial, firmware_version, protocol_version, enrollment_token_hash, enrollment_expires_at, status)
        VALUES
            (:uid, :serial, :firmware, :protocol, :token_hash, :expires_at, :status)
        RETURNING *
    """), {
        "uid": device_uid,
        "serial": hardware_serial,
        "firmware": firmware_version,
        "protocol": protocol_version,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "status": DEVICE_PENDING,
    }).fetchone()


def activate_device(device_id, credential_hash, remote_addr=None):
    return db.session.execute(text("""
        UPDATE iot_devices
        SET credential_hash = :credential_hash,
            enrollment_token_hash = NULL,
            enrollment_expires_at = NULL,
            status = :status,
            activated_at = NOW(),
            last_seen_at = NOW(),
            last_ip = :remote_addr,
            updated_at = NOW()
        WHERE id = :id
        RETURNING *
    """), {"id": device_id, "credential_hash": credential_hash, "status": DEVICE_ACTIVE, "remote_addr": remote_addr}).fetchone()


def touch_device(device_id, sequence=None, remote_addr=None):
    metadata = {}
    if sequence is not None:
        metadata["last_sequence"] = sequence
    db.session.execute(text("""
        UPDATE iot_devices
        SET last_seen_at = NOW(),
            last_ip = COALESCE(:remote_addr, last_ip),
            metadata = metadata || CAST(:metadata AS jsonb),
            updated_at = NOW()
        WHERE id = :id
    """), {"id": device_id, "remote_addr": remote_addr, "metadata": json.dumps(metadata)})


def get_active_black_box_for_device(device_id):
    return db.session.execute(text("""
        SELECT bbd.black_box_id, b.id_conteneurs AS container_id
        FROM black_box_devices bbd
        LEFT JOIN boite_noir b ON b.id_boite = bbd.black_box_id
        WHERE bbd.device_id = :device_id AND bbd.status = 'ACTIVE'
        LIMIT 1
    """), {"device_id": device_id}).fetchone()


def get_alert_thresholds(black_box_id):
    return db.session.execute(text("""
        SELECT temp_min, temp_max, humi_min, humi_max, choc_max,
               pression_min, pression_max, vitesse_max, angle_max
        FROM seuils_alerte WHERE id_boite=:box
    """), {"box": black_box_id}).fetchone()


def apply_fallback_position(validated, relation):
    """Remplace uniquement un GPS 0,0 par une position navigateur recente."""
    position = validated["position"]
    if position["latitude"] != 0 or position["longitude"] != 0:
        return validated
    fallback = db.session.execute(text("""
        SELECT latitude,longitude,accuracy
        FROM positions
        WHERE black_box_id=:box AND source='BROWSER_FALLBACK'
          AND measured_at >= NOW() - INTERVAL '24 hours'
        ORDER BY measured_at DESC LIMIT 1
    """), {"box": relation.black_box_id}).fetchone()
    if fallback:
        position["latitude"] = float(fallback.latitude)
        position["longitude"] = float(fallback.longitude)
        position["accuracy"] = float(fallback.accuracy or position["accuracy"])
        position["source"] = "BROWSER_FALLBACK"
    return validated


def insert_sensor_and_position(raw_id, device, relation, event_payload, validated):
    validated = normalize_telemetry_quality(validated)
    black_box_id = relation.black_box_id if relation else None
    container_id = relation.container_id if relation else None
    sensors = validated["sensors"]
    position = validated["position"]
    measured_at = validated["timestamp"]
    db.session.execute(text("""
        INSERT INTO sensor_readings
            (raw_message_id, device_id, black_box_id, container_id, sequence,
             temperature, humidity, shock, pressure, flame_detected, door_open, battery_level,
             light_level, sound_level, distance_cm, acceleration_x, acceleration_y,
             acceleration_z, security_alarm, modes, quality, measured_at)
        VALUES
            (:raw_id, :device_id, :black_box_id, :container_id, :sequence,
             :temperature, :humidity, :shock, :pressure, :flame, :door, :battery,
             :light, :sound, :distance, :accel_x, :accel_y, :accel_z,
             :security_alarm, CAST(:modes AS jsonb), CAST(:quality AS jsonb), :measured_at)
    """), {
        "raw_id": raw_id,
        "device_id": device.id,
        "black_box_id": black_box_id,
        "container_id": container_id,
        "sequence": validated["sequence"],
        "temperature": sensors["temperature"],
        "humidity": sensors["humidity"],
        "shock": sensors["shock"],
        "pressure": sensors["pressure"],
        "flame": sensors["flameDetected"],
        "door": sensors["doorOpen"],
        "battery": sensors["batteryLevel"],
        "light": sensors["lightLevel"],
        "sound": sensors["soundLevel"],
        "distance": sensors["distanceCm"],
        "accel_x": sensors["accelerationX"],
        "accel_y": sensors["accelerationY"],
        "accel_z": sensors["accelerationZ"],
        "security_alarm": sensors["securityAlarm"],
        "modes": json.dumps(validated["modes"]),
        "quality": json.dumps(validated.get("quality") or {}),
        "measured_at": measured_at,
    })
    if not (position["latitude"] == 0 and position["longitude"] == 0):
        db.session.execute(text("""
            INSERT INTO positions
                (raw_message_id, device_id, black_box_id, container_id, latitude, longitude, accuracy, speed, heading, source, measured_at)
            VALUES
                (:raw_id, :device_id, :black_box_id, :container_id, :lat, :lon, :accuracy, :speed, :heading, :source, :measured_at)
        """), {
            "raw_id": raw_id,
            "device_id": device.id,
            "black_box_id": black_box_id,
            "container_id": container_id,
            "lat": position["latitude"],
            "lon": position["longitude"],
            "accuracy": position["accuracy"],
            "speed": position["speed"],
            "heading": position["heading"],
            "source": position.get("source", "ESP32"),
            "measured_at": measured_at,
        })
    if black_box_id:
        notif = json.dumps(event_payload["notif"]) if event_payload.get("notif") else None
        log_action = "Alerte IoT" if event_payload.get("notif") else "Telemetry ESP32"
        db.session.execute(text("""
            INSERT INTO evenement_save
                (id_boite, device_uid, sequence, temperature, humidite, pressions,
                 lat, lon, log_action, vitesse, chocs, notif, horodatage,
                 acceleration_x, acceleration_y, acceleration_z, battery_level, heading,
                 quality)
            VALUES
                (:b, :uid, :seq, :t, :h, :p, :lat, :lon, :la, :v, :c, :n, :ts,
                 :ax, :ay, :az, :battery, :heading, CAST(:quality AS jsonb))
        """), {
            "b": black_box_id,
            "uid": validated["device_uid"],
            "seq": validated["sequence"],
            "t": sensors["temperature"],
            "h": sensors["humidity"],
            "p": sensors["pressure"],
            "lat": event_payload["lat"],
            "lon": event_payload["lon"],
            "la": log_action,
            "v": event_payload["vitesse"],
            "c": sensors["shock"],
            "n": notif,
            "ts": event_payload["horodatage"],
            "ax": sensors["accelerationX"],
            "ay": sensors["accelerationY"],
            "az": sensors["accelerationZ"],
            "battery": sensors["batteryLevel"],
            "heading": position["heading"],
            "quality": json.dumps(validated.get("quality") or {}),
        })


def create_audit(action, entity_type=None, entity_id=None, details=None, actor_role=None, actor_id=None):
    db.session.execute(text("""
        INSERT INTO audit_logs (actor_role, actor_id, action, entity_type, entity_id, details)
        VALUES (:actor_role, :actor_id, :action, :entity_type, :entity_id, CAST(:details AS jsonb))
    """), {
        "actor_role": actor_role,
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "details": json.dumps(details or {}, default=str),
    })


def create_command(command_uid, device_id, black_box_id, container_id, user_id, command_type, payload, expires_at, correlation_id):
    return db.session.execute(text("""
        INSERT INTO device_commands
            (command_uid, device_id, black_box_id, container_id, requested_by_user_id,
             command_type, payload, expires_at, correlation_id)
        VALUES
            (CAST(:command_uid AS uuid), :device_id, :black_box_id, :container_id, :user_id,
             :command_type, CAST(:payload AS jsonb), :expires_at, CAST(:correlation_id AS uuid))
        RETURNING *
    """), {
        "command_uid": command_uid,
        "device_id": device_id,
        "black_box_id": black_box_id,
        "container_id": container_id,
        "user_id": user_id,
        "command_type": command_type,
        "payload": json.dumps(payload or {}),
        "expires_at": expires_at,
        "correlation_id": correlation_id,
    }).fetchone()


def mark_command_published(command_uid):
    return db.session.execute(text("""
        UPDATE device_commands
        SET status = 'PUBLISHED', published_at = NOW()
        WHERE command_uid = CAST(:uid AS uuid)
        RETURNING *
    """), {"uid": command_uid}).fetchone()


def update_command_from_ack(command_uid, device_uid, status, result=None, error_code=None, error_message=None):
    db.session.execute(text("""
        INSERT INTO device_command_acknowledgements
            (command_uid, device_uid, status, result, error_code, error_message)
        VALUES
            (CAST(:command_uid AS uuid), :device_uid, :status, CAST(:result AS jsonb), :error_code, :error_message)
    """), {
        "command_uid": command_uid,
        "device_uid": device_uid,
        "status": status,
        "result": json.dumps(result or {}),
        "error_code": error_code,
        "error_message": error_message,
    })
    field_sql = {
        "ACKNOWLEDGED": "acknowledged_at = COALESCE(acknowledged_at, NOW())",
        "EXECUTING": "acknowledged_at = COALESCE(acknowledged_at, NOW())",
        "SUCCEEDED": "executed_at = NOW()",
        "FAILED": "failed_at = NOW()",
        "REJECTED": "failed_at = NOW()",
    }.get(status, "acknowledged_at = COALESCE(acknowledged_at, NOW())")
    return db.session.execute(text(f"""
        UPDATE device_commands
        SET status = :status,
            error_code = :error_code,
            error_message = :error_message,
            {field_sql}
        WHERE command_uid = CAST(:command_uid AS uuid)
        RETURNING *
    """), {
        "command_uid": command_uid,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
    }).fetchone()


def find_command(command_uid):
    return db.session.execute(text("""
        SELECT dc.*, d.device_uid
        FROM device_commands dc
        JOIN iot_devices d ON d.id = dc.device_id
        WHERE dc.command_uid = CAST(:uid AS uuid)
        LIMIT 1
    """), {"uid": command_uid}).fetchone()


def find_black_box_device(black_box_id):
    return db.session.execute(text("""
        SELECT d.*, b.id_conteneurs AS container_id
        FROM black_box_devices bbd
        JOIN iot_devices d ON d.id = bbd.device_id
        LEFT JOIN boite_noir b ON b.id_boite = bbd.black_box_id
        WHERE bbd.black_box_id = :black_box_id
          AND bbd.status = 'ACTIVE'
          AND d.status = :active
        LIMIT 1
    """), {"black_box_id": black_box_id, "active": DEVICE_ACTIVE}).fetchone()


def find_registered_black_box_device(black_box_id):
    """Association matérielle valide, y compris en mode AP avant enrôlement."""
    return db.session.execute(text("""
        SELECT d.*, b.id_conteneurs AS container_id
        FROM black_box_devices bbd
        JOIN iot_devices d ON d.id = bbd.device_id
        LEFT JOIN boite_noir b ON b.id_boite = bbd.black_box_id
        WHERE bbd.black_box_id = :black_box_id
          AND bbd.status = 'ACTIVE'
          AND d.status <> :revoked
        LIMIT 1
    """), {"black_box_id": black_box_id, "revoked": DEVICE_REVOKED}).fetchone()


def ensure_fallback_device_for_black_box(black_box_id):
    device = find_black_box_device(black_box_id)
    if device:
        return device

    fallback_uid = f"ARGOS-FALLBACK-{black_box_id}"
    existing = db.session.execute(text("""
        SELECT id
        FROM iot_devices
        WHERE device_uid = :device_uid
        LIMIT 1
    """), {"device_uid": fallback_uid}).fetchone()

    if existing:
        device_id = existing.id
    else:
        created = db.session.execute(text("""
            INSERT INTO iot_devices (device_uid, status, metadata)
            VALUES (:device_uid, :status, CAST(:metadata AS jsonb))
            RETURNING id
        """), {
            "device_uid": fallback_uid,
            "status": DEVICE_ACTIVE,
            "metadata": json.dumps({"fallback": True, "created_for_black_box_id": black_box_id}),
        }).fetchone()
        device_id = created.id

    db.session.execute(text("""
        INSERT INTO black_box_devices (black_box_id, device_id, status, assigned_by, reason)
        VALUES (:black_box_id, :device_id, 'ACTIVE', 'system', 'fallback-device')
        ON CONFLICT DO NOTHING
    """), {"black_box_id": black_box_id, "device_id": device_id})

    return db.session.execute(text("""
        SELECT d.*, b.id_conteneurs AS container_id
        FROM iot_devices d
        JOIN black_box_devices bbd ON bbd.device_id = d.id
        LEFT JOIN boite_noir b ON b.id_boite = bbd.black_box_id
        WHERE bbd.black_box_id = :black_box_id
          AND bbd.status = 'ACTIVE'
          AND d.id = :device_id
        LIMIT 1
    """), {"black_box_id": black_box_id, "device_id": device_id}).fetchone()


def list_device_commands(device_id, limit=10):
    return db.session.execute(text("""
        SELECT dc.*
        FROM device_commands dc
        WHERE dc.device_id = :device_id
          AND dc.status IN ('PENDING', 'PUBLISHED', 'ACKNOWLEDGED', 'EXECUTING')
          AND dc.expires_at > NOW()
        ORDER BY dc.created_at ASC
        LIMIT :limit
    """), {"device_id": device_id, "limit": limit}).fetchall()


def is_device_usable(device):
    return device and device.status == DEVICE_ACTIVE and device.status != DEVICE_REVOKED


def now_utc():
    return datetime.now(timezone.utc)
