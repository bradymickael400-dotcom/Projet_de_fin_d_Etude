"""Isolated, explicitly synthetic road-transport simulations for ARGOS.

This module never writes to the live IoT measurement, position, route, or
notification tables. Operational rules are called only as pure evaluators.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone

import requests


SCENARIOS = {
    "douala_ndjamena": {
        "route_name": "Douala → N'Djamena",
        "origin": "Douala, Cameroon",
        "destination": "N'Djamena, Chad",
        "mode": "stable",
    },
    "kribi_bertoua": {
        "route_name": "Kribi → Bertoua",
        "origin": "Kribi, Cameroon",
        "destination": "Bertoua, Cameroon",
        "mode": "perturbations",
    },
}

ROUTE_LIMITATIONS = [
    "OSRM profile 'driving' does not certify truck access, height/weight restrictions, border passage, road condition, or legal vehicle suitability.",
    "The route duration is a map-based estimate without live traffic; it is not a traffic-aware ETA.",
    "Route geometry is a reference corridor, not a navigational instruction or proof of a traversed road.",
]


@lru_cache(maxsize=1)
def load_scenario_configuration() -> dict:
    """Load scenario windows from JSON; override the path through the environment."""
    configured_path = os.getenv("ARGOS_TERRESTRIAL_SIMULATION_CONFIG", "").strip()
    path = Path(configured_path) if configured_path else Path(__file__).resolve().parents[2] / "config" / "terrestrial_transport_scenarios.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Configuration de scénarios illisible : {path.name}") from exc
    if not isinstance(value, dict) or set(value) != set(SCENARIOS):
        raise RuntimeError("La configuration doit définir exactement les deux scénarios ARGOS")
    for code, config in value.items():
        if not isinstance(config, dict) or not isinstance(config.get("events"), dict):
            raise RuntimeError(f"Configuration d'événements invalide pour {code}")
        for name, window in config["events"].items():
            if (not isinstance(window, list) or len(window) != 2
                    or not all(isinstance(item, (int, float)) for item in window)
                    or window[0] < 0 or window[1] <= window[0]):
                raise RuntimeError(f"Fenêtre temporelle invalide : {code}.{name}")
    return value

_geocode_lock = threading.Lock()
_last_geocode_request = 0.0


def _utcnow():
    return datetime.now(timezone.utc)


def _env(name, default):
    value = os.getenv(name, "").strip()
    return value or default


def _http_get(url, *, params, headers, timeout, geocode=False):
    """Retry transient route-service failures; rate-limit each public geocode request."""
    global _last_geocode_request
    for attempt in range(3):
        if geocode:
            with _geocode_lock:
                wait = 1.05 - (time.monotonic() - _last_geocode_request)
                if wait > 0:
                    time.sleep(wait)
                _last_geocode_request = time.monotonic()
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(0.5 * (2 ** attempt))
            continue
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == 2:
                response.raise_for_status()
            time.sleep(0.5 * (2 ** attempt))
            continue
        response.raise_for_status()
        return response


def _geocode(query: str) -> dict:
    """Geocode one place with a policy-identifying client and bounded retry."""
    base = _env("ARGOS_NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")
    user_agent = os.getenv("ARGOS_SIMULATOR_USER_AGENT", "").strip()
    if not user_agent:
        raise RuntimeError("Configurez ARGOS_SIMULATOR_USER_AGENT avec le nom du client et un contact avant le géocodage.")
    response = _http_get(
        f"{base}/search", params={"q": query, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": user_agent}, timeout=(5, 20), geocode=True,
    )
    response.raise_for_status()
    results = response.json()
    if not isinstance(results, list) or not results:
        raise RuntimeError(f"Lieu introuvable par le géocodeur : {query}")
    result = results[0]
    try:
        lat, lon = float(result["lat"]), float(result["lon"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError(f"Réponse de géocodage invalide pour {query}") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise RuntimeError(f"Coordonnées de géocodage hors limites pour {query}")
    return {"latitude": lat, "longitude": lon, "label": result.get("display_name"),
            "osm_type": result.get("osm_type"), "osm_id": result.get("osm_id")}


def fetch_osrm_route(scenario_code: str) -> dict:
    """Return an actual OSRM road route; fail closed rather than drawing a fake one."""
    if scenario_code not in SCENARIOS:
        raise ValueError("Scénario terrestre non reconnu")
    scenario = SCENARIOS[scenario_code]
    origin = _geocode(scenario["origin"])
    destination = _geocode(scenario["destination"])
    base = _env("ARGOS_OSRM_URL", "https://router.project-osrm.org").rstrip("/")
    coords = (f"{origin['longitude']},{origin['latitude']};"
              f"{destination['longitude']},{destination['latitude']}")
    response = _http_get(
        f"{base}/route/v1/driving/{coords}",
        params={"overview": "full", "geometries": "geojson", "steps": "true",
                "alternatives": "false", "annotations": "false"},
        headers={"User-Agent": _env("ARGOS_SIMULATOR_USER_AGENT", "ARGOS-Terrestrial-Simulator/1.0")},
        timeout=(5, 30),
    )
    response.raise_for_status()
    payload = response.json()
    routes = payload.get("routes") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("code") != "Ok" or not routes:
        code = payload.get("code", "réponse invalide") if isinstance(payload, dict) else "réponse invalide"
        raise RuntimeError(f"OSRM n'a pas trouvé de route routière ({code})")
    route = routes[0]
    geometry = route.get("geometry") or {}
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(geometry, dict) or geometry.get("type") != "LineString" or not isinstance(coordinates, list) or len(coordinates) < 2:
        raise RuntimeError("OSRM n'a pas fourni une géométrie GeoJSON exploitable")
    clean = []
    for point in coordinates:
        if not isinstance(point, list) or len(point) < 2:
            raise RuntimeError("Coordonnée GeoJSON OSRM invalide")
        lon, lat = float(point[0]), float(point[1])
        if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise RuntimeError("Coordonnée GeoJSON OSRM hors limites")
        clean.append([lon, lat])
    distance_m, duration_s = float(route.get("distance") or 0), float(route.get("duration") or 0)
    if distance_m <= 0 or duration_s <= 0:
        raise RuntimeError("OSRM a retourné une distance ou durée nulle")
    steps = []
    for leg in route.get("legs") or []:
        for step in leg.get("steps") or []:
            maneuver = step.get("maneuver") or {}
            steps.append({
                "name": str(step.get("name") or "")[:160],
                "distance_m": float(step.get("distance") or 0),
                "duration_s": float(step.get("duration") or 0),
                "instruction_type": str(maneuver.get("type") or "")[:40],
                "modifier": str(maneuver.get("modifier") or "")[:40],
                "location": maneuver.get("location"),
            })
    now = _utcnow()
    return {
        "route_name": scenario["route_name"], "origin": origin, "destination": destination,
        "mode": scenario["mode"], "profile": "driving",
        "geometry": {"type": "LineString", "coordinates": clean},
        "distance_m": distance_m, "duration_s": duration_s,
        "source": base, "source_name": "OpenStreetMap road graph via OSRM",
        "attribution": "© OpenStreetMap contributors · OpenStreetMap data under ODbL",
        "retrieved_at": now.isoformat(), "route_version": payload.get("data_version"),
        "steps": steps, "limitations": ROUTE_LIMITATIONS,
    }


def _haversine_m(a, b):
    lon1, lat1 = map(math.radians, a[:2])
    lon2, lat2 = map(math.radians, b[:2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(min(1.0, h)))


def position_on_route(geometry: dict, fraction: float) -> tuple[float, float, float]:
    """Interpolate [lon,lat] route coordinates by distance; return lat, lon, bearing."""
    coordinates = (geometry or {}).get("coordinates") or []
    if len(coordinates) < 2:
        raise ValueError("Géométrie de route insuffisante")
    segment_lengths = [_haversine_m(a, b) for a, b in zip(coordinates, coordinates[1:])]
    total = sum(segment_lengths)
    if total <= 0:
        raise ValueError("Géométrie de route de longueur nulle")
    target = max(0.0, min(1.0, float(fraction))) * total
    traversed = 0.0
    for index, length in enumerate(segment_lengths):
        if target <= traversed + length or index == len(segment_lengths) - 1:
            ratio = 0.0 if length <= 0 else max(0.0, min(1.0, (target - traversed) / length))
            a, b = coordinates[index], coordinates[index + 1]
            lon, lat = a[0] + ratio * (b[0] - a[0]), a[1] + ratio * (b[1] - a[1])
            lat1, lat2 = math.radians(a[1]), math.radians(b[1])
            dlon = math.radians(b[0] - a[0])
            bearing = (math.degrees(math.atan2(
                math.sin(dlon) * math.cos(lat2),
                math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon),
            )) + 360) % 360
            return lat, lon, bearing
        traversed += length
    return coordinates[-1][1], coordinates[-1][0], 0.0


def offset_laterally(latitude: float, longitude: float, bearing: float, distance_m: float):
    """Move a simulated point laterally from a route by a spherical bearing offset."""
    angular = float(distance_m) / 6_371_000
    direction = math.radians((float(bearing) + 90) % 360)
    lat1, lon1 = math.radians(latitude), math.radians(longitude)
    lat2 = math.asin(math.sin(lat1) * math.cos(angular)
                     + math.cos(lat1) * math.sin(angular) * math.cos(direction))
    lon2 = lon1 + math.atan2(math.sin(direction) * math.sin(angular) * math.cos(lat1),
                             math.cos(angular) - math.sin(lat1) * math.sin(lat2))
    return math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180


def build_scenario_tick(*, session_uid: str, scenario_code: str, route: dict,
                        elapsed_wall_s: float, time_scale: int, sequence: int,
                        started_at: datetime, shock_threshold_g: float = 5.0,
                        speed_limit_kmh: float = 80.0,
                        scenario_config: dict | None = None) -> dict:
    """Build one SIMULATION-only sample. No measurement is asserted as real."""
    if scenario_code not in SCENARIOS:
        raise ValueError("Scénario terrestre non reconnu")
    scale = max(1, int(time_scale))
    config = scenario_config or load_scenario_configuration()[scenario_code]
    event_config = config.get("events") or {}
    elapsed_sim_s = max(0.0, float(elapsed_wall_s) * scale)
    minute = elapsed_sim_s / 60
    perturbation = scenario_code == "kribi_bertoua"
    stop_start, stop_end = map(float, event_config.get("immobilization_minutes", [30, 220])) if perturbation else (0.0, 0.0)
    stop_duration = max(0.0, stop_end - stop_start)
    stopped_minutes = max(0.0, min(stop_duration, minute - stop_start)) if perturbation else 0.0
    moving_minutes = max(0.0, minute - stopped_minutes)
    route_minutes = float(route["duration_s"]) / 60
    progress = max(0.0, min(0.999, moving_minutes / max(route_minutes, 1e-6)))
    latitude, longitude, heading = position_on_route(route["geometry"], progress)
    route_alert = None
    max_test_deviation_m = float(config.get("max_test_lateral_deviation_m", 2000))
    corridor_width_m = float(config.get("corridor_width_m", 1000))
    threshold_percent = float(config.get("route_alert_threshold_percent", 60))
    deviation_start, deviation_end = map(float, event_config.get("route_deviation_minutes", [5, 15])) if perturbation else (0.0, 0.0)
    deviation_duration = max(0.0, deviation_end - deviation_start)
    lateral_distance = 0.0
    if perturbation and deviation_start <= minute < deviation_end:
        # Progressive departure and return; 60% means 60% of this configured maximum.
        phase = (minute - deviation_start) / max(deviation_duration, 1e-6)
        ramp = phase * 2 if phase <= 0.5 else (1.0 - phase) * 2
        lateral_distance = max(0.0, ramp) * (threshold_percent / 100) * max_test_deviation_m
        latitude, longitude = offset_laterally(latitude, longitude, heading, lateral_distance)
        threshold_start = deviation_start + deviation_duration * 0.25
        threshold_end = deviation_start + deviation_duration * 0.75
        minimum_duration_minutes = max(0.0, float(config.get("route_deviation_min_duration_simulated_seconds", 60)) / 60)
        if (lateral_distance >= corridor_width_m * threshold_percent / 100
                and minute >= threshold_start + minimum_duration_minutes
                and minute <= threshold_end):
            route_alert = {"event_type": "route_deviation_simulated", "severity": "warning",
                           "deviation_m": round(lateral_distance, 1),
                           "recommendation": "Écart de route simulé au seuil de démonstration; vérifier la route affichée."}

    stopped = perturbation and stop_start <= minute < stop_end
    if stopped:
        speed_kmh = 0.0
    else:
        speed_kmh = max(1.0, route["distance_m"] / route["duration_s"] * 3.6)
    shock_start, shock_end = map(float, event_config.get("shock_episode_minutes", [10, 30])) if perturbation else (0.0, 0.0)
    in_shock_episode = perturbation and shock_start <= minute < shock_end
    shock_factors = tuple(config.get("shock_factors") or (1.2, 1.4, 1.1, 2.1))
    shock = float(shock_threshold_g) * shock_factors[(sequence - 1) % len(shock_factors)] if in_shock_episode else 0.12
    door_start, door_end = map(float, event_config.get("door_open_minutes", [20, 30])) if perturbation else (0.0, 0.0)
    door_open = bool(perturbation and door_start <= minute < door_end)
    door_orientation = str(config.get("door_orientation") or "N")
    sensors = {
        "temperature": 25.0, "humidity": 65.0, "shock": round(shock, 2),
        "pressure": 1007.0, "flameDetected": False, "doorOpen": door_open,
        "doorOrientation": door_orientation if door_open else None,
        "doorOrientationOrigin": "SIMULATED_ONLY" if door_open else None,
        "batteryLevel": 98.0, "securityAlarm": False,
    }
    events = []
    if route_alert:
        events.append(route_alert)
    if in_shock_episode:
        events.append({"event_type": "shock_episode_simulated",
                       "severity": "critical" if shock >= 2 * float(shock_threshold_g) else "warning",
                       "recommendation": "Chocs simulés au-dessus du seuil configuré; inspection à évaluer dans cette démonstration."})
    if door_open:
        events.append({"event_type": "door_open_simulated", "severity": "warning",
                       "recommendation": "Ouverture simulée; vérifier l'autorisation et l'état du scellé dans la démonstration.",
                       "orientation": door_orientation, "orientation_origin": "SIMULATED_ONLY"})
    if perturbation and stop_start <= minute < stop_start + 1:
        events.append({"event_type": "road_incident_simulated", "severity": "warning",
                       "confirmation_status": "SIMULATED_ONLY", "recommendation": "Immobilisation simulée pour le scénario; aucun accident réel n'est signalé."})
    if stopped:
        events.append({"event_type": "prolonged_stop_simulated", "severity": "warning",
                       "recommendation": "Immobilisation simulée; contrôler la sécurité et l'évolution de l'ETA de démonstration."})
    skid_start, skid_end = map(float, event_config.get("skid_risk_minutes", [235, 245])) if perturbation else (0.0, 0.0)
    if perturbation and skid_start <= minute < skid_end:
        events.append({"event_type": "skid_risk_simulated", "severity": "warning",
                       "confidence": str(config.get("skid_risk_confidence") or "low"), "missing_inputs": ["accélération latérale mesurée", "état réel de chaussée", "pluie/adhérence"],
                       "recommendation": "Risque simulé à faible confiance. Réduisez progressivement la vitesse et adaptez la conduite aux conditions observées."})

    route_duration_s = float(route["duration_s"])
    remaining_route_s = max(0.0, route_duration_s * (1.0 - progress))
    eta_reference = started_at + timedelta(seconds=route_duration_s / scale)
    remaining_stop_real_s = max(0.0, (stop_start + stop_duration - minute) * 60 / scale) if stopped else 0.0
    eta_current = _utcnow() + timedelta(seconds=remaining_route_s / scale + remaining_stop_real_s)
    simulated_now = started_at + timedelta(seconds=elapsed_sim_s)
    return {
        "batch_uid": str(uuid4()), "sequence": int(sequence), "measured_at": _utcnow().isoformat(),
        "simulated_at": simulated_now.isoformat(), "simulated_elapsed_seconds": elapsed_sim_s,
        "latitude": latitude, "longitude": longitude, "speed_kmh": round(speed_kmh, 1),
        "heading": round(heading, 1), "remaining_distance_m": round(route["distance_m"] * (1 - progress), 1),
        "stopped_seconds": stopped_minutes * 60,
        "vehicle_state": "stopped" if stopped else "moving",
        "eta_reference_at": eta_reference.isoformat(), "eta_current_at": eta_current.isoformat(),
        "eta_delay_seconds": round((eta_current - eta_reference).total_seconds(), 1),
        "sensor_values": sensors, "active_events": events,
        "rule_assessments": {
            "route_deviation_definition": {"max_test_lateral_deviation_m": max_test_deviation_m,
                                            "simulated_offset_m": round(lateral_distance, 1),
                                            "corridor_width_m": corridor_width_m,
                                            "alert_threshold_percent_of_corridor": threshold_percent,
                                            "minimum_duration_simulated_seconds": float(config.get("route_deviation_min_duration_simulated_seconds", 60)),
                                            "threshold_duration_met": route_alert is not None},
            "shock_threshold_source": "configured_box_threshold_or_ARGOS_fallback",
            "skid_risk_confidence": "low_when_road_or_lateral_inputs_missing",
        },
        "provenance": {"dataOrigin": "SYNTHETIC", "sessionUid": str(session_uid),
                       "scenarioId": scenario_code, "sequence": int(sequence),
                       "sampleLabel": "simulated_" + (events[0]["event_type"] if events else "normal")},
    }


def evaluate_simulated_rules(sample: dict, route: dict, thresholds) -> dict:
    """Run existing deterministic ARGOS rules without persistence side effects."""
    from app.modules.iot.iot_event_service import add_configured_threshold_alerts
    from app.services.route_monitor_service import route_deviation
    from app.services.proactive_risk_service import assess_window

    sensors = sample.get("sensor_values") or {}
    event_payload = {
        "temperature": sensors.get("temperature"), "humidite": sensors.get("humidity"),
        "chocs": sensors.get("shock"), "pressions": sensors.get("pressure"),
        "vitesse": sample.get("speed_kmh"), "battery_level": sensors.get("batteryLevel"),
        "notif": [],
    }
    configured = add_configured_threshold_alerts(event_payload, thresholds)
    waypoints = [[point[1], point[0]] for point in route["geometry"]["coordinates"]]
    deviation = route_deviation(sample["latitude"], sample["longitude"], waypoints,
                                corridor_width_m=1000, accuracy_m=0)
    deviation["above_alert_threshold"] = deviation["deviation_score_percent"] >= 60
    risk = assess_window([{"shock": sensors.get("shock"), "door_open": sensors.get("doorOpen"),
                           "security_alarm": sensors.get("securityAlarm"),
                           "measured_at": datetime.fromisoformat(sample["simulated_at"])}],
                         [sample.get("speed_kmh")], {
                             "choc_max": getattr(thresholds, "choc_max", None),
                             "vitesse_max": getattr(thresholds, "vitesse_max", None),
                         })
    return {"configured_threshold_alerts": configured, "route_deviation": deviation,
            "deterministic_risk": risk}


def build_simulated_telemetry_contract(sample: dict, black_box_id: int,
                                      container_id: str | None = None) -> dict:
    """Build and validate the real IoT payload shape without sending it to ingestion."""
    from app.modules.iot.validator import validate_telemetry_payload

    sensors = sample["sensor_values"]
    payload = {
        "messageId": sample["batch_uid"], "type": "telemetry",
        "deviceUid": f"ARGOS-SIM-{sample['provenance']['sessionUid'][:8]}-{sample['provenance']['scenarioId']}",
        "blackBoxId": int(black_box_id), "timestamp": sample["measured_at"],
        "sequence": int(sample["sequence"]),
        "position": {"latitude": sample["latitude"], "longitude": sample["longitude"],
                     "accuracy": 10.0, "speed": sample["speed_kmh"],
                     "heading": sample["heading"], "source": "ARGOS_SIMULATOR"},
        "sensors": {"temperature": sensors["temperature"], "humidity": sensors["humidity"],
                    "shock": min(200.0, sensors["shock"]), "pressure": sensors["pressure"],
                    "flameDetected": sensors["flameDetected"], "doorOpen": sensors["doorOpen"],
                    "batteryLevel": sensors["batteryLevel"], "securityAlarm": sensors["securityAlarm"]},
        "modes": {"securityEnabled": False, "audioRecordingEnabled": False,
                  "audioListeningEnabled": False, "flameDetectionEnabled": False},
        "quality": {"dhtValid": True, "mpuValid": True, "gpsValid": True,
                    "distanceValid": False, "sdReady": False, "pressureMeasured": False,
                    "batteryMeasured": False, "timestampSource": "SIMULATION",
                    "dataOrigin": "SYNTHETIC", "datasetId": sample["provenance"]["sessionUid"],
                    "scenarioId": sample["provenance"]["scenarioId"],
                    "sampleLabel": sample["provenance"]["sampleLabel"]},
    }
    if container_id:
        payload["containerId"] = str(container_id)
    validate_telemetry_payload(payload)
    return payload


def to_json(value):
    """JSON encoder default used for timestamps and SQLAlchemy row values."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _severity_rank(value):
    return {"info": 0, "warning": 1, "critical": 2}.get(str(value), 0)


