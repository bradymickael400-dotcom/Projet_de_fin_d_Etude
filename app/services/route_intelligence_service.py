"""Explainable route and port context built from a box's authorized telemetry."""

import json
import math
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.extensions import db
from app.services.geofence_service import distance_meters, point_in_polygon
from app.services.route_monitor_service import route_deviation


def _distance_m(a, b):
    return distance_meters(a[0], a[1], b[0], b[1])


def _route_remaining_distance(latitude, longitude, waypoints):
    """Project the current GPS fix onto the nearest planned segment and sum its remainder."""
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        return None
    point = (float(latitude), float(longitude))
    legs = [_distance_m(a, b) for a, b in zip(waypoints, waypoints[1:])]
    best = None
    for index, (start, end) in enumerate(zip(waypoints, waypoints[1:])):
        lat0 = math.radians(point[0])
        scale_x = math.cos(lat0) * math.pi / 180 * 6_371_000
        scale_y = math.pi / 180 * 6_371_000
        px, py = point[1] * scale_x, point[0] * scale_y
        ax, ay = start[1] * scale_x, start[0] * scale_y
        bx, by = end[1] * scale_x, end[0] * scale_y
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        fraction = 0.0 if not length_sq else max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / length_sq))
        projected = (start[0] + fraction * (end[0] - start[0]),
                     start[1] + fraction * (end[1] - start[1]))
        cross_track = _distance_m(point, projected)
        remaining = _distance_m(projected, end) + sum(legs[index + 1:])
        candidate = (cross_track, remaining)
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        return None
    return best[0] + best[1], best[0]


def _estimate_eta(points, route, now=None):
    now = now or datetime.now(timezone.utc)
    base = {"status": "unavailable", "estimated_arrival_at": None,
            "remaining_distance_km": None, "estimated_speed_kmh": None,
            "confidence": "unavailable", "method": "planned_route_distance_divided_by_recent_gps_speed"}
    if not route or not points:
        return {**base, "reason": "Aucun itinéraire planifié ou aucune position GPS exploitable."}
    waypoints = route.get("waypoints")
    if isinstance(waypoints, str):
        try:
            waypoints = json.loads(waypoints)
        except ValueError:
            waypoints = []
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        return {**base, "reason": "Le trajet planifié ne contient pas assez de points."}

    latest = points[-1]
    measured_at = latest.get("measured_at")
    try:
        measured = datetime.fromisoformat(str(measured_at).replace("Z", "+00:00"))
        if measured.tzinfo is None:
            measured = measured.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return {**base, "status": "stale", "reason": "Horodatage GPS invalide."}
    age_seconds = max(0, int((now - measured.astimezone(timezone.utc)).total_seconds()))
    if age_seconds > 20 * 60:
        return {**base, "status": "stale", "last_position_at": measured_at,
                "reason": "Position trop ancienne pour produire une estimation fiable."}

    projected = _route_remaining_distance(latest["latitude"], latest["longitude"], waypoints)
    if projected is None:
        return {**base, "reason": "Distance restante au trajet impossible à calculer."}
    remaining_m, cross_track_m = projected
    if remaining_m <= 250:
        return {**base, "status": "arrived", "remaining_distance_km": round(remaining_m / 1000, 2),
                "destination": {"latitude": waypoints[-1][0], "longitude": waypoints[-1][1]},
                "route_name": route.get("route_name"), "last_position_at": measured_at,
                "reason": "La dernière position est à moins de 250 m du point final planifié."}

    recent = points[-6:]
    # ARGOS GPS payloads provide speed in km/h (same unit as `vitesse`).
    speeds = [float(p["speed"]) for p in recent
              if p.get("speed") is not None and math.isfinite(float(p["speed"]))
              and 1 < float(p["speed"]) <= 300]
    if not speeds:
        return {**base, "status": "stopped", "remaining_distance_km": round(remaining_m / 1000, 2),
                "destination": {"latitude": waypoints[-1][0], "longitude": waypoints[-1][1]},
                "route_name": route.get("route_name"), "last_position_at": measured_at,
                "reason": "La vitesse GPS récente est nulle ou insuffisante."}

    speeds.sort()
    middle = len(speeds) // 2
    speed_kmh = speeds[middle] if len(speeds) % 2 else (speeds[middle - 1] + speeds[middle]) / 2
    seconds = remaining_m / (speed_kmh * 1000 / 3600)
    confidence = "medium" if len(speeds) >= 3 and age_seconds <= 5 * 60 else "low"
    arrival = now + timedelta(seconds=seconds)
    return {
        "status": "estimated", "estimated_arrival_at": arrival.isoformat(),
        "remaining_distance_km": round(remaining_m / 1000, 2),
        "estimated_speed_kmh": round(speed_kmh, 1), "confidence": confidence,
        "method": "distance restante sur les points du trajet / médiane des vitesses GPS récentes",
        "route_name": route.get("route_name"),
        "destination": {"latitude": waypoints[-1][0], "longitude": waypoints[-1][1]},
        "last_position_at": measured_at, "position_age_seconds": age_seconds,
        "distance_to_planned_route_m": round(cross_track_m, 1),
        "caveat": "Projection indicative : suppose le maintien du trajet et de la vitesse récents; arrêts, trafic, météo, transbordements et attentes portuaires ne sont pas modélisés.",
    }


