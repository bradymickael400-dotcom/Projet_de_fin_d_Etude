"""Risk projections based on recent telemetry and box-specific thresholds.

These are transparent rate projections, not statistical probabilities or legal
compliance findings. A forecast is emitted only when the observation window is
large enough to support a rate calculation.
"""

from datetime import datetime, timezone

from sqlalchemy import text


def assess_window(readings, speeds, thresholds, positions=None):
    """Summarize recent incidents and provide conditional, explainable actions."""
    rows = list(readings or [])
    speed_values = [float(value) for value in (speeds or []) if value is not None]
    shock_limit = float((thresholds or {}).get("choc_max") or 5.0)
    speed_limit = float((thresholds or {}).get("vitesse_max") or 90.0)
    shock_values = [float(row.get("shock")) for row in rows if row.get("shock") is not None]
    shock_events = [value for value in shock_values if value > shock_limit]
    speed_events = [value for value in speed_values if value > speed_limit]
    window_seconds = 0.0
    if len(rows) > 1:
        first, last = rows[-1].get("measured_at"), rows[0].get("measured_at")
        if first and last:
            window_seconds = max(0.0, (last - first).total_seconds())
    rate_available = window_seconds >= 60
    hours = window_seconds / 3600 if rate_available else 0
    peak_shock = max(shock_values, default=0.0)
    peak_speed = max(speed_values, default=0.0)
    stationary_minutes = 0.0
    stationary_zone = None
    track = [point for point in (positions or []) if point.get("latitude") is not None
             and point.get("longitude") is not None and point.get("measured_at")]
    if len(track) >= 2 and all(float(point.get("speed") or 0) <= 3 for point in track[:7]):
        newest, oldest = track[0]["measured_at"], track[min(6, len(track) - 1)]["measured_at"]
        stationary_minutes = max(0.0, (newest - oldest).total_seconds() / 60)
        first = track[0]
        close = all(
            _distance_m(float(first["latitude"]), float(first["longitude"]),
                        float(point["latitude"]), float(point["longitude"])) <= 250
            for point in track[:7]
        )
        if close and stationary_minutes >= 6:
            stationary_zone = _zone_at(float(first["latitude"]), float(first["longitude"]))
    projected_shocks_per_hour = round(len(shock_events) / hours, 1) if hours else None
    projected_speed_violations_per_hour = round(len(speed_events) / hours, 1) if hours else None

    signals = []
    recommendations = []
    if shock_events:
        signals.append("chocs_au_dessus_du_seuil")
        recommendations.append("Limiter les manœuvres, inspecter l’arrimage et vérifier le capteur avant de poursuivre.")
    if speed_events:
        signals.append("vitesse_au_dessus_du_seuil")
        recommendations.append("Demander au conducteur de ralentir et vérifier la limite locale applicable au tronçon.")
    if any(bool(row.get("door_open")) for row in rows[:3]):
        signals.append("porte_ouverte_recente")
        recommendations.append("Vérifier immédiatement le scellé et l’autorisation d’ouverture.")
    if any(bool(row.get("security_alarm")) for row in rows[:3]):
        signals.append("alarme_securite_recente")
        recommendations.append("Vérifier l’alarme et appliquer le protocole de sûreté de l’entreprise.")
    if stationary_zone is not None:
        signals.append("immobilisation_prolongee_dans_une_zone")
        place = f" dans « {stationary_zone} »" if stationary_zone else ""
        recommendations.append(f"Vérifier la cause et la sécurité du véhicule{place}, puis confirmer la reprise du trajet.")

    level = "critical" if peak_shock >= max(shock_limit * 2, shock_limit + 1) or any(
        bool(row.get("security_alarm")) for row in rows[:3]
    ) else "warning" if len(shock_events) >= 2 or speed_events or stationary_zone is not None or any(
        bool(row.get("door_open")) for row in rows[:3]
    ) else "normal" if rows else "unknown"
    return {
        "risk_level": level,
        "signals": signals,
        "sample_count": len(rows),
        "window_seconds": round(window_seconds, 1),
        "forecast_method": "linear_rate_if_observation_window_at_least_60_seconds",
        "rate_available": rate_available,
        "thresholds": {"shock_g": shock_limit, "speed_kmh": speed_limit},
        "shock_count_above_threshold": len(shock_events),
        "shock_g_sum_above_threshold": round(sum(shock_events), 2),
        "peak_shock_g": round(peak_shock, 2),
        "projected_shocks_per_hour_if_rate_continues": projected_shocks_per_hour,
        "speed_exceedance_count": len(speed_events),
        "peak_speed_kmh": round(peak_speed, 1),
        "stationary_minutes": round(stationary_minutes, 1),
        "stationary_zone": stationary_zone,
        "projected_speed_exceedances_per_hour_if_rate_continues": projected_speed_violations_per_hour,
        "recommendations": recommendations,
        "limitations": [
            "Projection descriptive et conditionnelle; ce n’est pas une probabilité de panne ou d’accident.",
            "Seuil ARGOS configuré; les limites réglementaires dépendent du trajet et restent à vérifier.",
        ],
    }


