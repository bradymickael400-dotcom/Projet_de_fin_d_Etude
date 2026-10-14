
"""Routes du tableau de bord et des statistiques ARGOS.

Ce module agrège les données métier pour alimenter les graphiques,
les indicateurs et les vues de synthèse visibles dans l’interface.
"""

import json
import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, current_app
from sqlalchemy import text
from app import db, limiter
from app.utils import *
from app.utils import get_boite_for_client
from google.api_core.client_options import ClientOptions
from google.ai.generativelanguage import GenerativeServiceClient, GenerateContentRequest, Content, Part
from app.security import current_identity, roles_required

dash_bp = Blueprint("dashboard", __name__)

MONTH_NAMES = {
    '01': 'Jan', '02': 'Fév', '03': 'Mar', '04': 'Avr',
    '05': 'Mai', '06': 'Juin', '07': 'Juil', '08': 'Août',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Déc'
}

STATS_PERIODS = {
    "5h": ("5 hours", "hour", "DD/MM HH24:MI"),
    "24h": ("24 hours", "hour", "DD/MM HH24:MI"),
    "7d": ("7 days", "day", "DD/MM"),
    "30d": ("30 days", "day", "DD/MM"),
    "3m": ("3 months", "week", "DD/MM"),
    "all": (None, "month", "MM/YYYY"),
}


def _stats_period(value):
    """Normalise la période pour ne jamais interpoler une valeur HTTP en SQL."""
    period = str(value or "7d").strip().lower()
    return period if period in STATS_PERIODS else "7d"


def _number(value, digits=None):
    if value is None:
        return None
    result = float(value)
    return round(result, digits) if digits is not None else result


def _alerts(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except (TypeError, ValueError):
        return [str(value)]


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _freshness(timestamp):
    """Age de la mesure et état en ligne, sans rendre les anciennes données nulles."""
    try:
        parsed = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(
            str(timestamp).replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        seconds = max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))
        return seconds, seconds <= int(current_app.config.get("IOT_ONLINE_WINDOW_SECONDS", 120))
    except (TypeError, ValueError):
        return None, False


def _visible_boites_for(role, user_id):
    """None = accès global superadmin, [] = aucun accès, liste = boîtes autorisées."""
    if role in (None, "", "superadmin"):
        return None
    if not user_id:
        return []
    if role == "owner":
        return get_boites_for_owner(user_id)
    if role == "company":
        return get_boites_for_agency(user_id)
    if role == "client":
        return get_boite_for_client(user_id)
    if role == "driver":
        return get_boite_for_driver(user_id)
    if role == "port_authority":
        return get_boites_for_port_authority(user_id)
    return []


def _append_boites_filter(parts, params, boites, column="id_boite", prefix="bf"):
    if boites is None:
        return True
    if not boites:
        return False
    placeholders = ",".join([f":{prefix}{i}" for i in range(len(boites))])
    parts.append(f"{column} IN ({placeholders})")
    params.update({f"{prefix}{i}": v for i, v in enumerate(boites)})
    return True


def _monthly_subscriptions_chart(boites=None):
    parts = ["LOWER(COALESCE(status,'')) = 'actif'"]
    params = {}
    if not _append_boites_filter(parts, params, boites, "id_boite", "ab"):
        return {"labels": [], "data": []}

    rows = db.session.execute(text(f"""
        WITH monthly AS (
            SELECT TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS mois_annee,
                   COUNT(*) AS total
            FROM abonner
            WHERE {" AND ".join(parts)}
            GROUP BY DATE_TRUNC('month', created_at)
        )
        SELECT mois_annee, total
        FROM monthly
        ORDER BY mois_annee
    """), params).fetchall()

    return {
        "labels": [f"{MONTH_NAMES.get(r[0].split('-')[1], r[0].split('-')[1])} {r[0].split('-')[0]}" for r in rows],
        "data": [int(r[1] or 0) for r in rows],
    }


def _active_subscriptions_count(boites=None):
    parts = ["LOWER(COALESCE(status,'')) = 'actif'"]
    params = {}
    if not _append_boites_filter(parts, params, boites, "id_boite", "asb"):
        return 0
    return db.session.execute(text(f"""
        SELECT COUNT(*) FROM abonner
        WHERE {" AND ".join(parts)}
    """), params).scalar() or 0