def estimate_arrivals_for_boxes(black_box_ids):
    """Batch ETA estimates for box IDs already authorized by the calling route."""
    box_ids = sorted({int(value) for value in black_box_ids if str(value).isdigit() and int(value) > 0})
    if not box_ids:
        return {}
    params = {f"box_{index}": value for index, value in enumerate(box_ids)}
    placeholders = ",".join(f":box_{index}" for index in range(len(box_ids)))
    try:
        rows = db.session.execute(text(f"""
            WITH ranked_positions AS (
                SELECT p.black_box_id,p.latitude,p.longitude,p.measured_at,p.speed,p.accuracy,
                       ROW_NUMBER() OVER (PARTITION BY p.black_box_id ORDER BY p.measured_at DESC,p.id DESC) AS rn
                FROM positions p
                WHERE p.black_box_id IN ({placeholders})
                  AND p.latitude IS NOT NULL AND p.longitude IS NOT NULL
            )
            SELECT p.black_box_id,p.latitude,p.longitude,p.measured_at,p.speed,p.accuracy,
                   r.route_name,r.waypoints,r.mode
            FROM ranked_positions p
            LEFT JOIN brady.argos_planned_routes r
              ON r.black_box_id=p.black_box_id AND r.enabled=TRUE
            WHERE p.rn<=6
            ORDER BY p.black_box_id,p.measured_at ASC
        """), params).fetchall()
    except Exception:
        db.session.rollback()
        return {str(box_id): {"status": "unavailable", "estimated_arrival_at": None,
                "reason": "Le suivi GPS ou le trajet planifié n’est pas disponible."} for box_id in box_ids}

    grouped = {}
    routes = {}
    for row in rows:
        item = dict(row._mapping)
        box_id = int(item.pop("black_box_id"))
        route_name, waypoints, mode = item.pop("route_name"), item.pop("waypoints"), item.pop("mode")
        if item["measured_at"]:
            item["measured_at"] = item["measured_at"].isoformat()
        for key in ("latitude", "longitude", "speed", "accuracy"):
            if item.get(key) is not None:
                item[key] = float(item[key])
        grouped.setdefault(box_id, []).append(item)
        if route_name:
            routes[box_id] = {"route_name": route_name, "waypoints": waypoints, "mode": mode}
    return {str(box_id): _estimate_eta(grouped.get(box_id, []), routes.get(box_id))
            for box_id in box_ids}


