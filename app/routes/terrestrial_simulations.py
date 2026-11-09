"""Authenticated API for isolated terrestrial demo sessions."""

import json
import os
import requests
from datetime import datetime, timezone
from uuid import UUID, uuid4

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from app.extensions import db
from app.utils import get_caller_identity
from app.services.terrestrial_simulation_service import SCENARIOS, fetch_osrm_route, load_scenario_configuration


simulation_bp = Blueprint("terrestrial_simulations", __name__)
MANAGER_ROLES = {"superadmin", "owner"}
READ_ROLES = {"superadmin", "owner", "company", "client", "driver", "port_authority"}
ACTIVE_STATUSES = ("RUNNING", "PAUSED")


def _json_value(value, fallback=None):
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return fallback
    return value


def _session_access(session_uid, role, user_id):
    row = db.session.execute(text("""
        SELECT s.session_uid,s.status,s.requested_by_role,s.requested_by_id
        FROM brady.argos_transport_sim_sessions s
        WHERE s.session_uid=CAST(:uid AS uuid)
    """), {"uid": session_uid}).fetchone()
    if not row:
        return None
    if role == "superadmin":
        return row
    from app.routes.dashboard import _visible_boites_for
    allowed = {str(value) for value in (_visible_boites_for(role, user_id) or [])}
    boxes = db.session.execute(text("""
        SELECT black_box_id FROM brady.argos_transport_sim_scenarios
        WHERE session_uid=CAST(:uid AS uuid)
    """), {"uid": session_uid}).fetchall()
    if not boxes or any(str(item.black_box_id) not in allowed for item in boxes):
        return None
    return row