def assess_recent_box_risk(black_box_id, limit=20):
    """Load the recent sensor and speed window for an already authorized box."""
    from app.extensions import db

    rows = db.session.execute(text("""
        SELECT shock, door_open, security_alarm, measured_at
        FROM sensor_readings
        WHERE black_box_id=:box
        ORDER BY measured_at DESC
        LIMIT :limit
    """), {"box": int(black_box_id), "limit": max(2, min(int(limit), 60))}).fetchall()
    readings = [dict(row._mapping) for row in rows]
    positions = db.session.execute(text("""
        SELECT latitude,longitude,speed,measured_at FROM positions WHERE black_box_id=:box
        ORDER BY measured_at DESC LIMIT :limit
    """), {"box": int(black_box_id), "limit": max(2, min(int(limit), 60))}).fetchall()
    speeds = [row.speed for row in positions]
    threshold_row = db.session.execute(text("""
        SELECT choc_max, vitesse_max FROM seuils_alerte WHERE id_boite=:box
    """), {"box": int(black_box_id)}).fetchone()
    thresholds = dict(threshold_row._mapping) if threshold_row else {}
    return assess_window(readings, speeds, thresholds, [dict(row._mapping) for row in positions])


def _distance_m(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    value = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 6371000 * 2 * asin(sqrt(value))


def _zone_at(latitude, longitude):
    try:
        from app.services.geofence_service import point_in_polygon
        from app.extensions import db
        zones = db.session.execute(text("""
            SELECT zone_name, polygon FROM brady.argos_geofence_zones WHERE enabled=TRUE
        """)).fetchall()
        for zone in zones:
            if point_in_polygon(latitude, longitude, zone.polygon):
                return str(zone.zone_name)
    except Exception:
        return None
    return None


def create_proactive_risk_notification(black_box_id, device_uid=None, sequence=None):
    """Persist an alert and send an email when a recent trend needs attention."""
    from app.extensions import db
    from app.regulatory.history import record_decision
    from app.utils import get_public_base_url, send_email_background
    from app.modules.iot.iot_event_service import _concerned_emails

    assessment = assess_recent_box_risk(black_box_id)
    if assessment["risk_level"] not in {"warning", "critical"}:
        return assessment
    if assessment["risk_level"] == "warning" and not assessment["rate_available"]:
        return assessment

    level = assessment["risk_level"]
    title = "Risque critique détecté" if level == "critical" else "Tendance à surveiller"
    summary = (
        f"{title} — boîte #{black_box_id}. Chocs au-dessus du seuil: "
        f"{assessment['shock_count_above_threshold']} (somme observée {assessment['shock_g_sum_above_threshold']} G); "
        f"pic {assessment['peak_shock_g']} G. Vitesses au-dessus du seuil: "
        f"{assessment['speed_exceedance_count']}, pic {assessment['peak_speed_kmh']} km/h."
    )
    if assessment.get("stationary_zone"):
        summary += (f" Immobilisation observée {assessment['stationary_minutes']} minutes dans "
                    f"{assessment['stationary_zone']}.")
    if assessment.get("projected_shocks_per_hour_if_rate_continues") is not None:
        summary += (" Si la cadence de la fenêtre observée se maintient : environ "
                    f"{assessment['projected_shocks_per_hour_if_rate_continues']} dépassements de choc/heure "
                    "(projection indicative, non probabiliste).")
    advice = " ".join(assessment["recommendations"])
    summary += f" Recommandations : {advice or 'Surveiller les prochaines mesures.'}"
    cooldown = 15 if level == "critical" else 45
    exists = db.session.execute(text("""
        SELECT 1 FROM notifications
        WHERE id_boite=:box AND type='PROACTIVE_RISK' AND message LIKE :title_prefix
          AND horodatage >= NOW() - (:minutes * INTERVAL '1 minute') LIMIT 1
    """), {"box": black_box_id, "title_prefix": f"{title}%", "minutes": cooldown}).scalar()
    if exists:
        return assessment
    db.session.execute(text("""
        INSERT INTO notifications(type,message,cible_role,id_boite,device_uid,sequence)
        VALUES('PROACTIVE_RISK',:message,'all',:box,:device,:sequence)
    """), {"message": summary, "box": black_box_id, "device": device_uid, "sequence": sequence})
    record_decision(
        identity={"role": "system", "user_id": "proactive_risk_service"},
        black_box_id=int(black_box_id), subject_type="risk_forecast",
        subject_id=f"{black_box_id}:{sequence or datetime.now(timezone.utc).isoformat()}:{level}",
        event_type="PROACTIVE_RISK_ALERT", action="Projection préventive à partir de la fenêtre IoT récente",
        reaction=summary,
        remarks={**assessment, "device_uid": device_uid, "sequence": sequence,
                 "legal_applicability": "TO_VERIFY"},
        source_keys=["ARGOS_THRESHOLD_RULES", "ARGOS_IOT_TELEMETRY", "ARGOS_AGENT_RULES"],
    )
    emails = _concerned_emails(black_box_id)
    if emails:
        threading_target = send_email_background
        import threading
        threading.Thread(
            target=threading_target,
            args=(emails, f"[{level.upper()}] {title} — ARGOS boîte #{black_box_id}", summary),
            kwargs={"severity": level, "action_url": get_public_base_url(),
                    "action_label": "Ouvrir ARGOS et consulter le dossier"},
            daemon=True,
        ).start()
    db.session.commit()
    return assessment
