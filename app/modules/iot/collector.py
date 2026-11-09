"""Nœud C (Collector) du pipeline ARGOS, selon le vocabulaire ITU-T Y.3172.

Le collecteur accepte les messages de sources SRC, conserve le message reçu,
applique le contrat de validation et remet un événement validé au prétraitement.
Il ne remplace ni le transport réseau ni le traitement métier en aval.
"""

from app.modules.iot import repository as repo
from app.modules.iot.validator import PayloadValidationError, validate_telemetry_payload


NODE_ID = "C"
NODE_NAME = "Collector"


def collect_telemetry(payload, remote_addr=None, message_type="telemetry"):
    """Collecte et valide une trame télémétrique provenant d'une source SRC.

    Retourne ``(message_id, telemetry)`` pour le prétraitement. En cas de rejet,
    le message brut est conservé avec son état et sa raison de rejet lorsque la
    base peut être utilisée, puis l'erreur est propagée à l'API appelante.
    """
    try:
        telemetry = validate_telemetry_payload(payload)
    except PayloadValidationError as exc:
        try:
            repo.insert_raw_message(
                payload if isinstance(payload, dict) else {}, message_type,
                remote_addr, "REJECTED", str(exc),
            )
            from app.extensions import db
            db.session.commit()
        except Exception:
            # La validation/requête API conserve son erreur initiale même si
            # le journal de collecte est momentanément indisponible.
            try:
                from app.extensions import db
                db.session.rollback()
            except Exception:
                pass
            pass
        raise

    message_id = repo.insert_raw_message(payload, message_type, remote_addr, "VALIDATED")
    return message_id, telemetry