def _serialize_session(session_uid, role, user_id):
    row = db.session.execute(text("""
        SELECT session_uid,mode,status,requested_by_role,requested_by_id,
               interval_seconds,duration_seconds,time_scale,active_elapsed_seconds,
               started_at,stopped_at,last_active_at,worker_heartbeat_at,last_tick_at,last_error,created_at
        FROM brady.argos_transport_sim_sessions
        WHERE session_uid=CAST(:uid AS uuid)
    """), {"uid": session_uid}).fetchone()
    if not row:
        return None
    if not _session_access(session_uid, role, user_id):
        return None
    elapsed = float(row.active_elapsed_seconds or 0)
    if row.status == "RUNNING" and row.worker_heartbeat_at and row.last_active_at:
        # A stale worker heartbeat marks downtime; do not advance the scenario clock.
        heartbeat_age = (datetime.now(timezone.utc) - row.worker_heartbeat_at).total_seconds()
        if heartbeat_age <= max(15, int(row.interval_seconds) * 2):
            elapsed += max(0, min(heartbeat_age, (datetime.now(timezone.utc) - row.last_active_at).total_seconds()))

    scenarios = db.session.execute(text("""
        SELECT sc.scenario_code,sc.black_box_id,sc.container_id,sc.box_serial,
               sc.route_name,sc.origin,sc.destination,sc.route_geometry,
               sc.origin_geocode,sc.destination_geocode,
               sc.route_distance_m,sc.route_duration_s,sc.route_source,
               sc.route_retrieved_at,sc.route_version,sc.route_steps,
               sc.route_limitations,sc.scenario_config,
               latest.batch_uid,latest.sequence,latest.measured_at,latest.simulated_at,
               latest.simulated_elapsed_seconds,latest.latitude,latest.longitude,
               latest.speed_kmh,latest.heading,latest.remaining_distance_m,
               latest.stopped_seconds,latest.vehicle_state,latest.eta_reference_at,
               latest.eta_current_at,latest.eta_delay_seconds,latest.sensor_values,
               latest.active_events,latest.rule_assessments,latest.provenance,latest.telemetry_payload
        FROM brady.argos_transport_sim_scenarios sc
        LEFT JOIN LATERAL (
            SELECT * FROM brady.argos_transport_sim_samples sm
            WHERE sm.session_uid=sc.session_uid AND sm.scenario_code=sc.scenario_code
            ORDER BY sm.sequence DESC LIMIT 1
        ) latest ON TRUE
        WHERE sc.session_uid=CAST(:uid AS uuid)
        ORDER BY sc.scenario_code
    """), {"uid": session_uid}).fetchall()
    episodes = db.session.execute(text("""
        SELECT episode_uid,scenario_code,event_type,severity,status,
               first_sequence,last_sequence,first_simulated_at,last_simulated_at,
               closed_at,evidence,recommendation,provenance
        FROM brady.argos_transport_sim_episodes
        WHERE session_uid=CAST(:uid AS uuid)
        ORDER BY first_simulated_at DESC
    """), {"uid": session_uid}).fetchall()
    result_scenarios = []
    for item in scenarios:
        names = item._mapping.keys()
        names = list(names)
        result = {name: getattr(item, name) for name in names}
        for key in ("route_geometry", "origin_geocode", "destination_geocode", "route_steps", "route_limitations", "scenario_config",
                    "sensor_values", "active_events", "rule_assessments", "provenance", "telemetry_payload"):
            result[key] = _json_value(result.get(key), {} if key in {
                "route_geometry", "origin_geocode", "destination_geocode", "scenario_config", "sensor_values", "rule_assessments", "provenance", "telemetry_payload"
            } else [])
        result_scenarios.append(result)
    result_episodes = []
    for episode in episodes:
        item = dict(episode._mapping)
        item["evidence"] = _json_value(item.get("evidence"), [])
        item["provenance"] = _json_value(item.get("provenance"), {"dataOrigin": "SYNTHETIC"})
        result_episodes.append(item)
    heartbeat_age = None
    if row.worker_heartbeat_at:
        heartbeat_age = max(0, int((datetime.now(timezone.utc) - row.worker_heartbeat_at).total_seconds()))
    worker_state = "online" if heartbeat_age is not None and heartbeat_age <= 15 else "offline_or_not_started"
    return {
        "session_uid": str(row.session_uid), "mode": row.mode, "status": row.status,
        "interval_seconds": row.interval_seconds, "duration_seconds": row.duration_seconds,
        "time_scale": row.time_scale, "active_elapsed_seconds": round(elapsed, 1),
        "remaining_seconds": max(0, round(row.duration_seconds - elapsed, 1)),
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "stopped_at": row.stopped_at.isoformat() if row.stopped_at else None,
        "last_tick_at": row.last_tick_at.isoformat() if row.last_tick_at else None,
        "last_error": row.last_error,
        "worker": {"status": worker_state, "heartbeat_age_seconds": heartbeat_age},
        "scenarios": result_scenarios, "episodes": result_episodes,
    }