def _alerts_count_from_notifications(parts, params):
    wh = ("WHERE " + " AND ".join(parts)) if parts else ""
    return db.session.execute(text(f"""
        SELECT COUNT(*)
        FROM notifications {wh}
    """), params).scalar() or 0


def _alerts_dist_from_sources(event_wh, event_params, notif_wh="", notif_params=None):
    notif_params = notif_params or {}
    event_dist = db.session.execute(text(f"""
        SELECT SUM(CASE WHEN COALESCE(notif,'') ILIKE '%choc%'    THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(notif,'') ILIKE '%temp%'    THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(notif,'') ILIKE '%humid%'   THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(notif,'') ILIKE '%vitesse%' THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(notif,'') ILIKE '%press%'   THEN 1 ELSE 0 END)
        FROM evenement_save {event_wh}
    """), event_params).fetchone()

    # IOT_ALERT est la notification du même événement déjà présent dans
    # evenement_save. On ne compte ici que les alertes venant d'une autre
    # source afin de ne pas doubler la distribution.
    notification_scope = (
        f"{notif_wh} AND COALESCE(type,'') <> 'IOT_ALERT'"
        if notif_wh else "WHERE COALESCE(type,'') <> 'IOT_ALERT'"
    )
    notif_dist = db.session.execute(text(f"""
        SELECT SUM(CASE WHEN COALESCE(message,'') ILIKE '%choc%'    THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(message,'') ILIKE '%temp%'    THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(message,'') ILIKE '%humid%'   THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(message,'') ILIKE '%vitesse%' THEN 1 ELSE 0 END),
               SUM(CASE WHEN COALESCE(message,'') ILIKE '%press%'   THEN 1 ELSE 0 END)
        FROM notifications {notification_scope}
    """), notif_params).fetchone()

    return [int((event_dist[i] or 0) + (notif_dist[i] or 0)) for i in range(5)]



# ═══════════════════════════════════════════════════════════
#  HOME
# ═══════════════════════════════════════════════════════════

@dash_bp.route("/")
def home():
    try:
        init_blockchain()
    except Exception:
        pass
    return render_template("index.html")
# ═══════════════════════════════════════════════════════════
#  STATISTIQUES — avec restriction rôle
# ═══════════════════════════════════════════════════════════

