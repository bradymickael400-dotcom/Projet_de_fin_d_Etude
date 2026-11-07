"""Deterministic route-corridor monitoring for assigned black boxes."""
import math
import threading
from sqlalchemy import text
from app.extensions import db

EARTH_RADIUS_M = 6_371_000

def _distance_to_segment_m(point, start, end):
    """Approximate point-to-segment distance in a local equirectangular plane."""
    lat0 = math.radians(point[0])
    scale_x = math.cos(lat0) * math.pi / 180 * EARTH_RADIUS_M
    scale_y = math.pi / 180 * EARTH_RADIUS_M
    px, py = point[1] * scale_x, point[0] * scale_y
    ax, ay = start[1] * scale_x, start[0] * scale_y
    bx, by = end[1] * scale_x, end[0] * scale_y
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    ratio = 0 if not length_sq else max(0, min(1, ((px-ax)*dx + (py-ay)*dy) / length_sq))
    return math.hypot(px - (ax + ratio*dx), py - (ay + ratio*dy))

def validate_waypoints(value):
    if not isinstance(value, list) or len(value) < 2 or len(value) > 5000:
        raise ValueError("waypoints doit contenir entre 2 et 5000 points")
    result = []
    for point in value:
        if isinstance(point, dict):
            lat, lon = point.get("latitude"), point.get("longitude")
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            lat, lon = point
        else:
            raise ValueError("Chaque point doit contenir latitude et longitude")
        lat, lon = float(lat), float(lon)
        if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Coordonnées de route invalides")
        result.append([lat, lon])
    return result

def route_deviation(latitude, longitude, waypoints, corridor_width_m, accuracy_m=0):
    """Return an explainable operational score; it is not a statistical probability."""
    points = validate_waypoints(waypoints)
    distance = min(_distance_to_segment_m((latitude, longitude), a, b)
                   for a, b in zip(points, points[1:]))
    corridor = max(50.0, float(corridor_width_m))
    uncertainty = max(0.0, min(float(accuracy_m or 0), corridor))
    effective_distance = max(0.0, distance - uncertainty)
    score = round(max(0.0, min(100.0, (effective_distance / corridor) * 50)), 1)
    return {"distance_to_route_m": round(distance, 1), "corridor_width_m": round(corridor),
            "position_accuracy_m": round(uncertainty, 1), "deviation_score_percent": score,
            "score_method": "distance_to_route_corridor; 60 at 1.2 times the corridor width",
            "is_statistical_probability": False}

def route_assessment_for_box(black_box_id, latitude, longitude, accuracy_m=0):
    if latitude is None or longitude is None:
        return None
    route = db.session.execute(text("""
        SELECT route_name,mode,waypoints,corridor_width_m,alert_threshold
        FROM brady.argos_planned_routes WHERE black_box_id=:box AND enabled=TRUE
    """), {"box": int(black_box_id)}).fetchone()
    if not route:
        return None
    result = route_deviation(latitude, longitude, route.waypoints,
                            route.corridor_width_m, accuracy_m)
    result.update({"route_name": route.route_name, "mode": route.mode,
                   "alert_threshold_percent": route.alert_threshold,
                   "black_box_id": int(black_box_id),
                   "above_alert_threshold": result["deviation_score_percent"] >= route.alert_threshold})
    return result

def evaluate_route_position(black_box_id, latitude, longitude, measured_at,
                            accuracy_m=0, device_uid=None, sequence=None):
    if latitude is None or longitude is None:
        return None
    assessment = route_assessment_for_box(black_box_id, latitude, longitude, accuracy_m)
    if assessment is None:
        return None
    assessment["measured_at"] = measured_at.isoformat()
    if not assessment["above_alert_threshold"]:
        return assessment
    title = f"Écart de route — boîte #{black_box_id}"
    message = (f"{title} : score opérationnel {assessment['deviation_score_percent']} % "
               f"(seuil {assessment['alert_threshold_percent']} %), à {assessment['distance_to_route_m']} m "
               f"du corridor « {assessment['route_name']} ». Ce score n'est pas une probabilité statistique.")
    duplicate = db.session.execute(text("""
        SELECT 1 FROM notifications WHERE id_boite=:box AND type='ROUTE_DEVIATION'
          AND message LIKE :route_marker
          AND horodatage >= NOW() - INTERVAL '30 minutes' LIMIT 1
    """), {"box": int(black_box_id),
           "route_marker": f"%corridor « {assessment['route_name']} »%"}).scalar()
    if duplicate:
        return assessment
    db.session.execute(text("""
        INSERT INTO notifications(type,message,cible_role,id_boite,device_uid,sequence)
        VALUES('ROUTE_DEVIATION',:message,'all',:box,:device,:sequence)
    """), {"message": message, "box": int(black_box_id), "device": device_uid, "sequence": sequence})
    from app.regulatory.history import record_decision
    record_decision(identity={"role": "system", "user_id": "route_monitor_service"},
        black_box_id=int(black_box_id), subject_type="route_deviation",
        subject_id=f"{black_box_id}:{sequence or measured_at.isoformat()}",
        event_type="ROUTE_DEVIATION_ALERT", action="Écart au corridor planifié détecté",
        reaction=message, remarks=assessment,
        source_keys=["ARGOS_GPS_POSITION", "ARGOS_AGENT_RULES"])
    from app.modules.iot.iot_event_service import _concerned_emails
    from app.utils import get_public_base_url, send_email_background
    emails = _concerned_emails(black_box_id)
    if emails:
        threading.Thread(target=send_email_background, args=(emails, f"[ARGOS] {title}", message),
            kwargs={"severity": "warning", "action_url": get_public_base_url(),
                    "action_label": "Consulter le suivi ARGOS"}, daemon=True).start()
    db.session.commit()
    return assessment
