"""Positionnement hybride IoT/AIS et corrélation litiges."""
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import text

IOT_FRESHNESS_THRESHOLD_MIN = 30
SHOCK_ALERT_THRESHOLD_G = 3.0


def _as_utc(dt):
    if not dt:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_hybrid_position(id_boite: str, voyage_id: Optional[int] = None) -> dict:
    from app import db

    now = datetime.now(timezone.utc)
    iot_cutoff = now - timedelta(minutes=IOT_FRESHNESS_THRESHOLD_MIN)

    iot_row = db.session.execute(text("""
        SELECT lat, lon, horodatage, vitesse
        FROM evenement_save
        WHERE id_boite = :bid
          AND lat IS NOT NULL
          AND lon IS NOT NULL
          AND horodatage >= :cutoff
        ORDER BY horodatage DESC
        LIMIT 1
    """), {"bid": id_boite, "cutoff": iot_cutoff}).fetchone()

    if iot_row and iot_row[0] is not None and iot_row[1] is not None:
        ts = _as_utc(iot_row[2])
        age_min = (now - ts).total_seconds() / 60 if ts else 0
        return {
            "lat": float(iot_row[0]),
            "lon": float(iot_row[1]),
            "source": "iot",
            "ts": ts.isoformat() if ts else None,
            "freshness_min": round(age_min, 1),
            "speed_kmh": float(iot_row[3]) if iot_row[3] else 0,
            "status_msg": f"Boîte noire - il y a {round(age_min)} min",
        }

    if voyage_id:
        voyage = db.session.execute(text("""
            SELECT mv.imo_number, v.vessel_name
            FROM maritime_voyage mv
            LEFT JOIN vessel v ON v.imo_number = mv.imo_number
            WHERE mv.id = :vid
        """), {"vid": voyage_id}).fetchone()

        if voyage and voyage[0]:
            ais_row = db.session.execute(text("""
                SELECT lat, lon, ts, speed_knots, heading_deg
                FROM ais_position
                WHERE imo_number = :imo
                ORDER BY ts DESC
                LIMIT 1
            """), {"imo": voyage[0]}).fetchone()
            if ais_row:
                ts = _as_utc(ais_row[2])
                age_min = (now - ts).total_seconds() / 60 if ts else 0
                return {
                    "lat": float(ais_row[0]),
                    "lon": float(ais_row[1]),
                    "source": "ais",
                    "ts": ts.isoformat() if ts else None,
                    "freshness_min": round(age_min, 1),
                    "speed_kmh": round(float(ais_row[3] or 0) * 1.852, 1),
                    "heading_deg": ais_row[4],
                    "vessel_name": voyage[1],
                    "status_msg": f"AIS navire ({voyage[1] or voyage[0]}) - il y a {round(age_min)} min",
                }

    last_known = db.session.execute(text("""
        SELECT lat, lon, horodatage
        FROM evenement_save
        WHERE id_boite = :bid
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        ORDER BY horodatage DESC
        LIMIT 1
    """), {"bid": id_boite}).fetchone()

    if last_known:
        ts = _as_utc(last_known[2])
        age_min = (now - ts).total_seconds() / 60 if ts else 0
        return {
            "lat": float(last_known[0]),
            "lon": float(last_known[1]),
            "source": "last_known",
            "ts": ts.isoformat() if ts else None,
            "freshness_min": round(age_min, 1),
            "status_msg": f"Dernière position connue - il y a {round(age_min / 60, 1)}h",
        }

    return {"lat": None, "lon": None, "source": "unavailable", "status_msg": "Position inconnue"}


