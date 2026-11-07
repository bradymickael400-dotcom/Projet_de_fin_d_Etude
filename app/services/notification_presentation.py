"""Human-readable notification headlines while preserving complete details."""

import unicodedata


TITLES = {
    "ROUTE_DEVIATION": "Dérive de trajet détectée",
    "PORT_PROXIMITY_DETECTED": "Proximité portuaire signalée",
    "GEOFENCE_ENTRY": "Entrée dans une zone surveillée",
    "IOT_ALERT": "Alerte capteur",
    "THRESHOLD_ALERT": "Seuil opérationnel dépassé",
    "AI_RISK_ALERT": "Risque de transport à examiner",
    "PROACTIVE_RISK": "Risque de transport à examiner",
    "SECURITY_ALARM": "Alarme de sécurité",
    "CONTAINER_OPENED": "Ouverture du conteneur détectée",
    "CONTAINER_DETACHED": "Boîte dissociée du conteneur",
    "IOT_DIRECT_CONNECTED": "Boîte ARGOS connectée",
}


def notification_presentation(notification_type, message):
    kind = str(notification_type or "").upper()
    details = str(message or "Notification ARGOS")
    normalized = "".join(char for char in unicodedata.normalize("NFKD", details.casefold())
                         if not unicodedata.combining(char))
    title = TITLES.get(kind, kind.replace("_", " ").capitalize() or "Notification ARGOS")

    if "flamme" in normalized or "incendie" in normalized:
        reason = "Le capteur a signalé une présence de flamme."
    elif "alarme de securite" in normalized or "alarme securite" in normalized:
        reason = "L’alarme de sécurité du conteneur s’est déclenchée."
    elif "ouverture non autorisee" in normalized or "ouverture detectee" in normalized or "porte ouverte" in normalized:
        reason = "Le capteur a détecté une ouverture du conteneur."
    elif "choc severe" in normalized:
        reason = "Un choc a dépassé le niveau sévère configuré."
    elif "choc" in normalized or "shock" in normalized:
        reason = "La mesure de choc a dépassé le seuil configuré."
    elif kind == "ROUTE_DEVIATION":
        reason = "La position GPS s’est écartée du corridor planifié au-delà du seuil d’alerte."
    elif kind == "PORT_PROXIMITY_DETECTED":
        reason = "La position GPS se trouve près d’un point de référence portuaire."
    elif kind == "GEOFENCE_ENTRY":
        reason = "Une position GPS est entrée dans une zone géographique configurée."
    elif "temperature" in normalized or "température" in details.casefold():
        reason = "La température mesurée est sortie de la plage configurée."
    elif "humidite" in normalized or "humidité" in details.casefold():
        reason = "L’humidité mesurée est sortie de la plage configurée."
    elif "vitesse" in normalized:
        reason = "La vitesse mesurée a dépassé le seuil configuré."
    else:
        reason = details.split(" | ", 1)[0].strip()[:220]

    return {"title": title, "summary": title, "reason": reason, "details": details}
