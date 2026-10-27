"""Agents opérationnels composés au-dessus des services ARGOS existants."""

from datetime import datetime, timezone

from flask import has_app_context
from sqlalchemy import text

from app.agents.registry import AgentRegistry, AgentResult, AgentSpec
from app.extensions import db


OPERATIONAL_ROLES = frozenset({"superadmin", "owner", "company", "client", "driver"})
DOCUMENT_ROLES = frozenset({"superadmin", "owner", "company", "client", "driver", "port_authority"})


def _visible_box_ids(identity: dict) -> list[str] | None:
    role = identity.get("role")
    if role == "superadmin":
        return None
    if role not in OPERATIONAL_ROLES:
        return []
    from app.routes.dashboard import _visible_boites_for

    values = _visible_boites_for(role, identity.get("user_id")) or []
    return [str(value) for value in values]


def _resolve_box(arguments: dict, identity: dict) -> tuple[str | None, str | None]:
    requested = str(arguments.get("black_box_id") or "").strip()
    if not requested:
        return None, "black_box_id requis"
    if not requested.isdigit() or int(requested) <= 0:
        return None, "black_box_id invalide"
    allowed = _visible_box_ids(identity)
    if allowed is not None and requested not in allowed:
        return None, "Boîte hors périmètre autorisé"
    return requested, None


def telemetry_agent(arguments: dict, identity: dict, _registry: AgentRegistry) -> AgentResult:
    box_id, error = _resolve_box(arguments, identity)
    if error:
        return AgentResult("iot_monitor", "denied" if "périmètre" in error else "invalid", error=error)
    row = db.session.execute(text("""
        SELECT black_box_id, container_id, temperature, humidity, shock, pressure,
               flame_detected, door_open, battery_level, security_alarm,
               measured_at, sequence, quality
        FROM sensor_readings
        WHERE black_box_id = :box_id
        ORDER BY measured_at DESC
        LIMIT 1
    """), {"box_id": int(box_id)}).fetchone()
    if not row:
        return AgentResult("iot_monitor", "empty", data={"black_box_id": int(box_id)})
    measured_at = row.measured_at
    if measured_at.tzinfo is None:
        measured_at = measured_at.replace(tzinfo=timezone.utc)
    age_seconds = max(0, int((datetime.now(timezone.utc) - measured_at).total_seconds()))
    return AgentResult(
        "iot_monitor", "success",
        data={
            "black_box_id": row.black_box_id,
            "container_id": row.container_id,
            "temperature": row.temperature,
            "humidity": row.humidity,
            "shock": row.shock,
            "pressure": row.pressure,
            "flame_detected": bool(row.flame_detected),
            "door_open": bool(row.door_open),
            "battery_level": row.battery_level,
            "security_alarm": bool(row.security_alarm),
            "measured_at": measured_at.isoformat(),
            "age_seconds": age_seconds,
            "sequence": row.sequence,
            "quality": row.quality or {},
        },
        provenance=[{"source": "sensor_readings", "black_box_id": int(box_id)}],
    )


def position_agent(arguments: dict, identity: dict, _registry: AgentRegistry) -> AgentResult:
    box_id, error = _resolve_box(arguments, identity)
    if error:
        return AgentResult("gps_route", "denied" if "périmètre" in error else "invalid", error=error)
    voyage_id = arguments.get("voyage_id")
    if voyage_id is not None and (not str(voyage_id).isdigit() or int(voyage_id) <= 0):
        return AgentResult("gps_route", "invalid", error="voyage_id invalide")
    if voyage_id is not None:
        assignment = db.session.execute(text("""
            SELECT 1 FROM container_voyage_assignment
            WHERE id_boite = :box_id AND voyage_id = :voyage_id
            LIMIT 1
        """), {"box_id": int(box_id), "voyage_id": int(voyage_id)}).scalar()
        if not assignment:
            return AgentResult("gps_route", "denied", error="Voyage non associé à cette boîte")
    from app.services.positioning_service import get_hybrid_position

    value = get_hybrid_position(box_id, int(voyage_id) if voyage_id else None)
    return AgentResult(
        "gps_route", "success" if value.get("source") != "unavailable" else "empty",
        data={"black_box_id": int(box_id), **value},
        provenance=[{"source": value.get("source", "unavailable"), "timestamp": value.get("ts")}],
    )