def create_geolocalized_litige(
    id_boite: str,
    iot_event_id: int,
    alert_type: str,
    alert_values: dict,
    event_ts: datetime,
    iot_lat: Optional[float],
    iot_lon: Optional[float],
) -> Optional[int]:
    from app import db
    from app.services.maritime_service import get_maritime_adapter

    assignment = db.session.execute(text("""
        SELECT cva.voyage_id, cva.container_number, mv.imo_number, v.vessel_name
        FROM container_voyage_assignment cva
        JOIN maritime_voyage mv ON mv.id = cva.voyage_id
        LEFT JOIN vessel v ON v.imo_number = mv.imo_number
        WHERE cva.id_boite = :bid
          AND mv.voyage_status IN ('loaded', 'at_sea')
        ORDER BY cva.assigned_at DESC
        LIMIT 1
    """), {"bid": id_boite}).fetchone()

    ais_lat, ais_lon, position_source = None, None, "iot"
    vessel_name, nearest_port, distance_nm = None, None, None

    if assignment and assignment[2]:
        vessel_name = assignment[3]
        try:
            adapter = get_maritime_adapter()
            ais_pos = adapter.get_vessel_position_at(assignment[2], event_ts)
            if ais_pos:
                ais_lat = ais_pos["lat"]
                ais_lon = ais_pos["lon"]
                _save_ais_position(assignment[2], ais_pos)
        except Exception as e:
            print(f"[LITIGE] Pas de position AIS disponible : {e}")

    final_lat = iot_lat if iot_lat is not None else ais_lat
    final_lon = iot_lon if iot_lon is not None else ais_lon
    if iot_lat is not None and ais_lat is not None:
        position_source = "hybrid"
    elif ais_lat is not None:
        position_source = "ais"
    else:
        position_source = "iot" if iot_lat is not None else "unavailable"

    if final_lat is not None and final_lon is not None:
        nearest_port, distance_nm = _find_nearest_port(float(final_lat), float(final_lon))

    litige_id = db.session.execute(text("""
        INSERT INTO litige_alerte
            (id_boite, container_number, voyage_id, iot_event_id,
             event_ts, alert_type, alert_values,
             iot_lat, iot_lon, ais_lat, ais_lon,
             position_source, vessel_name,
             nearest_port_locode, distance_to_port_nm)
        VALUES
            (:id_boite, :cont, :voyage_id, :evt_id,
             :event_ts, :alert_type, CAST(:alert_values AS jsonb),
             :iot_lat, :iot_lon, :ais_lat, :ais_lon,
             :pos_source, :vessel,
             :nearest_port, :distance_nm)
        RETURNING id
    """), {
        "id_boite": id_boite,
        "cont": assignment[1] if assignment else None,
        "voyage_id": assignment[0] if assignment else None,
        "evt_id": iot_event_id,
        "event_ts": event_ts,
        "alert_type": alert_type,
        "alert_values": json.dumps(alert_values),
        "iot_lat": iot_lat,
        "iot_lon": iot_lon,
        "ais_lat": ais_lat,
        "ais_lon": ais_lon,
        "pos_source": position_source,
        "vessel": vessel_name,
        "nearest_port": nearest_port,
        "distance_nm": distance_nm,
    }).scalar()
    db.session.commit()

    from app.utils import _sceller_evenement
    _sceller_evenement("LITIGE_CRITIQUE", id_boite, {
        "litige_id": litige_id,
        "alert_type": alert_type,
        "values": alert_values,
        "lat": final_lat,
        "lon": final_lon,
        "source": position_source,
        "vessel": vessel_name,
        "port": nearest_port,
    })
    return litige_id


def _save_ais_position(imo: str, ais_data: dict) -> None:
    from app import db

    try:
        db.session.execute(text("""
            INSERT INTO ais_position
                (imo_number, ts, lat, lon, speed_knots, heading_deg, source)
            VALUES (:imo, :ts, :lat, :lon, :spd, :hdg, :src)
            ON CONFLICT DO NOTHING
        """), {
            "imo": imo,
            "ts": ais_data.get("ts") or datetime.utcnow(),
            "lat": ais_data["lat"],
            "lon": ais_data["lon"],
            "spd": ais_data.get("speed_knots"),
            "hdg": ais_data.get("heading_deg"),
            "src": ais_data.get("source", "ais"),
        })
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[AIS CACHE ERROR] {e}")


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_nm = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return radius_nm * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_nearest_port(lat: float, lon: float) -> Tuple[Optional[str], Optional[float]]:
    from app import db

    ports = db.session.execute(text("SELECT locode, lat, lon FROM port WHERE lat IS NOT NULL AND lon IS NOT NULL")).fetchall()
    if not ports:
        return None, None
    nearest = min(ports, key=lambda p: _haversine_nm(lat, lon, float(p[1]), float(p[2])))
    distance = _haversine_nm(lat, lon, float(nearest[1]), float(nearest[2]))
    return nearest[0], round(distance, 2)