@dash_bp.route("/api/stats", methods=["GET"])
def get_dashboard_stats():
    try:
        period = _stats_period(request.args.get("period", "7d"))
        boite = str(request.args.get("boite") or "").strip() or None
        role, user_id = get_caller_identity()
        boites_filter = _visible_boites_for(role, user_id)
        if boite and boites_filter is not None and boite not in {
            str(value) for value in boites_filter
        }:
            return jsonify({"status": "error", "message": "Boîte hors périmètre"}), 403

        sql_interval, bucket, bucket_format = STATS_PERIODS[period]
        parts, params = [], {}
        notif_parts, notif_params = [], {}
        if sql_interval:
            parts.append(
                f"COALESCE(horodatage, created_at) >= NOW() - INTERVAL '{sql_interval}'"
            )
            notif_parts.append(f"horodatage >= NOW() - INTERVAL '{sql_interval}'")
        if boite:
            parts.append("id_boite=:boite")
            params["boite"] = boite
            notif_parts.append("id_boite=:boite")
            notif_params["boite"] = boite
        if not _append_boites_filter(parts, params, boites_filter, "id_boite", "bff"):
            return jsonify({"status": "success",
                "kpi": {"avg_temp":0,"avg_hum":0,"avg_press":0,"avg_speed":0,
                        "total_events":0,"total_shocks":0,"total_alertes":0,"fiabilite":100,
                        "total_abonnes":0,"total_notifications":0,"devices":0,
                        "gps_coverage":0,"identity_coverage":0},
                "ranges": {}, "devices": [],
                "charts": {"labels":[],"temp":[],"hum":[],"press":[],"speed":[],"shocks":[],
                           "acceleration_x":[],"acceleration_y":[],"acceleration_z":[],
                           "battery":[],"gps_lat":[],"gps_lon":[],"samples":[],"alerts":[],
                           "alerts_dist":[0,0,0,0,0], "abonnements": {"labels": [], "data": []}}
            })
        _append_boites_filter(
            notif_parts, notif_params, boites_filter, "id_boite", "nbff"
        )

        wh = ("WHERE " + " AND ".join(parts)) if parts else ""
        notif_wh = ("WHERE " + " AND ".join(notif_parts)) if notif_parts else ""

        kpi = db.session.execute(text(f"""
            SELECT COALESCE(AVG(temperature),0), COALESCE(AVG(humidite),0),
                   COALESCE(AVG(pressions),0),  COALESCE(AVG(vitesse),0),
                   COUNT(*),
                   SUM(CASE WHEN chocs > 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                             AND TRIM(notif) != '[]' THEN 1 ELSE 0 END),
                   COALESCE(AVG(chocs),0), COALESCE(MAX(chocs),0),
                   COALESCE(AVG(acceleration_x),0),
                   COALESCE(AVG(acceleration_y),0),
                   COALESCE(AVG(acceleration_z),0),
                   COALESCE(MAX(CASE
                       WHEN acceleration_x IS NOT NULL OR acceleration_y IS NOT NULL
                            OR acceleration_z IS NOT NULL
                       THEN SQRT(POWER(COALESCE(acceleration_x,0),2)
                               + POWER(COALESCE(acceleration_y,0),2)
                               + POWER(COALESCE(acceleration_z,0),2))
                   END),0),
                   COALESCE(AVG(battery_level),0),
                   MIN(temperature), MAX(temperature),
                   MIN(humidite), MAX(humidite),
                   MIN(pressions), MAX(pressions), MAX(vitesse),
                   SUM(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
                                  AND NOT (lat=0 AND lon=0) THEN 1 ELSE 0 END),
                   COUNT(DISTINCT device_uid),
                   MIN(COALESCE(horodatage,created_at)),
                   MAX(COALESCE(horodatage,created_at)),
                   COUNT(device_uid), COUNT(sequence)
            FROM evenement_save {wh}
        """), params).fetchone()

        notification_alerts = _alerts_count_from_notifications(notif_parts, notif_params)
        # Une notification IOT_ALERT est la diffusion d'un événement déjà compté.
        # Elle reste exposée séparément pour ne pas doubler le KPI des anomalies.
        total_alertes = int(kpi[6] or 0) # type: ignore

        fiabilite = 100.0
        total_events = int(kpi[4] or 0) # type: ignore
        if total_events > 0:
            fiabilite = max(0, round(100 - (total_alertes / total_events * 100), 1))

        ts = db.session.execute(text(f"""
            SELECT TO_CHAR(DATE_TRUNC('{bucket}',COALESCE(horodatage,created_at)),'{bucket_format}'),
                   COALESCE(AVG(temperature),0), COALESCE(AVG(humidite),0),
                   COALESCE(AVG(pressions),0),   COALESCE(AVG(vitesse),0),
                   COALESCE(MAX(chocs),0),
                   COALESCE(AVG(acceleration_x),0),
                   COALESCE(AVG(acceleration_y),0),
                   COALESCE(AVG(acceleration_z),0),
                   COALESCE(AVG(battery_level),0),
                   AVG(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
                                  AND NOT (lat=0 AND lon=0) THEN lat END),
                   AVG(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
                                  AND NOT (lat=0 AND lon=0) THEN lon END),
                   COUNT(*),
                   SUM(CASE WHEN NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                                  AND TRIM(notif) != '[]' THEN 1 ELSE 0 END)
            FROM evenement_save {wh}
            GROUP BY DATE_TRUNC('{bucket}',COALESCE(horodatage,created_at))
            ORDER BY DATE_TRUNC('{bucket}',COALESCE(horodatage,created_at))
        """), params).fetchall()

        dist = _alerts_dist_from_sources(wh, params, notif_wh, notif_params)
        by_device = db.session.execute(text(f"""
            SELECT device_uid, id_boite, COUNT(*) AS samples,
                   MIN(COALESCE(horodatage,created_at)) AS first_seen,
                   MAX(COALESCE(horodatage,created_at)) AS last_seen,
                   COALESCE(AVG(temperature),0) AS avg_temperature,
                   COALESCE(AVG(humidite),0) AS avg_humidity,
                   COALESCE(AVG(pressions),0) AS avg_pressure,
                   COALESCE(MAX(chocs),0) AS max_shock,
                   COALESCE(AVG(vitesse),0) AS avg_speed,
                   COALESCE(MAX(sequence),0) AS last_sequence,
                   SUM(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
                                  AND NOT (lat=0 AND lon=0) THEN 1 ELSE 0 END) AS gps_samples
            FROM evenement_save {wh}
            GROUP BY device_uid,id_boite
            ORDER BY MAX(COALESCE(horodatage,created_at)) DESC
            LIMIT 100
        """), params).fetchall()

        subscription_scope = [boite] if boite else boites_filter
        event_count = max(1, total_events)

        return jsonify({
            "status": "success",
            "period": period,
            "sort": {"field": "timestamp", "direction": "asc"},
            "kpi": {
                "avg_temp":      round(float(kpi[0]), 1), # type: ignore
                "avg_hum":       round(float(kpi[1]), 1), # type: ignore
                "avg_press":     round(float(kpi[2]), 1), # type: ignore
                "avg_speed":     round(float(kpi[3]), 1), # type: ignore
                "avg_shock":     round(float(kpi[7]), 3), # type: ignore
                "max_shock":     round(float(kpi[8]), 3), # type: ignore
                "avg_acceleration_x": round(float(kpi[9]), 3), # type: ignore
                "avg_acceleration_y": round(float(kpi[10]), 3), # type: ignore
                "avg_acceleration_z": round(float(kpi[11]), 3), # type: ignore
                "max_acceleration_magnitude": round(float(kpi[12]), 3), # type: ignore
                "avg_battery":   round(float(kpi[13]), 1), # type: ignore
                "total_events":  total_events,
                "total_shocks":  int(kpi[5] or 0), # type: ignore
                "total_alertes": total_alertes,
                "total_notifications": int(notification_alerts or 0),
                "fiabilite":     fiabilite,
                "total_abonnes": _active_subscriptions_count(subscription_scope),
                "devices":       int(kpi[22] or 0), # type: ignore
                "gps_coverage":   round(int(kpi[21] or 0) / event_count * 100, 1), # type: ignore
                "identity_coverage": round(int(kpi[25] or 0) / event_count * 100, 1), # type: ignore
                "sequence_coverage": round(int(kpi[26] or 0) / event_count * 100, 1), # type: ignore
            },
            "ranges": {
                "temperature": {"min": _number(kpi[14], 2), "max": _number(kpi[15], 2)}, # type: ignore
                "humidity": {"min": _number(kpi[16], 2), "max": _number(kpi[17], 2)}, # type: ignore
                "pressure": {"min": _number(kpi[18], 2), "max": _number(kpi[19], 2)}, # type: ignore
                "speed": {"min": 0, "max": _number(kpi[20], 2)}, # type: ignore
                "shock": {"min": 0, "max": _number(kpi[8], 3)}, # type: ignore
                "first_at": _iso(kpi[23]), # type: ignore
                "last_at": _iso(kpi[24]), # type: ignore
            },
            "devices": [{
                "deviceUid": row[0],
                "blackBoxId": row[1],
                "samples": int(row[2] or 0),
                "firstAt": _iso(row[3]),
                "lastAt": _iso(row[4]),
                "avgTemperature": _number(row[5], 2),
                "avgHumidity": _number(row[6], 2),
                "avgPressure": _number(row[7], 2),
                "maxShock": _number(row[8], 3),
                "avgSpeed": _number(row[9], 2),
                "lastSequence": int(row[10] or 0),
                "gpsCoverage": round(int(row[11] or 0) / max(1, int(row[2] or 0)) * 100, 1),
            } for row in by_device],
            "charts": {
                "labels":      [r[0] for r in ts],
                "temp":        [round(float(r[1]), 1) for r in ts],
                "hum":         [round(float(r[2]), 1) for r in ts],
                "press":       [round(float(r[3]), 1) for r in ts],
                "speed":       [round(float(r[4]), 1) for r in ts],
                "shocks":      [round(float(r[5]), 1) for r in ts],
                "acceleration_x": [round(float(r[6]), 3) for r in ts],
                "acceleration_y": [round(float(r[7]), 3) for r in ts],
                "acceleration_z": [round(float(r[8]), 3) for r in ts],
                "battery":     [round(float(r[9]), 1) for r in ts],
                "gps_lat":     [_number(r[10], 6) for r in ts],
                "gps_lon":     [_number(r[11], 6) for r in ts],
                "samples":     [int(r[12] or 0) for r in ts],
                "alerts":      [int(r[13] or 0) for r in ts],
                "alerts_dist": dist,
                "abonnements":  _monthly_subscriptions_chart(subscription_scope),
            }
        }), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _cached_live_document(value):
    """Stabilise le contrat JSON Redis utilisé par l'interface temps réel."""
    document = dict(value or {})
    timestamp = document.get("timestamp")
    freshness_seconds, online = _freshness(timestamp)
    document["position"] = dict(document.get("position") or {})
    document["sensors"] = dict(document.get("sensors") or {})
    document["modes"] = dict(document.get("modes") or {})
    document["quality"] = dict(document.get("quality") or {})
    document["alerts"] = _alerts(document.get("alerts"))
    document["timestamp"] = _iso(timestamp)
    document["date"] = str(timestamp or "")[:10] or None
    document["time"] = str(timestamp or "")[11:19] or None
    document["freshnessSeconds"] = freshness_seconds
    document["online"] = online
    return document