def risk_agent(arguments: dict, identity: dict, registry: AgentRegistry) -> AgentResult:
    """Consomme les résultats de deux autres agents sans passer par le LLM."""
    box_id = str(arguments.get("black_box_id") or "").strip()
    telemetry = registry.execute("iot_monitor", {"black_box_id": box_id}, identity, "")
    position = registry.execute("gps_route", {"black_box_id": box_id}, identity, "")
    if telemetry.status == "denied" or position.status == "denied":
        return AgentResult("risk_assessor", "denied", error="Périmètre opérationnel refusé")
    signals = []
    readings = telemetry.data
    if readings.get("flame_detected") or readings.get("security_alarm"):
        signals.append("security_alarm")
    if readings.get("door_open"):
        signals.append("door_open")
    if readings.get("shock") is not None:
        from app.services.positioning_service import SHOCK_ALERT_THRESHOLD_G
        if readings["shock"] >= SHOCK_ALERT_THRESHOLD_G:
            signals.append("shock_above_existing_threshold")
    from app.services.proactive_risk_service import assess_window
    forecast = assess_window(
        [{"shock": readings.get("shock"), "door_open": readings.get("door_open"),
          "security_alarm": readings.get("security_alarm")}],
        [position.data.get("speed_kmh")] if position.data.get("speed_kmh") is not None else [],
        {},
    )
    if has_app_context():
        try:
            from app.services.proactive_risk_service import assess_recent_box_risk
            recent = assess_recent_box_risk(box_id)
            if recent.get("sample_count", 0) >= 2:
                forecast = recent
        except Exception:
            db.session.rollback()
    stale = position.data.get("source") == "last_known"
    return AgentResult(
        "risk_assessor", "success" if telemetry.status == "success" else telemetry.status,
        data={
            "risk_level": forecast.get("risk_level") if forecast.get("risk_level") not in {"normal", "unknown"} else ("warning" if signals else "undetermined"),
            "signals": signals,
            "stale_position": stale,
            "assessment_basis": "deterministic_existing_rules",
            "forecast": forecast,
            "recommendations": forecast.get("recommendations", []),
            "legal_applicability": "TO_VERIFY",
            "consumed_results": [telemetry.to_dict(), position.to_dict()],
        },
        provenance=telemetry.provenance + position.provenance,
        error=telemetry.error or position.error,
    )


def knowledge_agent(arguments: dict, identity: dict, _registry: AgentRegistry) -> AgentResult:
    from app.knowledge.rag import search_knowledge
    from app.regulatory.history import search_regulatory_sources

    query = str(arguments.get("query") or "").strip()
    if not query or len(query) > 1000:
        return AgentResult("knowledge_retriever", "invalid", error="query requise (1000 caractères max)")
    hits = search_knowledge(query)
    references = search_regulatory_sources(query)
    return AgentResult(
        "knowledge_retriever", "success" if hits or references else "empty",
        data={"query": query, "passages": hits, "references": references},
        provenance=hits + [{"source_key": item["source_key"], "source": item["title"],
                            "official_url": item.get("official_url"),
                            "jurisdiction": item["jurisdiction"],
                            "legal_status": item["legal_status"],
                            "applicability_status": "TO_VERIFY"} for item in references],
    )


def register_specialists(registry: AgentRegistry) -> None:
    registry.register(AgentSpec(
        "iot_monitor", "1.0", "Lecture de la dernière mesure IoT validée",
        "operational.telemetry.latest", "Lire les mesures IoT récentes d'une boîte noire.",
        {"type": "object", "properties": {"black_box_id": {"type": "string"}}, "required": ["black_box_id"]},
        OPERATIONAL_ROLES, telemetry_agent,
        output_schema={"type": "object", "required": ["black_box_id", "measured_at", "age_seconds"]},
        tools_or_services=("sensor_readings",),
        limitations=("Retourne uniquement la mesure la plus récente.", "L'accès DB au moment de l'appel n'est pas sondé dans le registre."),
    ))
    registry.register(AgentSpec(
        "gps_route", "1.0", "Lecture de position et fraîcheur",
        "operational.position.read", "Lire la position disponible, sa source et son âge.",
        {"type": "object", "properties": {
            "black_box_id": {"type": "string"}, "voyage_id": {"type": "integer"},
        }, "required": ["black_box_id"]},
        OPERATIONAL_ROLES, position_agent,
        output_schema={"type": "object", "required": ["black_box_id", "source"]},
        tools_or_services=("get_hybrid_position", "container_voyage_assignment"),
        limitations=("Une position ancienne est signalée par sa source et son âge.", "Une position indisponible reste explicitement null."),
    ))
    registry.register(AgentSpec(
        "risk_assessor", "1.0", "Rapprochement de signaux IoT et GPS",
        "operational.risk.assess", "Évaluer des signaux à partir des résultats IoT et GPS.",
        {"type": "object", "properties": {"black_box_id": {"type": "string"}}, "required": ["black_box_id"]},
        OPERATIONAL_ROLES, risk_agent,
        output_schema={"type": "object", "required": ["risk_level", "signals", "consumed_results"]},
        tools_or_services=("iot_monitor", "gps_route"),
        limitations=("Évaluation déterministe, non probabiliste et non ML.",),
    ))
    registry.register(AgentSpec(
        "knowledge_retriever", "1.0", "Recherche textuelle locale avec provenance",
        "knowledge.search", "Rechercher des passages dans les documents autorisés présents localement.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        DOCUMENT_ROLES, knowledge_agent,
        output_schema={"type": "object", "required": ["query", "passages"]},
        tools_or_services=("local filesystem",),
        limitations=("Recherche lexicale locale; absence de corpus ou de document pertinent retourne zéro passage.",),
    ))