def _track_points(black_box_id, limit):
    rows = db.session.execute(text("""
        SELECT p.latitude,p.longitude,p.measured_at,p.speed,p.heading,p.accuracy,p.source,
               p.container_id,p.raw_message_id,sr.sequence,sr.temperature,sr.humidity,
               sr.shock,sr.battery_level,sr.flame_detected,sr.door_open,sr.security_alarm,
               sr.quality,e.log_action,e.notif
        FROM positions p
        LEFT JOIN sensor_readings sr ON sr.raw_message_id=p.raw_message_id
        LEFT JOIN LATERAL (
            SELECT log_action,notif FROM evenement_save
            WHERE id_boite=p.black_box_id AND sequence=sr.sequence
            ORDER BY COALESCE(horodatage,created_at) DESC LIMIT 1
        ) e ON TRUE
        WHERE p.black_box_id=:box AND p.latitude IS NOT NULL AND p.longitude IS NOT NULL
        ORDER BY p.measured_at DESC,p.id DESC LIMIT :limit
    """), {"box": int(black_box_id), "limit": int(limit)}).fetchall()
    points = []
    for row in reversed(rows):
        item = dict(row._mapping)
        stamp = item.get("measured_at")
        item["measured_at"] = stamp.isoformat() if stamp else None
        item["latitude"] = float(item["latitude"])
        item["longitude"] = float(item["longitude"])
        for key in ("speed", "heading", "accuracy", "temperature", "humidity", "shock", "battery_level"):
            if item.get(key) is not None:
                item[key] = float(item[key])
        item.pop("raw_message_id", None)
        points.append(item)
    return points


def _alerts_from_value(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item)[:300] for item in value if item]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item)[:300] for item in parsed if item]
        if isinstance(parsed, dict):
            return [str(parsed.get("message") or parsed.get("label") or parsed)[:300]]
    except (TypeError, ValueError):
        pass
    return [str(value)[:300]]


def _sensitive_events(points):
    events = []
    for point in points:
        details = _alerts_from_value(point.get("notif"))
        if point.get("flame_detected"):
            details.append("Détection de flamme")
        if point.get("security_alarm"):
            details.append("Alarme de sécurité active")
        if point.get("door_open"):
            details.append("Porte ouverte")

        score = (point.get("route_assessment") or {}).get("deviation_score_percent")
        if point.get("route_assessment", {}).get("above_alert_threshold"):
            details.append(f"Dérive de route : score opérationnel {score} %")
        details = list(dict.fromkeys(details))
        if not details:
            continue

        normalized = "".join(char for char in unicodedata.normalize("NFKD", " ".join(details).casefold())
                              if not unicodedata.combining(char))
        critical_terms = ("flamme", "incendie", "alarme de securite", "choc severe",
                          "ouverture non autorisee", "critique", "critical")
        severity = "danger" if any(term in normalized for term in critical_terms) else "warning"
        if score is not None and score >= 85:
            severity = "danger"
        events.append({
            "kind": "sensitive_transport_event",
            "severity": severity,
            "title": "Événement sensible détecté" if severity == "danger" else "Vigilance requise",
            "details": details[:12],
            "measured_at": point.get("measured_at"),
            "sequence": point.get("sequence"),
            "latitude": point["latitude"],
            "longitude": point["longitude"],
            "accuracy_m": point.get("accuracy"),
        })
    return events