def _postgres_live_document(row):
    values = dict(row._mapping)
    timestamp = values.get("measured_at")
    freshness_seconds, online = _freshness(timestamp)
    modes = values.get("modes") or {}
    if isinstance(modes, str):
        try:
            modes = json.loads(modes)
        except (TypeError, ValueError):
            modes = {}
    quality = values.get("quality") or {}
    if isinstance(quality, str):
        try:
            quality = json.loads(quality)
        except (TypeError, ValueError):
            quality = {}
    return {
        "messageId": values.get("message_id"),
        "deviceUid": values.get("device_uid"),
        "sequence": values.get("sequence"),
        "blackBoxId": values.get("black_box_id"),
        "containerId": values.get("container_id"),
        "timestamp": _iso(timestamp),
        "date": timestamp.strftime("%Y-%m-%d") if timestamp else None,
        "time": timestamp.strftime("%H:%M:%S") if timestamp else None,
        "freshnessSeconds": freshness_seconds,
        "online": online,
        "position": {
            "latitude": _number(values.get("latitude"), 7) or 0,
            "longitude": _number(values.get("longitude"), 7) or 0,
            "accuracy": _number(values.get("accuracy"), 2) or 0,
            "speed": _number(values.get("speed"), 2) or 0,
            "heading": _number(values.get("position_heading"), 2) or 0,
            "source": values.get("position_source") or "ESP32",
        },
        "sensors": {
            "temperature": _number(values.get("temperature"), 2),
            "humidity": _number(values.get("humidity"), 2),
            "pressure": _number(values.get("pressure"), 2),
            "shock": _number(values.get("shock"), 3),
            "accelerationX": _number(values.get("acceleration_x"), 3),
            "accelerationY": _number(values.get("acceleration_y"), 3),
            "accelerationZ": _number(values.get("acceleration_z"), 3),
            "batteryLevel": _number(values.get("battery_level"), 1),
            "lightLevel": _number(values.get("light_level"), 2),
            "soundLevel": _number(values.get("sound_level"), 2),
            "distanceCm": _number(values.get("distance_cm"), 2),
            "flameDetected": bool(values.get("flame_detected")),
            "doorOpen": bool(values.get("door_open")),
            "securityAlarm": bool(values.get("security_alarm")),
        },
        "modes": modes if isinstance(modes, dict) else {},
        "quality": quality if isinstance(quality, dict) else {},
        "alerts": _alerts(values.get("notif")),
    }


