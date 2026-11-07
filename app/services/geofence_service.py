"""Named geofence entry notifications for configured route polygons."""

import json
import math
import threading

from sqlalchemy import text

from app.extensions import db

EARTH_RADIUS_M = 6_371_000


def distance_meters(latitude_a, longitude_a, latitude_b, longitude_b):
    """Distance haversine entre deux points WGS84, en mètres."""
    lat_a, lat_b = math.radians(float(latitude_a)), math.radians(float(latitude_b))
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(float(longitude_b) - float(longitude_a))
    hav = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(hav)))


def point_in_polygon(latitude, longitude, polygon):
    """Ray-casting for a GeoJSON Polygon ring expressed as [longitude, latitude]."""
    if isinstance(polygon, str):
        polygon = json.loads(polygon)
    if isinstance(polygon, dict):
        if polygon.get("type") != "Polygon":
            return False
        coordinates = polygon.get("coordinates") or []
        ring = coordinates[0] if coordinates else []
    else:
        ring = polygon
    inside = False
    if len(ring) < 4:
        return False
    x, y = float(longitude), float(latitude)
    previous = ring[-1]
    for current in ring:
        x1, y1 = float(previous[0]), float(previous[1])
        x2, y2 = float(current[0]), float(current[1])
        crosses = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-15) + x1)
        if crosses:
            inside = not inside
        previous = current
    return inside


