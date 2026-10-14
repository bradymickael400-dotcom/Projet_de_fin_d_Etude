"""Cache temps reel Redis pour la telemetrie IoT.

Redis recoit la mesure valide avant sa persistence PostgreSQL. Le flux conserve
une courte fenetre rejouable et la cle ``latest`` alimente les vues temps reel.
L'ingestion reste disponible en developpement/tests lorsque Redis n'est pas
configure; en production, ``IOT_REDIS_REQUIRED=true`` rend Redis obligatoire.
"""

import json

from flask import current_app, has_app_context


STREAM_KEY = "argos:telemetry:stream"
LATEST_BOX_KEY_PREFIX = "argos:telemetry:latest:box:"


def _client():
    if not has_app_context():
        return None
    url = str(current_app.config.get("IOT_REDIS_URL") or "").strip()
    if not url:
        return None
    from redis import Redis
    return Redis.from_url(url, decode_responses=True, socket_timeout=2)


def publish(validated, event_payload, black_box_id, container_id):
    """Publie atomiquement la mesure dans le flux et le cache par appareil."""
    client = _client()
    if client is None:
        if has_app_context() and current_app.config.get("IOT_REDIS_REQUIRED"):
            raise RuntimeError("Redis IoT non configure")
        return {"cached": False}
    document = {
        "messageId": validated["message_id"],
        "deviceUid": validated["device_uid"],
        "sequence": validated["sequence"],
        "blackBoxId": black_box_id,
        "containerId": container_id,
        "timestamp": validated["timestamp"].isoformat(),
        "position": validated["position"],
        "sensors": validated["sensors"],
        "modes": validated["modes"],
        "quality": validated.get("quality") or {},
        "alerts": event_payload.get("notif") or [],
    }
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    try:
        pipe = client.pipeline(transaction=True)
        pipe.setex(f"argos:telemetry:latest:{validated['device_uid']}", 86400, encoded)
        pipe.setex(f"argos:telemetry:latest:box:{black_box_id}", 86400, encoded)
        pipe.xadd(STREAM_KEY, {"payload": encoded}, maxlen=10000, approximate=True)
        result = pipe.execute()
        return {"cached": True, "streamId": result[-1]}
    except Exception:
        if current_app.config.get("IOT_REDIS_REQUIRED"):
            raise
        current_app.logger.warning("Redis IoT indisponible; persistence directe", exc_info=True)
        return {"cached": False}


def read_latest_by_boxes(black_box_ids=None, limit=100):
    """Retourne les dernieres mesures Redis, triees de la plus recente a l'ancienne.

    ``black_box_ids`` vaut ``None`` pour le périmètre global du superadministrateur.
    Une liste vide signifie au contraire qu'aucune boîte n'est autorisée. La fonction
    reste volontairement tolérante en développement : l'appelant peut alors se
    rabattre sur PostgreSQL.
    """
    if black_box_ids is not None and not black_box_ids:
        return []

    client = _client()
    if client is None:
        return []

    try:
        if black_box_ids is None:
            keys = list(client.scan_iter(match=f"{LATEST_BOX_KEY_PREFIX}*", count=200))
        else:
            # dict.fromkeys conserve l'ordre tout en supprimant les doublons.
            keys = [
                f"{LATEST_BOX_KEY_PREFIX}{box_id}"
                for box_id in dict.fromkeys(str(value) for value in black_box_ids)
            ]
        if not keys:
            return []

        values = client.mget(keys)
        documents = []
        for encoded in values:
            if not encoded:
                continue
            try:
                document = json.loads(encoded)
            except (TypeError, ValueError):
                continue
            if isinstance(document, dict):
                documents.append(document)

        documents.sort(
            key=lambda item: str(item.get("timestamp") or ""),
            reverse=True,
        )
        return documents[:max(1, min(int(limit or 100), 500))]
    except Exception:
        if has_app_context():
            current_app.logger.warning(
                "Lecture du cache IoT Redis impossible; repli PostgreSQL",
                exc_info=True,
            )
        return []