def _latest_postgres_telemetry(boites, device_uid=None, after_sequence=None, limit=100):
    where, params = [], {"limit": max(1, min(int(limit or 100), 500))}
    if not _append_boites_filter(where, params, boites, "sr.black_box_id", "live_box"):
        return []
    if device_uid:
        where.append("sd.device_uid=:device_uid")
        params["device_uid"] = device_uid
    if after_sequence is not None:
        where.append("sr.sequence>:after_sequence")
        params["after_sequence"] = after_sequence
    wh = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.session.execute(text(f"""
        WITH latest AS (
            SELECT sr.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY sr.black_box_id
                       ORDER BY sr.measured_at DESC,sr.id DESC
                   ) AS row_number
            FROM sensor_readings sr
            LEFT JOIN iot_devices sd ON sd.id=sr.device_id
            {wh}
        )
        SELECT latest.raw_message_id,latest.device_id,latest.black_box_id,
               COALESCE(latest.container_id,b.id_conteneurs) AS container_id,
               latest.sequence,latest.temperature,latest.humidity,latest.shock,
               latest.pressure,latest.flame_detected,latest.door_open,
               latest.battery_level,latest.light_level,latest.sound_level,
               latest.distance_cm,latest.acceleration_x,latest.acceleration_y,
               latest.acceleration_z,latest.security_alarm,latest.modes,latest.quality,
               latest.measured_at,d.device_uid,CAST(raw.message_id AS text) AS message_id,
               COALESCE(pos.latitude,event.lat,0) AS latitude,
               COALESCE(pos.longitude,event.lon,0) AS longitude,
               COALESCE(pos.accuracy,0) AS accuracy,
               COALESCE(pos.speed,event.vitesse,0) AS speed,
               COALESCE(pos.heading,event.heading,0) AS position_heading,
               COALESCE(pos.source,'ESP32') AS position_source,event.notif
        FROM latest
        LEFT JOIN iot_devices d ON d.id=latest.device_id
        LEFT JOIN iot_raw_messages raw ON raw.id=latest.raw_message_id
        LEFT JOIN boite_noir b ON b.id_boite=latest.black_box_id
        LEFT JOIN positions pos ON pos.raw_message_id=latest.raw_message_id
        LEFT JOIN LATERAL (
            SELECT e.lat,e.lon,e.vitesse,e.heading,e.notif
            FROM evenement_save e
            WHERE e.id_boite=latest.black_box_id
              AND (e.sequence=latest.sequence OR latest.sequence IS NULL)
              AND (e.device_uid=d.device_uid OR e.device_uid IS NULL)
            ORDER BY COALESCE(e.horodatage,e.created_at) DESC
            LIMIT 1
        ) event ON TRUE
        WHERE latest.row_number=1
        ORDER BY latest.measured_at DESC
        LIMIT :limit
    """), params).fetchall()
    return [_postgres_live_document(row) for row in rows]