def _update_simulation_episodes(session_uid, scenario_code, sample):
    from app.extensions import db
    from sqlalchemy import text

    active = {str(event["event_type"]): event for event in sample.get("active_events", [])}
    current_simulated_at = datetime.fromisoformat(sample["simulated_at"])
    current_minute = float(sample["simulated_elapsed_seconds"]) / 60
    rows = db.session.execute(text("""
        SELECT episode_uid,event_type,severity,status,last_simulated_at,evidence
        FROM brady.argos_transport_sim_episodes
        WHERE session_uid=CAST(:uid AS uuid) AND scenario_code=:scenario
          AND status IN ('new','ongoing','aggravated')
        ORDER BY created_at DESC
    """), {"uid": session_uid, "scenario": scenario_code}).fetchall()
    open_by_type = {row.event_type: row for row in rows}
    for event_type, event in active.items():
        existing = open_by_type.pop(event_type, None)
        gap_minutes = 20 if "shock" in event_type else 10
        if existing and (current_simulated_at - existing.last_simulated_at).total_seconds() <= gap_minutes * 60:
            evidence = _json_value(existing.evidence, []) if "_json_value" in globals() else existing.evidence
            if isinstance(evidence, str):
                try: evidence = json.loads(evidence)
                except ValueError: evidence = []
            evidence = list(evidence or [])
            evidence.append({"sequence": sample["sequence"], "simulated_at": sample["simulated_at"], "event": event})
            aggravated = _severity_rank(event.get("severity")) > _severity_rank(existing.severity)
            status = "aggravated" if aggravated else "ongoing"
            db.session.execute(text("""
                UPDATE brady.argos_transport_sim_episodes
                SET severity=:severity,status=:status,last_sequence=:sequence,
                    last_simulated_at=CAST(:simulated_at AS timestamptz),
                    evidence=CAST(:evidence AS jsonb),recommendation=:recommendation,updated_at=NOW()
                WHERE episode_uid=CAST(:episode AS uuid)
            """), {"severity": event.get("severity", "info"), "status": status,
                    "sequence": sample["sequence"], "simulated_at": sample["simulated_at"],
                    "evidence": json.dumps(evidence[-200:], ensure_ascii=False),
                    "recommendation": event.get("recommendation"), "episode": str(existing.episode_uid)})
        else:
            from uuid import uuid4
            db.session.execute(text("""
                INSERT INTO brady.argos_transport_sim_episodes
                    (episode_uid,session_uid,scenario_code,event_type,severity,status,
                     first_sequence,last_sequence,first_simulated_at,last_simulated_at,
                     evidence,recommendation,provenance)
                VALUES (CAST(:episode AS uuid),CAST(:uid AS uuid),:scenario,:type,:severity,'new',
                    :sequence,:sequence,CAST(:simulated_at AS timestamptz),CAST(:simulated_at AS timestamptz),
                    CAST(:evidence AS jsonb),:recommendation,'{"dataOrigin":"SYNTHETIC"}'::jsonb)
            """), {"episode": str(uuid4()), "uid": session_uid, "scenario": scenario_code,
                    "type": event_type, "severity": event.get("severity", "info"),
                    "sequence": sample["sequence"], "simulated_at": sample["simulated_at"],
                    "evidence": json.dumps([{"sequence": sample["sequence"],
                                             "simulated_at": sample["simulated_at"], "event": event}], ensure_ascii=False),
                    "recommendation": event.get("recommendation")})

    for event_type, existing in open_by_type.items():
        gap_minutes = 20 if "shock" in event_type else 10
        gap_s = (current_simulated_at - existing.last_simulated_at).total_seconds()
        if gap_s >= gap_minutes * 60:
            db.session.execute(text("""
                UPDATE brady.argos_transport_sim_episodes
                SET status='resolved',closed_at=CAST(:closed AS timestamptz),updated_at=NOW()
                WHERE episode_uid=CAST(:episode AS uuid)
            """), {"closed": current_simulated_at.isoformat(), "episode": str(existing.episode_uid)})


