"""Niveaux d'affichage explicables des notifications ARGOS."""

import re
import unicodedata


def notification_severity(notification_type, message=""):
    """Mappe les types et libellés connus vers danger|warning|info|success."""
    kind = str(notification_type or "").upper()
    raw = str(message or "").casefold()
    normalized = "".join(
        char for char in unicodedata.normalize("NFKD", raw)
        if not unicodedata.combining(char)
    )
    if kind in {"AI_RISK_ALERT", "PROACTIVE_RISK"}:
        return "danger" if any(word in normalized for word in ("critique", "critical", "flamme", "incendie", "alarme securite")) else "warning"
    if kind in {"IOT_ALERT", "THRESHOLD_ALERT"}:
        return "danger" if any(word in normalized for word in (
            "flamme", "incendie", "alarme", "ouverture non autorisee",
            "porte ouverte", "ouverture detectee", "alarme de securite active",
            "choc severe",
        )) else "warning"
    if kind == "ROUTE_DEVIATION":
        match = re.search(r"score operationnel\s+(\d+(?:\.\d+)?)\s*%", normalized)
        return "danger" if match and float(match.group(1)) >= 85 else "warning"
    if kind in {"GEOFENCE_ENTRY", "PORT_PROXIMITY_DETECTED"}:
        return "info"
    if kind in {"CONTAINER_OPENED", "SECURITY_ALARM"}:
        return "danger"
    if kind.endswith("_FAILED") or kind.endswith("_ERROR"):
        return "danger"
    return "info"