def notify_zone_entries(black_box_id, latitude, longitude, measured_at, device_uid=None, sequence=None):
    """Notify once when a telemetry point crosses into an active named zone."""
    if latitude is None or longitude is None:
        return []
    zones = db.session.execute(text("""
        SELECT zone_id, zone_name, country, mode, polygon, source_key
        FROM brady.argos_geofence_zones WHERE enabled=TRUE
    """)).fetchall()
    previous = db.session.execute(text("""
        SELECT latitude, longitude FROM positions
        WHERE black_box_id=:box AND measured_at < :measured_at
          AND latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY measured_at DESC LIMIT 1
    """), {"box": black_box_id, "measured_at": measured_at}).fetchone()
    previous_point = (float(previous.latitude), float(previous.longitude)) if previous else None
    entered = []
    for zone in zones:
        polygon = zone.polygon if not isinstance(zone.polygon, str) else json.loads(zone.polygon)
        now_inside = point_in_polygon(latitude, longitude, polygon)
        was_inside = bool(previous_point and point_in_polygon(*previous_point, polygon))
        if not now_inside or was_inside:
            continue
        name = str(zone.zone_name)
        message = f"Nouvelle zone géographique : la boîte #{black_box_id} entre dans « {name} » ({zone.country}, {zone.mode})."
        duplicate = db.session.execute(text("""
            SELECT 1 FROM notifications
            WHERE id_boite=:box AND type='GEOFENCE_ENTRY' AND message=:message
              AND horodatage >= NOW() - INTERVAL '24 hours' LIMIT 1
        """), {"box": black_box_id, "message": message}).scalar()
        if duplicate:
            continue
        db.session.execute(text("""
            INSERT INTO notifications(type,message,cible_role,id_boite,device_uid,sequence)
            VALUES('GEOFENCE_ENTRY',:message,'all',:box,:device,:sequence)
        """), {"message": message, "box": black_box_id, "device": device_uid, "sequence": sequence})
        from app.regulatory.history import record_decision
        record_decision(
            identity={"role": "system", "user_id": "geofence_service"},
            black_box_id=int(black_box_id), subject_type="geofence", subject_id=f"{zone.zone_id}:{sequence}",
            event_type="GEOFENCE_ENTRY", action=f"Entrée détectée dans la zone {name}",
            reaction=message,
            remarks={"zone_id": zone.zone_id, "country": zone.country, "mode": zone.mode,
                     "latitude": float(latitude), "longitude": float(longitude),
                     "measured_at": measured_at.isoformat(), "source_key": zone.source_key},
            source_keys=["ARGOS_GEOFENCE_ZONES", "ARGOS_GPS_POSITION"],
        )
        entered.append(name)
        from app.modules.iot.iot_event_service import _concerned_emails
        from app.utils import get_public_base_url, send_email_background
        emails = _concerned_emails(black_box_id)
        if emails:
            threading.Thread(
                target=send_email_background,
                args=(emails, f"[ARGOS] Entrée dans une zone — boîte #{black_box_id}", message),
                kwargs={"severity": "info", "action_url": get_public_base_url(),
                        "action_label": "Ouvrir le suivi ARGOS"}, daemon=True,
            ).start()
    # Les points fournis ne sont pas des limites officielles; le rayon est
    # donc une zone de proximité indicative, jamais une entrée confirmée.
    ports = db.session.execute(text("""
        SELECT port_id, port_name, country, latitude, longitude,
               proximity_radius_m, coordinate_precision, verification_status
        FROM brady.argos_port_locations WHERE enabled=TRUE
    """)).fetchall()
    for port in ports:
        radius = float(port.proximity_radius_m or 3000)
        current_distance = distance_meters(latitude, longitude, port.latitude, port.longitude)
        previous_distance = (
            distance_meters(*previous_point, port.latitude, port.longitude)
            if previous_point else None
        )
        if current_distance > radius or (previous_distance is not None and previous_distance <= radius):
            continue
        name = str(port.port_name)
        message = (
            f"Proximité portuaire indicative détectée pour la boîte #{black_box_id} : "
            f"position à moins de {int(radius)} m du point de référence « {name} » ({port.country}); "
            f"distance GPS estimée {int(round(current_distance))} m. "
            "Ce point ne représente pas le périmètre officiel du port."
        )
        duplicate = db.session.execute(text("""
            SELECT 1 FROM notifications
            WHERE id_boite=:box AND type='PORT_PROXIMITY_DETECTED' AND message=:message
              AND horodatage >= NOW() - INTERVAL '24 hours' LIMIT 1
        """), {"box": black_box_id, "message": message}).scalar()
        if duplicate:
            continue
        db.session.execute(text("""
            INSERT INTO notifications(type,message,cible_role,id_boite,device_uid,sequence)
            VALUES('PORT_PROXIMITY_DETECTED',:message,'all',:box,:device,:sequence)
        """), {"message": message, "box": black_box_id, "device": device_uid, "sequence": sequence})
        from app.regulatory.history import record_decision
        record_decision(
            identity={"role": "system", "user_id": "port_geofence_service"},
            black_box_id=int(black_box_id), subject_type="port_proximity",
            subject_id=f"{port.port_id}:{sequence}", event_type="PORT_PROXIMITY_DETECTED",
            action=f"Proximité du point de référence portuaire {name} détectée",
            reaction=message,
            remarks={"port_id": port.port_id, "country": port.country,
                "distance_m": round(current_distance, 1), "radius_m": radius,
                "coordinate_precision": port.coordinate_precision,
                "verification_status": port.verification_status,
                "measured_at": measured_at.isoformat()},
            source_keys=["ARGOS_PORT_LOCATIONS", "ARGOS_GPS_POSITION"],
            applicability_status="PROVISIONAL_GEOFENCE",
        )
        entered.append(name)
        from app.modules.iot.iot_event_service import _concerned_emails
        from app.utils import get_public_base_url, send_email_background
        emails = _concerned_emails(black_box_id)
        if emails:
            threading.Thread(
                target=send_email_background,
                args=(emails, f"[ARGOS] Proximité portuaire — boîte #{black_box_id}", message),
                kwargs={"severity": "info", "action_url": get_public_base_url(),
                    "action_label": "Ouvrir le suivi ARGOS"}, daemon=True,
            ).start()
    if entered:
        db.session.commit()
    return entered