def process_one_simulation_tick(session_uid: str, now: datetime | None = None) -> dict:
    """Advance one active simulation; all writes stay in simulation-only tables."""
    from app.extensions import db
    from app.modules.iot.repository import get_alert_thresholds
    from sqlalchemy import text

    now = now or _utcnow()
    session = db.session.execute(text("""
        SELECT session_uid,status,interval_seconds,duration_seconds,time_scale,
               active_elapsed_seconds,last_active_at,worker_heartbeat_at,last_tick_at,started_at
        FROM brady.argos_transport_sim_sessions
        WHERE session_uid=CAST(:uid AS uuid) FOR UPDATE
    """), {"uid": session_uid}).fetchone()
    if not session or session.status != "RUNNING":
        db.session.rollback()
        return {"status": "inactive"}

    # If the worker was down, exclude that offline wall time from scenario time.
    heartbeat_stale = (session.worker_heartbeat_at is None or
                       (now - session.worker_heartbeat_at).total_seconds() > 15)
    last_active = session.last_active_at
    if heartbeat_stale or last_active is None:
        last_active = now
        session_elapsed = float(session.active_elapsed_seconds or 0)
    else:
        session_elapsed = float(session.active_elapsed_seconds or 0) + max(
            0.0, (now - last_active).total_seconds())

    if session_elapsed >= float(session.duration_seconds):
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_sessions
            SET active_elapsed_seconds=:elapsed,status='COMPLETED',last_active_at=NULL,
                stopped_at=:now,worker_heartbeat_at=:now,updated_at=:now
            WHERE session_uid=CAST(:uid AS uuid)
        """), {"uid": session_uid, "elapsed": session.duration_seconds, "now": now})
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_episodes
            SET status='resolved',closed_at=COALESCE(closed_at,:now),updated_at=:now
            WHERE session_uid=CAST(:uid AS uuid) AND status IN ('new','ongoing','aggravated')
        """), {"uid": session_uid, "now": now})
        db.session.commit()
        return {"status": "completed"}

    due = session.last_tick_at is None or (
        now - session.last_tick_at
    ).total_seconds() >= float(session.interval_seconds)
    if not due:
        db.session.execute(text("""
            UPDATE brady.argos_transport_sim_sessions SET last_active_at=:active_at,
                worker_heartbeat_at=:now,active_elapsed_seconds=:elapsed,updated_at=:now
            WHERE session_uid=CAST(:uid AS uuid)
        """), {"uid": session_uid, "active_at": now,
                "now": now, "elapsed": session_elapsed})
        db.session.commit()
        return {"status": "heartbeat"}

    scenarios = db.session.execute(text("""
        SELECT scenario_code,black_box_id,container_id,route_geometry,route_distance_m,route_duration_s,scenario_config
        FROM brady.argos_transport_sim_scenarios
        WHERE session_uid=CAST(:uid AS uuid) ORDER BY scenario_code
    """), {"uid": session_uid}).fetchall()
    if len(scenarios) != 2:
        db.session.rollback()
        raise RuntimeError("La session doit contenir ses deux scénarios")

    results = []
    for scenario in scenarios:
        previous = db.session.execute(text("""
            SELECT sequence FROM brady.argos_transport_sim_samples
            WHERE session_uid=CAST(:uid AS uuid) AND scenario_code=:scenario
            ORDER BY sequence DESC LIMIT 1
        """), {"uid": session_uid, "scenario": scenario.scenario_code}).scalar()
        sequence = int(previous or 0) + 1
        configured_thresholds = get_alert_thresholds(scenario.black_box_id)
        if configured_thresholds is None:
            class FallbackThresholds:
                temp_min = None
                temp_max = None
                humi_min = None
                humi_max = None
                choc_max = 5.0
                pression_min = None
                pression_max = None
                vitesse_max = 80.0
            configured_thresholds = FallbackThresholds()
        from app.services.shock_assessment import resolve_shock_threshold
        shock_threshold = resolve_shock_threshold(getattr(configured_thresholds, "choc_max", None))
        route = {"geometry": _json_load(scenario.route_geometry),
                 "distance_m": float(scenario.route_distance_m),
                 "duration_s": float(scenario.route_duration_s)}
        sample = build_scenario_tick(
            session_uid=session_uid, scenario_code=scenario.scenario_code, route=route,
            elapsed_wall_s=session_elapsed, time_scale=session.time_scale,
            sequence=sequence, started_at=session.started_at,
            shock_threshold_g=shock_threshold,
            scenario_config=_json_load(scenario.scenario_config),
            speed_limit_kmh=float(getattr(configured_thresholds, "vitesse_max", None) or 80),
        )
        sample["telemetry_payload"] = build_simulated_telemetry_contract(
            sample, scenario.black_box_id, scenario.container_id)
        sample["rule_assessments"] = evaluate_simulated_rules(sample, route, configured_thresholds)
        for alert in sample["rule_assessments"].get("configured_threshold_alerts", []):
            lowered = str(alert).lower()
            event_type = ("shock_threshold_simulated" if "choc" in lowered else
                          "speed_threshold_simulated" if "vitesse" in lowered else
                          "sensor_threshold_simulated")
            sample["active_events"].append({
                "event_type": event_type,
                "severity": "critical" if "sévère" in lowered or "severe" in lowered else "warning",
                "evidence": str(alert)[:240],
                "recommendation": "Signal de règle ARGOS évalué en simulation; contrôler la mesure et le seuil avant toute décision terrain.",
            })
        simulated_at = datetime.fromisoformat(sample["simulated_at"])
        db.session.execute(text("""
            INSERT INTO brady.argos_transport_sim_samples
                (session_uid,scenario_code,batch_uid,sequence,measured_at,simulated_at,
                 simulated_elapsed_seconds,latitude,longitude,speed_kmh,heading,
                 remaining_distance_m,stopped_seconds,vehicle_state,eta_reference_at,
                 eta_current_at,eta_delay_seconds,sensor_values,active_events,
                 rule_assessments,provenance,telemetry_payload)
            VALUES (CAST(:uid AS uuid),:scenario,CAST(:batch_uid AS uuid),:sequence,CAST(:measured AS timestamptz),
                CAST(:simulated AS timestamptz),:elapsed,:lat,:lon,:speed,:heading,
                :remaining,:stopped,:state,CAST(:eta_reference AS timestamptz),
                CAST(:eta_current AS timestamptz),:delay,CAST(:sensors AS jsonb),
                CAST(:events AS jsonb),CAST(:rules AS jsonb),CAST(:provenance AS jsonb),CAST(:telemetry AS jsonb))
        """), {"uid": session_uid, "scenario": scenario.scenario_code,
                "batch_uid": sample["batch_uid"], "sequence": sequence, "measured": sample["measured_at"],
                "simulated": sample["simulated_at"], "elapsed": sample["simulated_elapsed_seconds"],
                "lat": sample["latitude"], "lon": sample["longitude"],
                "speed": sample["speed_kmh"], "heading": sample["heading"],
                "remaining": sample["remaining_distance_m"], "stopped": sample["stopped_seconds"],
                "state": sample["vehicle_state"], "eta_reference": sample["eta_reference_at"],
                "eta_current": sample["eta_current_at"], "delay": sample["eta_delay_seconds"],
                "sensors": json.dumps(sample["sensor_values"], ensure_ascii=False),
                "events": json.dumps(sample["active_events"], ensure_ascii=False),
                "rules": json.dumps(sample["rule_assessments"], ensure_ascii=False, default=to_json),
                "provenance": json.dumps(sample["provenance"], ensure_ascii=False),
                "telemetry": json.dumps(sample["telemetry_payload"], ensure_ascii=False, default=to_json)})
        _update_simulation_episodes(session_uid, scenario.scenario_code, sample)
        results.append({"scenario_code": scenario.scenario_code, "sequence": sequence})

    db.session.execute(text("""
        UPDATE brady.argos_transport_sim_sessions
        SET active_elapsed_seconds=:elapsed,last_active_at=:now,last_tick_at=:now,
            worker_heartbeat_at=:now,updated_at=:now,last_error=NULL
        WHERE session_uid=CAST(:uid AS uuid)
    """), {"uid": session_uid, "elapsed": session_elapsed, "now": now})
    db.session.commit()
    return {"status": "tick", "scenarios": results, "elapsed_seconds": session_elapsed}


def _json_load(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return value or {}