@dash_bp.route("/api/stats/live", methods=["GET"])
def get_live_telemetry_stats():
    """Dernière mesure par boîte : Redis d'abord, PostgreSQL en repli."""
    role, user_id = get_caller_identity()
    visible = _visible_boites_for(role, user_id)
    requested_box = str(request.args.get("boite") or "").strip() or None
    device_uid = str(request.args.get("device_uid") or "").strip() or None
    direction = str(request.args.get("sort") or "desc").lower()
    direction = "asc" if direction == "asc" else "desc"
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 500))
    except (TypeError, ValueError):
        limit = 100
    try:
        after_sequence = request.args.get("after_sequence")
        after_sequence = int(after_sequence) if after_sequence not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "after_sequence invalide"}), 400

    if requested_box and visible is not None and requested_box not in {
        str(value) for value in visible
    }:
        return jsonify({"status": "error", "message": "Boîte hors périmètre"}), 403
    scoped_boxes = [requested_box] if requested_box else visible
    if scoped_boxes == []:
        return jsonify({
            "status": "success", "source": "none", "count": 0,
            "sort": direction, "latest": None, "telemetry": [],
        })

    from app.modules.iot.telemetry_cache import read_latest_by_boxes

    cached = read_latest_by_boxes(scoped_boxes, limit=limit)
    documents = []
    for value in cached:
        if requested_box and str(value.get("blackBoxId")) != requested_box:
            continue
        if device_uid and str(value.get("deviceUid") or "") != device_uid:
            continue
        if after_sequence is not None and int(value.get("sequence") or -1) <= after_sequence:
            continue
        documents.append(_cached_live_document(value))

    source = "redis"
    # Si la boîte n'a pas encore de clé Redis (redémarrage/TTL), la vue reste
    # immédiatement utilisable grâce à la dernière mesure persistée.
    if not cached:
        documents = _latest_postgres_telemetry(
            scoped_boxes, device_uid=device_uid,
            after_sequence=after_sequence, limit=limit,
        )
        source = "postgresql"

    documents.sort(
        key=lambda item: str(item.get("timestamp") or ""),
        reverse=direction == "desc",
    )
    documents = documents[:limit]
    response = jsonify({
        "status": "success",
        "source": source,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(documents),
        "sort": direction,
        "latest": documents[0] if documents else None,
        "telemetry": documents,
    })
    response.headers["Cache-Control"] = "no-store"
    return response, 200

