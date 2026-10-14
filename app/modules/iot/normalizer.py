"""Normalisation des messages IoT valides.

Les valeurs brutes restent disponibles dans ``iot_raw_messages``. Les valeurs
exposees au temps reel, aux alertes et aux tables de mesures sont en revanche
neutralisees lorsque le firmware indique explicitement qu'un capteur n'est pas
fiable. Cela empeche les valeurs de repli du prototype (par exemple 1013.25 hPa)
d'etre prises pour des mesures reelles.
"""


def normalize_telemetry_quality(validated):
    """Retourne une copie de la telemetrie avec les capteurs invalides a ``None``."""
    normalized = dict(validated)
    sensors = dict(validated.get("sensors") or {})
    quality = dict(validated.get("quality") or {})

    if quality.get("dhtValid") is False:
        sensors["temperature"] = None
        sensors["humidity"] = None
    if quality.get("mpuValid") is False:
        sensors["shock"] = None
        sensors["accelerationX"] = None
        sensors["accelerationY"] = None
        sensors["accelerationZ"] = None
    if quality.get("pressureMeasured") is False:
        sensors["pressure"] = None
    if quality.get("batteryMeasured") is False:
        sensors["batteryLevel"] = None
    if quality.get("distanceValid") is False:
        sensors["distanceCm"] = None

    normalized["sensors"] = sensors
    normalized["quality"] = quality
    return normalized


def telemetry_to_event_payload(validated):
    validated = normalize_telemetry_quality(validated)
    position = validated["position"]
    sensors = validated["sensors"]
    modes = validated["modes"]
    alerts = []
    if sensors["flameDetected"] and modes["flameDetectionEnabled"]:
        alerts.append("Flamme detectee")
    if sensors["doorOpen"] and modes["securityEnabled"]:
        alerts.append("Ouverture detectee")
    if sensors["securityAlarm"] and modes["securityEnabled"]:
        alerts.append("Alarme de securite active")
    return {
        "message_id": validated["message_id"],
        "device_uid": validated["device_uid"],
        "sequence": validated["sequence"],
        "temperature": sensors["temperature"],
        "humidite": sensors["humidity"],
        "pressions": sensors["pressure"],
        "chocs": sensors["shock"],
        "battery_level": sensors["batteryLevel"],
        "light_level": sensors["lightLevel"],
        "sound_level": sensors["soundLevel"],
        "distance_cm": sensors["distanceCm"],
        "security_alarm": sensors["securityAlarm"],
        "lat": position["latitude"],
        "lon": position["longitude"],
        "vitesse": position["speed"],
        "heading": position["heading"],
        "notif": alerts,
        "modes": modes,
        "quality": validated.get("quality") or {},
        "alert": validated.get("alert") or {},
        "horodatage": validated["timestamp"],
    }
