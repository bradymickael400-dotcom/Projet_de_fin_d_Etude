"""Named geofence entry notifications for configured route polygons."""

import json
import threading

from sqlalchemy import text

from app.extensions import db


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
    if entered:
        db.session.commit()
    return entered