def _route_summary(points, route):
    if not route:
        return {"configured": False, "route_name": None, "alert_active": False,
                "point_count": len(points), "deviation_count": 0,
                "threshold_semantics": "score opérationnel, non probabiliste"}
    waypoints = route["waypoints"]
    assessments = []
    for point in points:
        result = route_deviation(point["latitude"], point["longitude"], waypoints,
                                 route["corridor_width_m"], point.get("accuracy") or 0)
        result["above_alert_threshold"] = result["deviation_score_percent"] >= route["alert_threshold"]
        assessments.append(result)
        point["route_assessment"] = result
        point["route_state"] = "deviation" if result["above_alert_threshold"] else "on_corridor"

    groups = []
    for previous, current in zip(points, points[1:]):
        state = "deviation" if (previous["route_assessment"]["above_alert_threshold"]
                                 or current["route_assessment"]["above_alert_threshold"]) else "on_corridor"
        coordinates = [[previous["latitude"], previous["longitude"]],
                       [current["latitude"], current["longitude"]]]
        if groups and groups[-1]["state"] == state:
            if groups[-1]["coordinates"][-1] != coordinates[0]:
                groups[-1]["coordinates"].append(coordinates[0])
            groups[-1]["coordinates"].append(coordinates[1])
        else:
            groups.append({"state": state, "color": "red" if state == "deviation" else "cyan",
                           "coordinates": coordinates})
    return {
        "configured": True,
        "route_name": route["route_name"],
        "mode": route["mode"],
        "waypoints": waypoints,
        "corridor_width_m": int(route["corridor_width_m"]),
        "alert_threshold_percent": int(route["alert_threshold"]),
        "alert_active": any(a["above_alert_threshold"] for a in assessments),
        "point_count": len(points),
        "deviation_count": sum(1 for a in assessments if a["above_alert_threshold"]),
        "maximum_deviation_score_percent": max((a["deviation_score_percent"] for a in assessments), default=0),
        "maximum_distance_to_route_m": max((a["distance_to_route_m"] for a in assessments), default=0),
        "segments": groups,
        "threshold_semantics": "score géométrique opérationnel, pas une probabilité statistique",
    }


def route_tracking_for_box(black_box_id, limit=300):
    points = _track_points(black_box_id, max(2, min(int(limit), 2000)))
    row = db.session.execute(text("""
        SELECT route_name,mode,waypoints,corridor_width_m,alert_threshold,enabled,updated_at
        FROM brady.argos_planned_routes WHERE black_box_id=:box
    """), {"box": int(black_box_id)}).fetchone()
    route = None
    if row and row.enabled:
        route = dict(row._mapping)
        route["waypoints"] = route["waypoints"] if isinstance(route["waypoints"], list) else []
        route["updated_at"] = route["updated_at"].isoformat() if route.get("updated_at") else None
    summary = _route_summary(points, route)
    sensitive_events = _sensitive_events(points)
    eta = _estimate_eta(points, route)
    return {"black_box_id": int(black_box_id), "route": route, "summary": summary,
            "points": points, "sensitive_events": sensitive_events,
            "sensitive_event_count": len(sensitive_events),
            "estimated_arrival": eta,
            "generated_from": "positions_and_sensor_readings"}