@simulation_bp.route("/api/terrestrial-simulations", methods=["GET", "POST"])
def terrestrial_simulations():
    role, user_id = get_caller_identity()
    if request.method == "GET":
        if role not in READ_ROLES:
            return jsonify({"error": "Authentification requise"}), 401
        rows = db.session.execute(text("""
            SELECT session_uid FROM brady.argos_transport_sim_sessions
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC LIMIT 20
        """)).fetchall()
        sessions = []
        for row in rows:
            value = _serialize_session(str(row.session_uid), role, user_id)
            if value:
                sessions.append(value)
        return jsonify({"mode": "SIMULATION", "sessions": sessions}), 200

    if role not in MANAGER_ROLES:
        return jsonify({"error": "Création de démonstration réservée aux gestionnaires autorisés"}), 403
    data = request.get_json(silent=True) or {}
    if data.get("mode", "SIMULATION") != "SIMULATION":
        return jsonify({"error": "Cette API accepte uniquement des sessions SIMULATION"}), 400
    try:
        box_ids = data.get("black_box_ids")
        if not isinstance(box_ids, list) or len(box_ids) != 2:
            raise ValueError("Sélectionnez exactement deux boîtes noires enregistrées")
        if any(not str(value).isdigit() or int(value) <= 0 for value in box_ids):
            raise ValueError("Les identifiants de boîte doivent être des entiers positifs")
        box_ids = [int(value) for value in box_ids]
        if len(set(box_ids)) != 2:
            raise ValueError("Les deux scénarios doivent utiliser deux boîtes distinctes")
        interval = int(data.get("interval_seconds", 60))
        duration = int(data.get("duration_seconds", 3600))
        time_scale = int(data.get("time_scale", 5))
        if not 10 <= interval <= 600 or not 60 <= duration <= 3600 or not 1 <= time_scale <= 20:
            raise ValueError("Fréquence (10–600 s), durée (60–3600 s) ou accélération (1–20×) invalide")

        from app.routes.dashboard import _visible_boites_for
        visible = _visible_boites_for(role, user_id)
        if visible is not None and not set(map(str, box_ids)).issubset({str(value) for value in visible}):
            return jsonify({"error": "Une boîte sélectionnée est hors de votre périmètre"}), 403
        params = {f"box{index}": value for index, value in enumerate(box_ids)}
        placeholders = ",".join(f":box{index}" for index in range(len(box_ids)))
        boxes = db.session.execute(text(f"""
            SELECT id_boite,numero_serie,id_conteneurs,status,archived
            FROM boite_noir WHERE id_boite IN ({placeholders})
              AND COALESCE(archived,FALSE)=FALSE
              AND LOWER(COALESCE(status,'')) NOT IN ('deleted','revoked','off')
            FOR UPDATE
        """), params).fetchall()
        if len(boxes) != 2:
            raise ValueError("Une boîte n'existe pas, est archivée ou n'est pas disponible")
        busy = db.session.execute(text(f"""
            SELECT DISTINCT sc.black_box_id
            FROM brady.argos_transport_sim_scenarios sc
            JOIN brady.argos_transport_sim_sessions se USING(session_uid)
            WHERE sc.black_box_id IN ({placeholders}) AND se.status IN ('RUNNING','PAUSED')
        """), params).fetchall()
        if busy:
            raise ValueError("Une boîte sélectionnée participe déjà à une session de simulation active")

        # Resolve both actual road routes before creating any session record.
        route_by_code = {
            "douala_ndjamena": fetch_osrm_route("douala_ndjamena"),
            "kribi_bertoua": fetch_osrm_route("kribi_bertoua"),
        }
        runtime_configs = load_scenario_configuration()
        session_uid = str(uuid4())
        now = datetime.now(timezone.utc)
        db.session.execute(text("""
            INSERT INTO brady.argos_transport_sim_sessions
                (session_uid,mode,status,requested_by_role,requested_by_id,
                 interval_seconds,duration_seconds,time_scale,active_elapsed_seconds,
                 last_active_at,started_at,created_at,updated_at)
            VALUES (CAST(:uid AS uuid),'SIMULATION','RUNNING',:role,:actor,
                    :interval,:duration,:scale,0,:now,:now,:now,:now)
        """), {"uid": session_uid, "role": role, "actor": str(user_id or ""),
                "interval": interval, "duration": duration, "scale": time_scale, "now": now})
        box_by_id = {int(box.id_boite): box for box in boxes}
        for scenario_code, box_id in zip(SCENARIOS, box_ids):
            route = route_by_code[scenario_code]
            scenario = SCENARIOS[scenario_code]
            box = box_by_id[box_id]
            config = {**runtime_configs[scenario_code],
                      "truck_restrictions_checked": False,
                      "traffic_data_available": False,
                      "configuration_source": os.getenv("ARGOS_TERRESTRIAL_SIMULATION_CONFIG") or "config/terrestrial_transport_scenarios.json"}
            db.session.execute(text("""
                INSERT INTO brady.argos_transport_sim_scenarios
                    (session_uid,scenario_code,black_box_id,container_id,box_serial,
                     route_name,origin,destination,route_geometry,origin_geocode,destination_geocode,route_distance_m,
                     route_duration_s,route_source,route_retrieved_at,route_version,
                     route_steps,route_limitations,scenario_config)
                VALUES (CAST(:uid AS uuid),:code,:box,:container,:serial,:name,:origin,:destination,
                    CAST(:geometry AS jsonb),CAST(:origin_geocode AS jsonb),CAST(:destination_geocode AS jsonb),
                    :distance,:duration,:source,CAST(:retrieved AS timestamptz),
                    :version,CAST(:steps AS jsonb),CAST(:limitations AS jsonb),CAST(:config AS jsonb))
            """), {
                "uid": session_uid, "code": scenario_code, "box": box_id,
                "container": box.id_conteneurs, "serial": box.numero_serie,
                "name": scenario["route_name"], "origin": scenario["origin"],
                "destination": scenario["destination"], "geometry": json.dumps(route["geometry"]),
                "origin_geocode": json.dumps(route["origin"]),
                "destination_geocode": json.dumps(route["destination"]),
                "distance": route["distance_m"], "duration": route["duration_s"],
                "source": route["source_name"], "retrieved": route["retrieved_at"],
                "version": route["route_version"], "steps": json.dumps(route["steps"]),
                "limitations": json.dumps(route["limitations"]), "config": json.dumps(config),
            })
        db.session.commit()
        value = _serialize_session(session_uid, role, user_id)
        return jsonify(value), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except requests.RequestException as exc:
        db.session.rollback()
        return jsonify({"error": f"Calcul d'itinéraire indisponible; aucune route de remplacement n'a été inventée ({type(exc).__name__})"}), 503
    except RuntimeError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Création de la session de simulation impossible"}), 500