# ═══════════════════════════════════════════════════════════
#  DASHBOARDS
# ═══════════════════════════════════════════════════════════
@dash_bp.route("/api/dashboard/superadmin", methods=["GET"])
@roles_required("superadmin")
def get_sa_dashboard():
    try:
        tot_ent    = db.session.execute(text("SELECT COUNT(*) FROM proprietaire_conteneur")).scalar() or 0
        tot_abs    = _active_subscriptions_count()
        event_alerts = db.session.execute(text(
            "SELECT COUNT(*) FROM evenement_save WHERE NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL AND TRIM(notif) != '[]'"
        )).scalar() or 0
        notification_alerts = db.session.execute(text("SELECT COUNT(*) FROM notifications")).scalar() or 0
        tot_alerts = int(event_alerts or 0) + int(notification_alerts or 0)
        tot_clients= db.session.execute(text("SELECT COUNT(*) FROM client")).scalar() or 0
        tot_boites = db.session.execute(text("SELECT COUNT(*) FROM boite_noir")).scalar() or 0

        recent = db.session.execute(text("""
            SELECT * FROM (
                SELECT horodatage, id_boite, notif AS details, log_action AS message,
                       temperature, chocs, 'event' AS source
                FROM evenement_save
                WHERE NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                  AND TRIM(notif) != '[]'
                UNION ALL
                SELECT horodatage, id_boite, NULL AS details, message,
                       NULL::double precision AS temperature,
                       NULL::double precision AS chocs,
                       'notification' AS source
                FROM notifications
            ) alerts
            ORDER BY horodatage DESC LIMIT 10
        """)).fetchall()
        alertes_recentes = []
        for r in recent:
            try: msgs = json.loads(r[2]) if r[2] else []
            except: msgs = []
            alertes_recentes.append({
                "time": r[0].strftime("%d/%m %H:%M") if r[0] else "?",
                "boite": r[1], "message": r[3] or "Alerte",
                "details": msgs[:2],
                "temp": float(r[4]) if r[4] else None,
                "chocs": float(r[5]) if r[5] else None,
            })

        crit = db.session.execute(text("""
            SELECT id_boite, COUNT(*) c
            FROM (
                SELECT id_boite
                FROM evenement_save
                WHERE NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                  AND TRIM(notif) != '[]'
                UNION ALL
                SELECT id_boite
                FROM notifications
                WHERE id_boite IS NOT NULL
            ) alerts
            GROUP BY id_boite ORDER BY c DESC LIMIT 5
        """)).fetchall()

        top_ent = db.session.execute(text("""
            SELECT p.nom_agence, p.nbr_boite, p.addresse_mail,
                   p.lieu_residence, p.lat, p.lon,
                   COUNT(DISTINCT a.numero_a) AS nbcl
            FROM proprietaire_conteneur p
            LEFT JOIN boite_noir b ON b.id_proprietaire = p.id
            LEFT JOIN abonner a ON a.id_boite = b.id_boite AND LOWER(COALESCE(a.status,'')) = 'actif'
            GROUP BY p.id,p.nom_agence,p.nbr_boite,p.addresse_mail,
                     p.lieu_residence,p.lat,p.lon
            ORDER BY p.id DESC LIMIT 5
        """)).fetchall()

        dist = _alerts_dist_from_sources("", {}, "", {})

        abonnements_chart = _monthly_subscriptions_chart()

        # Modifiez la clé "charts" dans votre return jsonify final :
        return jsonify({
            "status": "success",
            "kpi": {"entreprises": tot_ent, "abonnes": tot_abs, "alertes": tot_alerts,
                    "clients": tot_clients, "boites": tot_boites},
            "alertes_recentes": alertes_recentes,
            "conteneurs_critiques": [{"id": r[0], "count": r[1]} for r in crit],
            "top_entreprises": [{
                "nom": r[0], "boites": r[1], "contact": r[2],
                "location": r[3], "lat": float(r[4]) if r[4] else None,
                "lon": float(r[5]) if r[5] else None, "clients": r[6], "statut": "active"
            } for r in top_ent],
            "charts": {
                "alerts_dist": dist,
                "abonnements": abonnements_chart
            },
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@dash_bp.route("/api/dashboard/owner", methods=["GET"])
@roles_required("superadmin", "owner")
def get_owner_dashboard():
    try:
        identity = current_identity()
        owner_id = request.args.get("owner_id") if identity.get("role") == "superadmin" else identity.get("user_id")
        boites_ids = get_boites_for_owner(owner_id)

        boites = db.session.execute(text("""
            SELECT b.id_boite, b.type_boite, c.id_conteneurs, c.type_conteneurs, c.status
            FROM proprietaire_conteneur p
            JOIN boite_noir b ON b.id_proprietaire = p.id
            JOIN conteneurs c ON c.id_conteneurs = b.id_conteneurs
            WHERE p.id = :oid
        """), {"oid": owner_id}).fetchall()

        boites_data = []
        for b in boites:
            last = db.session.execute(text("""
                SELECT temperature,humidite,pressions,lat,lon,vitesse,chocs,notif
                FROM evenement_save WHERE id_boite=:bid ORDER BY horodatage DESC LIMIT 1
            """), {"bid": b[0]}).fetchone()
            alerts = []
            if last and last[7]:
                try: alerts = json.loads(last[7])
                except: pass
            status = b[4] or "off"
            if last:
                status = "danger" if len(alerts) >= 2 else ("warning" if alerts else "ok")
            boites_data.append({
                "id_boite": b[0], "type_boite": b[1], "id_conteneur": b[2],
                "type_conteneur": b[3], "status": status,
                "temp": float(last[0]) if last and last[0] else None,
                "humidity": float(last[1]) if last and last[1] else None,
                "lat": float(last[3]) if last and last[3] else None,
                "lon": float(last[4]) if last and last[4] else None,
                "speed": float(last[5]) if last and last[5] else 0,
                "shock": float(last[6]) if last and last[6] else 0,
                "alerts": alerts,
            })

        kpi_row = db.session.execute(text("""
            SELECT COALESCE(AVG(temperature),0), COUNT(*),
                SUM(CASE WHEN NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                          AND TRIM(notif) != '[]' THEN 1 ELSE 0 END)
            FROM evenement_save e
            JOIN boite_noir b ON b.id_boite = e.id_boite
            JOIN proprietaire_conteneur p ON p.id = b.id_proprietaire -- CORRECTION ICI
            WHERE p.id = :oid
        """), {"oid": owner_id}).fetchone()
        owner_notifications = 0
        if boites_ids:
            placeholders = ",".join([f":ob{i}" for i in range(len(boites_ids))])
            owner_notifications = db.session.execute(text(f"""
                SELECT COUNT(*) FROM notifications
                WHERE id_boite IN ({placeholders})
            """), {f"ob{i}": v for i, v in enumerate(boites_ids)}).scalar() or 0

        return jsonify({
            "status": "success",
            "boites": boites_data,
            "kpi": {
                "avg_temp": round(float(kpi_row[0]), 1) if kpi_row else 0,
                "total_events": int(kpi_row[1]) if kpi_row else 0,
                "total_alertes": (int(kpi_row[2] or 0) if kpi_row else 0) + int(owner_notifications or 0),
                "total_notifications": int(owner_notifications or 0),
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@dash_bp.route('/api/ai/chat', methods=['POST'])
@limiter.limit("20/hour")
def ai_chat():
    try:
        data = request.get_json() or {}
        message = (data.get('message') or '').strip()
        system_prompt = (
            "Tu es ReportAI, assistant ARGOS. Produis des rapports factuels en francais, "
            "n'invente aucune donnee et signale explicitement toute information manquante."
        )
        context_data = data.get('contextData') or ''

        if not message:
            return jsonify({"error": "Le message est requis."}), 400

        # Récupérer la clé API depuis la config Flask ou l'environnement
        api_key = current_app.config.get('API_KEY') or os.environ.get('API_KEY')
        if not api_key:
            return jsonify({"error": "Assistant IA non configuré côté serveur. Veuillez définir API_KEY dans .env"}), 500

        client = GenerativeServiceClient(client_options=ClientOptions(api_key=api_key))
        final_prompt = f"DONNÉES ACTUELLES DES CONTENEURS :\n{context_data}\n\nDEMANDE DE L'UTILISATEUR :\n{message}"

        gemini_model = current_app.config.get('GEMINI_MODEL') or os.environ.get('GEMINI_MODEL') or 'models/gemini-2.5-flash'
        request_payload = GenerateContentRequest(
            model=gemini_model,
            system_instruction=Content(
                role='system',
                parts=[Part(text=system_prompt)]
            ),
            contents=[
                Content(
                    role='user',
                    parts=[Part(text=final_prompt)]
                )
            ]
        )

        response = client.generate_content(request=request_payload, timeout=30)
        reply = ''
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                reply = ''.join([part.text or '' for part in candidate.content.parts])

        return jsonify({"reply": reply})

    except Exception as e:
        current_app.logger.exception("Erreur Gemini")
        return jsonify({"error": f"Erreur de communication avec l'IA: {e}"}), 500
