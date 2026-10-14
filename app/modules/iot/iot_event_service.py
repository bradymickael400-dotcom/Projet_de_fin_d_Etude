"""Événements, notifications et e-mails produits par l'ingestion IoT."""

import threading

from sqlalchemy import text

from app.extensions import db
from app.utils import get_public_base_url, send_email_background


ALERT_COOLDOWN_MINUTES = 45


def add_configured_threshold_alerts(event_payload, thresholds):
    """Ajoute les dépassements de seuil configurés pour la boîte."""
    if not thresholds:
        return event_payload.get("notif") or []
    alerts = list(event_payload.get("notif") or [])
    temperature = event_payload.get("temperature")
    temperature = float(temperature) if temperature is not None else None
    humidity = event_payload.get("humidite")
    humidity = float(humidity) if humidity is not None else None
    shock = event_payload.get("chocs")
    shock = float(shock) if shock is not None else None
    pressure = event_payload.get("pressions")
    pressure = float(pressure) if pressure is not None else None
    speed = event_payload.get("vitesse")
    speed = float(speed) if speed is not None else None
    temp_min = getattr(thresholds, "temp_min", None)
    temp_max = getattr(thresholds, "temp_max", None)
    shock_max = getattr(thresholds, "choc_max", None)
    if temperature is not None and temp_min is not None and temperature < float(temp_min):
        alerts.append(f"Température trop basse : {temperature:.1f} °C (min. {float(temp_min):.1f} °C)")
    if temperature is not None and temp_max is not None and temperature > float(temp_max):
        alerts.append(f"Température trop élevée : {temperature:.1f} °C (max. {float(temp_max):.1f} °C)")
    if shock is not None and shock_max is not None and shock > float(shock_max):
        alerts.append(f"Choc excessif : {shock:.2f} g (max. {float(shock_max):.2f} g)")
    if humidity is not None and getattr(thresholds, "humi_min", None) is not None and humidity < float(thresholds.humi_min):
        alerts.append(f"Humidité trop basse : {humidity:.1f} % (min. {float(thresholds.humi_min):.1f} %)")
    if humidity is not None and getattr(thresholds, "humi_max", None) is not None and humidity > float(thresholds.humi_max):
        alerts.append(f"Humidité trop élevée : {humidity:.1f} % (max. {float(thresholds.humi_max):.1f} %)")
    if pressure is not None and getattr(thresholds, "pression_min", None) is not None and pressure < float(thresholds.pression_min):
        alerts.append(f"Pression trop basse : {pressure:.1f} hPa (min. {float(thresholds.pression_min):.1f} hPa)")
    if pressure is not None and getattr(thresholds, "pression_max", None) is not None and pressure > float(thresholds.pression_max):
        alerts.append(f"Pression trop élevée : {pressure:.1f} hPa (max. {float(thresholds.pression_max):.1f} hPa)")
    if speed is not None and getattr(thresholds, "vitesse_max", None) is not None and speed > float(thresholds.vitesse_max):
        alerts.append(f"Vitesse excessive : {speed:.1f} km/h (max. {float(thresholds.vitesse_max):.1f} km/h)")
    event_payload["notif"] = list(dict.fromkeys(alerts))
    return event_payload["notif"]


def _concerned_emails(black_box_id):
    """Adresses liées au conteneur courant ; aucune si la boîte est libre."""
    rows = db.session.execute(text("""
        SELECT p.addresse_mail AS email
        FROM boite_noir b JOIN proprietaire_conteneur p ON p.id=b.id_proprietaire
        WHERE b.id_boite=:box AND b.id_conteneurs IS NOT NULL
        UNION
        SELECT a.addresse_mail
        FROM boite_noir b
        JOIN agence_abonnement aa ON aa.id_boite=b.id_boite
        JOIN agence_utilisatrice a ON a.niu=aa.id_agence
        WHERE b.id_boite=:box AND b.id_conteneurs IS NOT NULL
          AND LOWER(COALESCE(aa.status,'actif'))='actif'
        UNION
        SELECT c.address_mail
        FROM boite_noir b
        JOIN abonner ab ON ab.id_boite=b.id_boite
        JOIN client c ON c.id_cni=ab.id_cni
        WHERE b.id_boite=:box AND b.id_conteneurs IS NOT NULL
          AND LOWER(COALESCE(ab.status,'actif'))='actif'
    """), {"box": black_box_id}).fetchall()
    return sorted({str(row.email).strip() for row in rows if row.email and "@" in str(row.email)})


def create_threshold_notifications(black_box_id, alerts, device_uid=None, sequence=None):
    if not black_box_id or not alerts:
        return
    message = " | ".join(dict.fromkeys(alerts))
    duplicate = db.session.execute(text("""
        SELECT 1 FROM notifications
        WHERE id_boite=:box AND type='IOT_ALERT' AND message=:message
          AND horodatage >= NOW() - (:minutes * INTERVAL '1 minute')
        LIMIT 1
    """), {"box": black_box_id, "message": message,
           "minutes": ALERT_COOLDOWN_MINUTES}).scalar()
    if duplicate:
        return
    db.session.execute(text("""
        INSERT INTO notifications
            (type, message, cible_role, id_boite, device_uid, sequence)
        VALUES ('IOT_ALERT', :message, 'all', :id_boite, :device_uid, :sequence)
    """), {"message": message, "id_boite": black_box_id,
            "device_uid": device_uid, "sequence": sequence})
    emails = _concerned_emails(black_box_id)
    if emails:
        subject = f"[ARGOS] Alerte boîte noire #{black_box_id}"
        content = (f"Une anomalie a été détectée sur la boîte noire #{black_box_id}.\n\n"
                   f"{message}\n\nConsultez immédiatement l’application ARGOS.")
        threading.Thread(
            target=send_email_background,
            args=(emails, subject, content), daemon=True,
            kwargs={
                "severity": "critical",
                "action_url": get_public_base_url(),
                "action_label": "Consulter l'alerte",
            },
        ).start()