@simulation_bp.route("/api/terrestrial-simulations/<session_uid>/control", methods=["POST"])
def control_terrestrial_simulation(session_uid):
    role, user_id = get_caller_identity()
    if role not in MANAGER_ROLES:
        return jsonify({"error": "Commande réservée aux gestionnaires autorisés"}), 403
    try:
        session_uid = str(UUID(session_uid))
    except (ValueError, TypeError):
        return jsonify({"error": "Identifiant de session invalide"}), 400
    row = _session_access(session_uid, role, user_id)
    if not row:
        return jsonify({"error": "Session hors périmètre ou inexistante"}), 404
    action = str((request.get_json(silent=True) or {}).get("action") or "").lower()
    now = datetime.now(timezone.utc)
    if action == "pause" and row.status == "RUNNING":
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_sessions
            SET active_elapsed_seconds=active_elapsed_seconds + CASE
                  WHEN worker_heartbeat_at IS NOT NULL AND last_active_at IS NOT NULL
                  THEN GREATEST(0,EXTRACT(EPOCH FROM (worker_heartbeat_at-last_active_at)))
                  ELSE 0 END,
                status='PAUSED',last_active_at=NULL,updated_at=:now
            WHERE session_uid=CAST(:uid AS uuid)
        """), {"uid": session_uid, "now": now})
    elif action == "resume" and row.status == "PAUSED":
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_sessions
            SET status='RUNNING',last_active_at=:now,worker_heartbeat_at=:now,
                updated_at=:now,last_error=NULL
            WHERE session_uid=CAST(:uid AS uuid)
        """), {"uid": session_uid, "now": now})
    elif action == "stop" and row.status in ACTIVE_STATUSES:
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_sessions
            SET active_elapsed_seconds=active_elapsed_seconds + CASE
                  WHEN status='RUNNING' AND worker_heartbeat_at IS NOT NULL AND last_active_at IS NOT NULL
                  THEN GREATEST(0,EXTRACT(EPOCH FROM (worker_heartbeat_at-last_active_at)))
                  ELSE 0 END,
                status='STOPPED',last_active_at=NULL,stopped_at=:now,updated_at=:now
            WHERE session_uid=CAST(:uid AS uuid)
        """), {"uid": session_uid, "now": now})
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_episodes
            SET status='resolved',closed_at=COALESCE(closed_at,:now),updated_at=:now
            WHERE session_uid=CAST(:uid AS uuid) AND status IN ('new','ongoing','aggravated')
        """), {"uid": session_uid, "now": now})
    elif action not in {"pause", "resume", "stop"}:
        return jsonify({"error": "action doit être pause, resume ou stop"}), 400
    elif (action, row.status) not in {("pause", "RUNNING"), ("resume", "PAUSED"),
                                      ("stop", "RUNNING"), ("stop", "PAUSED")}:
        return jsonify({"error": f"Action {action} incompatible avec l'état {row.status}"}), 409
    db.session.commit()
    return jsonify(_serialize_session(session_uid, role, user_id)), 200
