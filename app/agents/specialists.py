"""Agents opérationnels composés au-dessus des services ARGOS existants."""

from datetime import datetime, timezone
import re

from flask import has_app_context
from sqlalchemy import text

from app.agents.registry import AgentRegistry, AgentResult, AgentSpec
from app.extensions import db


OPERATIONAL_ROLES = frozenset({"superadmin", "owner", "company", "client", "driver", "port_authority"})
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
    try:
        from app.services.route_intelligence_service import route_tracking_for_box
        tracking = route_tracking_for_box(box_id, 100)
        value["route_tracking"] = tracking["summary"]
        value["recent_route_points"] = [{key: point.get(key) for key in (
            "sequence", "measured_at", "latitude", "longitude", "speed", "accuracy", "source", "route_state", "route_assessment"
        )} for point in tracking["points"][-20:]]
        value["planned_route_assessment"] = (
            tracking["points"][-1].get("route_assessment")
            if tracking["points"] else None
        )
    except Exception:
        # Le suivi GPS reste disponible si la migration de route n'a pas encore
        # été appliquée; aucune donnée de route n'est alors présentée au LLM.
        db.session.rollback()
        value["planned_route_assessment"] = None
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
    from app.services.shock_assessment import get_box_shock_threshold
    shock_threshold = get_box_shock_threshold(box_id)
    if readings.get("shock") is not None:
        if float(readings["shock"]) > shock_threshold:
            signals.append("shock_above_configured_threshold")
    from app.services.proactive_risk_service import assess_window
    forecast = assess_window(
        [{"shock": readings.get("shock"), "door_open": readings.get("door_open"),
          "security_alarm": readings.get("security_alarm")}],
        [position.data.get("speed_kmh")] if position.data.get("speed_kmh") is not None else [],
        {"choc_max": shock_threshold},
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
            "black_box_id": int(box_id),
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


def transport_regulatory_agent(arguments: dict, _identity: dict, _registry: AgentRegistry) -> AgentResult:
    """Prépare une revue réglementaire contextualisée, sans inférer l'applicabilité."""
    from app.regulatory.history import search_regulatory_sources

    query = str(arguments.get("query") or "transport conteneur logistique").strip()[:500]
    mode = str(arguments.get("mode") or "").strip().lower()
    mode = {"maritime": "sea", "mer": "sea", "routier": "road",
            "route": "road", "ferroviaire": "rail", "train": "rail"}.get(mode, mode)
    if mode and mode not in {"road", "sea", "rail", "multimodal", "digital"}:
        return AgentResult("transport_regulatory", "invalid", error="mode non reconnu")
    jurisdiction = str(arguments.get("jurisdiction") or "").strip()[:100]
    origin = str(arguments.get("origin") or "").strip()[:100]
    destination = str(arguments.get("destination") or "").strip()[:100]
    goods = str(arguments.get("goods") or "").strip()[:160]
    assessment_date = str(arguments.get("assessment_date") or "").strip()[:20]
    search_terms = " ".join(filter(None, [query, mode, jurisdiction, origin, destination, goods]))
    candidates = search_regulatory_sources(search_terms, limit=20)
    # The regional inventory helps locate likely data holders, but it is not
    # itself a law, a verified source register, or proof of rule applicability.
    from app.knowledge.rag import search_knowledge
    regional_context = search_knowledge(search_terms + " données opérationnelles corridor escales ETA incidents")
    if mode:
        candidates = [item for item in candidates if mode in (item.get("transport_modes") or [])]
    if jurisdiction:
        needle = jurisdiction.casefold()
        candidates = [item for item in candidates if (
            needle in str(item.get("jurisdiction") or "").casefold()
            or "international" in str(item.get("jurisdiction") or "").casefold()
            or (needle in {"cameroun", "cameroon"}
                and "cemac" in str(item.get("jurisdiction") or "").casefold())
        )]
    missing = [label for label, value in (
        ("juridiction/pays concernés", jurisdiction), ("mode de transport", mode),
        ("itinéraire et pays traversés", f"{origin}:{destination}" if origin and destination else ""),
        ("nature/classe des marchandises", goods), ("date du transport", assessment_date),
    ) if not value]
    for item in candidates:
        item["applicability_status"] = "TO_VERIFY"
    return AgentResult(
        "transport_regulatory", "success" if candidates else "empty",
        data={
            "query": query, "context": {"jurisdiction": jurisdiction or None, "mode": mode or None,
                "origin": origin or None, "destination": destination or None,
                "goods": goods or None, "assessment_date": assessment_date or None},
            "missing_context": missing, "applicability_status": "TO_VERIFY",
            "candidates": candidates,
            "regional_data_context": regional_context,
            "regional_context_note": "Ces passages décrivent des sources de données candidates fournies par l'équipe; ils ne sont pas des références juridiques et leur disponibilité n'est pas vérifiée par cet agent.",
            "skills_used": ["mode_and_jurisdiction_scoping", "source_version_and_status_review",
                "dangerous_goods_context", "container_and_cargo_evidence", "citation_provenance",
                "human_review_escalation"],
            "decision": "Aucune conclusion de conformité; les références sont des pistes documentaires à vérifier.",
        },
        provenance=[{"source_key": item["source_key"], "source": item["title"],
            "official_url": item.get("official_url"), "jurisdiction": item.get("jurisdiction"),
            "legal_status": item.get("legal_status"), "applicability_status": "TO_VERIFY"}
            for item in candidates] + regional_context,
    )


def port_intelligence_agent(arguments: dict, identity: dict, _registry: AgentRegistry) -> AgentResult:
    """Compétences métier sur les ports, statistiques sourcées et proximité de boîte."""
    from app.services.geofence_service import distance_meters

    query = str(arguments.get("query") or "").strip()[:300]
    if not query:
        return AgentResult("port_intelligence", "invalid", error="query requise")
    from app.knowledge.rag import search_knowledge
    regional_context = search_knowledge(query)
    box_id = None
    if arguments.get("black_box_id") not in (None, ""):
        box_id, error = _resolve_box({"black_box_id": arguments["black_box_id"]}, identity)
        if error:
            return AgentResult("port_intelligence", "denied", error=error)
    ports = db.session.execute(text("""
        SELECT port_id, port_name, country, country_code, latitude, longitude,
               location_type, operational_status, coordinate_precision,
               verification_status, coordinate_source, proximity_radius_m
        FROM brady.argos_port_locations WHERE enabled=TRUE
        ORDER BY country, port_name
    """)).fetchall()
    query_terms = {term.casefold() for term in re.findall(r"[\wÀ-ÿ-]+", query) if len(term) > 2}
    selected_ports = []
    for port in ports:
        item = dict(port._mapping)
        label = f"{item['port_name']} {item['country']} {item['country_code']} {item['port_id']}".casefold()
        if not query_terms or any(term in label for term in query_terms):
            selected_ports.append(item)
    generic_terms = {
        "port", "ports", "portuaire", "portuaires", "terminal", "terminaux",
        "trafic", "statistique", "statistiques", "conteneur", "conteneurs",
        "afrique", "centrale", "central", "donnee", "donnees",
    }
    if not selected_ports and query_terms and query_terms.issubset(generic_terms):
        selected_ports = [dict(port._mapping) for port in ports]
    port_ids = [item["port_id"] for item in selected_ports]
    stats = []
    if port_ids:
        rows = db.session.execute(text("""
            SELECT port_id,period_year,indicator,value,unit,source_url,source_page,
                   verification_status,notes
            FROM brady.argos_port_statistics WHERE port_id=ANY(CAST(:port_ids AS varchar[]))
            ORDER BY period_year DESC,port_id,indicator
        """), {"port_ids": port_ids}).fetchall()
        stats = [dict(row._mapping) for row in rows]
    location = None
    port_journey = None
    if box_id:
        row = db.session.execute(text("""
            SELECT latitude,longitude,measured_at FROM positions
            WHERE black_box_id=:box AND latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY measured_at DESC LIMIT 1
        """), {"box": int(box_id)}).fetchone()
        if row:
            location = {"black_box_id": int(box_id), "latitude": float(row.latitude),
                        "longitude": float(row.longitude), "measured_at": row.measured_at.isoformat(),
                        "nearby_ports": []}
            for port in ports:
                distance = distance_meters(row.latitude, row.longitude, port.latitude, port.longitude)
                if distance <= float(port.proximity_radius_m):
                    location["nearby_ports"].append({
                        "port_id": port.port_id, "port_name": port.port_name,
                        "distance_m": round(distance), "radius_m": port.proximity_radius_m,
                        "status": "PROXIMITY_ONLY_NOT_OFFICIAL_PORT_ENTRY",
                        "coordinate_verification": port.verification_status,
                    })
        try:
            from app.services.route_intelligence_service import port_tracking_for_box
            tracking = port_tracking_for_box(box_id, 500, include_points=False)
            port_journey = {
                "window_start": tracking.get("window_start"),
                "window_end": tracking.get("window_end"),
                "point_count": tracking.get("point_count", 0),
                "current_nearby_ports": tracking.get("current_nearby_ports", []),
                "events": tracking.get("events", [])[-30:],
                "limitations": tracking.get("limitations", []),
            }
        except Exception:
            db.session.rollback()
    return AgentResult(
        "port_intelligence", "success" if selected_ports or stats or regional_context else "empty",
        data={
            "query": query, "ports": selected_ports, "statistics": stats,
            "regional_documentary_evidence": regional_context,
            "regional_documentary_evidence_note": "Les passages de l'inventaire fourni par l'équipe sont des pistes documentaires, non revérifiées indépendamment; ils restent séparés des statistiques et positions structurées ARGOS.",
            "selected_box_location": location,
            "port_journey": port_journey,
            "skills_used": ["port_and_terminal_identification", "port_proximity_awareness",
                "port_and_geofence_entry_exit_tracking", "route_to_port_contextualization",
                "coordinate_quality_and_boundary_uncertainty",
                "port_statistics_source_and_unit_interpretation", "transshipment_vs_unique_container_distinction",
                "port_risk_triage", "port_authority_human_escalation"],
            "limitations": [
                "Les coordonnées sont des points de référence provisoires, pas des limites de ports.",
                "Une proximité GPS ne prouve pas l'entrée dans une enceinte portuaire contrôlée.",
                "Les statistiques sont celles fournies dans le référentiel et leurs sources n'ont pas été revérifiées ici.",
                "Aucun incident réel ou taux de perte n'est présent dans le jeu de données initial.",
            ],
        },
        provenance=[{"source_key": "ARGOS_PORT_LOCATIONS", "source": item["port_name"],
                     "port_id": item["port_id"], "coordinate_source": item["coordinate_source"],
                     "verification_status": item["verification_status"]} for item in selected_ports]
            + [{"source_key": "ARGOS_PORT_STATISTICS", "source": item["indicator"],
                "port_id": item["port_id"], "year": item["period_year"],
                "unit": item["unit"], "official_url": item["source_url"],
                "verification_status": item["verification_status"]} for item in stats]
            + regional_context,
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
        "gps_route", "1.1", "Suivi de position, corridor et dérive",
        "operational.position.read", "Lire la position récente, le corridor prévu, l'historique de trajectoire et les écarts mesurés point par point.",
        {"type": "object", "properties": {
            "black_box_id": {"type": "string"}, "voyage_id": {"type": "integer"},
        }, "required": ["black_box_id"]},
        OPERATIONAL_ROLES, position_agent,
        output_schema={"type": "object", "required": ["black_box_id", "source"]},
        tools_or_services=("get_hybrid_position", "route_tracking_for_box", "container_voyage_assignment"),
        limitations=("Une position ancienne est signalée par sa source et son âge.", "Le score d'écart est géométrique et opérationnel, pas une probabilité.", "Une position indisponible reste explicitement null."),
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
    registry.register(AgentSpec(
        "transport_regulatory", "1.0", "Préparation d'une revue réglementaire contextualisée du transport",
        "transport.regulatory.scope", "Repérer les sources de transport selon la juridiction, le mode, le trajet, la marchandise et la date; signale toujours ce qui reste à vérifier.",
        {"type": "object", "properties": {
            "query": {"type": "string"}, "jurisdiction": {"type": "string"},
            "mode": {"type": "string"}, "origin": {"type": "string"},
            "destination": {"type": "string"}, "goods": {"type": "string"},
            "assessment_date": {"type": "string"}}, "required": ["query"]},
        DOCUMENT_ROLES, transport_regulatory_agent,
        output_schema={"type": "object", "required": ["context", "missing_context", "applicability_status", "candidates", "skills_used"]},
        tools_or_services=("regulatory_sources",),
        limitations=("Recherche lexicale de références; ne tranche pas l'applicabilité ni la conformité.",
                     "Les sources doivent être validées et le corpus officiel/versionné alimenté par ARGOS."),
    ))
    registry.register(AgentSpec(
        "port_intelligence", "1.1", "Intelligence de trajet et de proximité portuaire en Afrique centrale",
        "transport.port_intelligence", "Rechercher des ports et statistiques sourcés, puis expliquer les zones configurées et les transitions de proximité portuaire du trajet d'une boîte autorisée.",
        {"type": "object", "properties": {"query": {"type": "string"},
            "black_box_id": {"type": "string"}}, "required": ["query"]},
        DOCUMENT_ROLES, port_intelligence_agent,
        output_schema={"type": "object", "required": ["ports", "statistics", "skills_used", "limitations"]},
        tools_or_services=("argos_port_locations", "argos_port_statistics", "port_tracking_for_box", "geofence_service"),
        limitations=("Repères géographiques et statistiques initiaux non certifiés; proximité indicative, non détection du périmètre officiel.", "Les traversées de polygones reflètent la configuration ARGOS; elles ne certifient pas une entrée dans un périmètre officiel."),
    ))