def port_tracking_for_box(black_box_id, limit=500, include_points=True):
    points = _track_points(black_box_id, max(2, min(int(limit), 2000)))
    ports = [dict(row._mapping) for row in db.session.execute(text("""
        SELECT port_id,port_name,country,country_code,latitude,longitude,location_type,
               coordinate_precision,verification_status,coordinate_source,proximity_radius_m
        FROM brady.argos_port_locations WHERE enabled=TRUE
    """)).fetchall()]
    zones = [dict(row._mapping) for row in db.session.execute(text("""
        SELECT zone_id,zone_name,country,mode,polygon,source_key
        FROM brady.argos_geofence_zones WHERE enabled=TRUE
    """)).fetchall()]

    events = []
    previous_state = {}
    current_references = []
    compact_points = []
    for index, point in enumerate(points):
        near_ports = []
        inside_zones = []
        for port in ports:
            distance = distance_meters(point["latitude"], point["longitude"],
                                       port["latitude"], port["longitude"])
            radius = float(port.get("proximity_radius_m") or 3000)
            inside = distance <= radius
            key = ("port", port["port_id"])
            was_inside = previous_state.get(key)
            if inside:
                near_ports.append({"port_id": port["port_id"], "port_name": port["port_name"],
                    "country": port["country"], "distance_m": round(distance, 1),
                    "radius_m": round(radius), "verification_status": port["verification_status"],
                    "coordinate_precision": port["coordinate_precision"],
                    "classification": "reference_point_proximity_not_official_port_entry"})
            if inside and index == 0:
                events.append({"kind": "port_near_at_window_start", "measured_at": point["measured_at"],
                    "sequence": point.get("sequence"), "latitude": point["latitude"],
                    "longitude": point["longitude"], "port_id": port["port_id"],
                    "port_name": port["port_name"], "country": port["country"],
                    "distance_m": round(distance, 1), "radius_m": round(radius),
                    "verification_status": port["verification_status"],
                    "certainty": "proximity_only_transition_not_observed"})
            elif inside and was_inside is False:
                events.append({"kind": "port_proximity_entry", "measured_at": point["measured_at"],
                    "sequence": point.get("sequence"), "latitude": point["latitude"],
                    "longitude": point["longitude"], "port_id": port["port_id"],
                    "port_name": port["port_name"], "country": port["country"],
                    "distance_m": round(distance, 1), "radius_m": round(radius),
                    "verification_status": port["verification_status"],
                    "certainty": "indicative_proximity_only"})
            elif not inside and was_inside is True:
                events.append({"kind": "port_proximity_exit", "measured_at": point["measured_at"],
                    "sequence": point.get("sequence"), "port_id": port["port_id"],
                    "port_name": port["port_name"], "country": port["country"],
                    "certainty": "reference_radius_crossing"})
            previous_state[key] = inside

        for zone in zones:
            inside = point_in_polygon(point["latitude"], point["longitude"], zone["polygon"])
            key = ("zone", zone["zone_id"])
            was_inside = previous_state.get(key)
            if inside:
                inside_zones.append({"zone_id": zone["zone_id"], "zone_name": zone["zone_name"],
                                     "country": zone["country"], "mode": zone["mode"]})
            if inside and index == 0:
                events.append({"kind": "geofence_present_at_window_start", "measured_at": point["measured_at"],
                    "sequence": point.get("sequence"), "latitude": point["latitude"],
                    "longitude": point["longitude"], "zone_id": zone["zone_id"],
                    "zone_name": zone["zone_name"], "country": zone["country"],
                    "mode": zone["mode"], "source_key": zone["source_key"],
                    "certainty": "configured_polygon_presence_not_entry_transition"})
            elif inside and was_inside is False:
                events.append({"kind": "geofence_entry", "measured_at": point["measured_at"],
                    "sequence": point.get("sequence"), "latitude": point["latitude"],
                    "longitude": point["longitude"], "zone_id": zone["zone_id"],
                    "zone_name": zone["zone_name"], "country": zone["country"],
                    "mode": zone["mode"], "source_key": zone["source_key"],
                    "certainty": "configured_polygon_crossing_boundary_validation_required"})
            elif not inside and was_inside is True:
                events.append({"kind": "geofence_exit", "measured_at": point["measured_at"],
                    "sequence": point.get("sequence"), "zone_id": zone["zone_id"],
                    "zone_name": zone["zone_name"], "country": zone["country"],
                    "certainty": "configured_polygon_crossing_boundary_validation_required"})
            previous_state[key] = inside

        point["nearby_ports"] = near_ports
        point["inside_zones"] = inside_zones
        if index == len(points) - 1:
            current_references = near_ports
        if not include_points:
            compact_points.append({key: point[key] for key in
                ("measured_at", "sequence", "latitude", "longitude", "source", "accuracy")})

    events.sort(key=lambda item: (item.get("measured_at") or "", item.get("sequence") or 0))
    result = {"black_box_id": int(black_box_id), "point_count": len(points),
        "window_start": points[0]["measured_at"] if points else None,
        "window_end": points[-1]["measured_at"] if points else None,
        "current_nearby_ports": current_references, "events": events,
        "event_count": len(events),
        "limitations": ["Les rayons portuaires indiquent une proximité d'un point de référence, pas l'entrée dans une enceinte officielle.",
                        "Les polygones décrivent une traversée de la zone configurée; leur caractère officiel dépend de la source et de sa validation."],
    }
    if include_points:
        result["points"] = points
    else:
        result["sampled_points"] = compact_points[-20:]
    return result
