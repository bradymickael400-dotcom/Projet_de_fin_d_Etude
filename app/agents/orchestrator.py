"""Appels d'outils autorisés et coordination multi-agents."""

import re
from uuid import uuid4

from app.agents import build_registry
from app.agents.registry import AgentResult


OPERATIONAL_AGENTS = {"iot_monitor", "gps_route", "risk_assessor"}
OPTIONAL_PERSONAL_CONTEXT_AGENTS = {"port_intelligence"}
INSTITUTIONAL_POLICY_AGENTS = {
    "policy_operator", "policy_customs_port", "policy_data_protection", "policy_adviser",
}
_BOX_REFERENCE_PATTERNS = (
    re.compile(r"\b(?:bo[iî]te(?:\s+(?:noire|argos))?|box|container|conteneur)(?:\s+(?:id|n[°o.]?))?[-_\s]*#?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(?:id[_ ](?:de[_ ])?bo[iî]te|black[_ ]box(?:[_ ]id)?)\s*[:=#]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(?:id|identifiant)\s+(?:de\s+)?(?:la\s+)?(?:bo[iî]te|conteneur)\s*[:=#]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(?:id|identifiant)\s+(?:technique|de routage)\s*[:=#]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(?:id|identifiant)\s*[:=]\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"(?<!\w)#(\d+)\b"),
)
_CONTAINER_CODE_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:[A-Z]{4}\d{7}|(?:CONT(?:AINER|ENEUR)?|CNTR)[-_][A-Z0-9]{2,})(?![A-Z0-9])",
    re.IGNORECASE,
)
_INTERNAL_ID_KEYS = {
    "black_box_id", "black_box_ids", "id_boite", "box_id", "box_ids",
    "device_id", "deviceid", "device_uid", "hardware_serial", "uuid_qrcode",
}
_CONTAINER_ID_KEYS = {"container_id", "container_ids", "id_conteneurs"}


def _sanitize_scope_text(value, selected_box_ids, selected_refs_by_box, hidden_identifiers=()):
    """Masque les identifiants hors sélection et les IDs techniques dans le texte LLM."""
    text = str(value or "")
    for identifier in sorted({str(item).strip() for item in hidden_identifiers if str(item).strip()}, key=len, reverse=True):
        text = re.sub(
            rf"(?<![\w]){re.escape(identifier)}(?![\w])",
            "[référence hors périmètre]",
            text,
            flags=re.IGNORECASE,
        )

    def replace_box_reference(match):
        box_id = match.group(1)
        if box_id not in selected_box_ids:
            return "une boîte hors périmètre"
        container_ref = selected_refs_by_box.get(box_id)
        return f"le conteneur {container_ref}" if container_ref else "le conteneur sélectionné"

    for pattern in _BOX_REFERENCE_PATTERNS:
        text = pattern.sub(replace_box_reference, text)

    selected_container_refs = {value.casefold() for value in selected_refs_by_box.values() if value}
    def replace_container_code(match):
        code = match.group(0)
        return code if code.casefold() in selected_container_refs else "[référence de conteneur masquée]"

    return _CONTAINER_CODE_PATTERN.sub(replace_container_code, text)


def _sanitize_tool_value(value, key, selected_box_ids, selected_refs_by_box, hidden_identifiers):
    if isinstance(value, dict):
        cleaned = {}
        for child_key, child in value.items():
            normalized_key = str(child_key).casefold()
            if normalized_key in _INTERNAL_ID_KEYS:
                continue
            if normalized_key in _CONTAINER_ID_KEYS:
                values = child if isinstance(child, list) else [child]
                allowed_refs = {ref.casefold() for ref in selected_refs_by_box.values() if ref}
                safe_values = [item for item in values if str(item).casefold() in allowed_refs]
                if safe_values:
                    cleaned[child_key] = safe_values if isinstance(child, list) else safe_values[0]
                continue
            cleaned_value = _sanitize_tool_value(
                child, normalized_key, selected_box_ids, selected_refs_by_box, hidden_identifiers
            )
            if cleaned_value is not None:
                cleaned[child_key] = cleaned_value
        return cleaned
    if isinstance(value, list):
        return [
            cleaned for item in value
            if (cleaned := _sanitize_tool_value(
                item, key, selected_box_ids, selected_refs_by_box, hidden_identifiers
            )) is not None
        ]
    if isinstance(value, str):
        return _sanitize_scope_text(value, selected_box_ids, selected_refs_by_box, hidden_identifiers)
    return value


def _sanitize_tool_result(result, selected_box_ids, selected_refs_by_box, hidden_identifiers):
    return AgentResult(
        agent_id=result.agent_id,
        status=result.status,
        data=_sanitize_tool_value(
            result.data, "data", selected_box_ids, selected_refs_by_box, hidden_identifiers
        ),
        provenance=_sanitize_tool_value(
            result.provenance, "provenance", selected_box_ids, selected_refs_by_box, hidden_identifiers
        ),
        error=_sanitize_scope_text(result.error, selected_box_ids, selected_refs_by_box, hidden_identifiers)
        if result.error else None,
        message_id=result.message_id,
        timestamp=result.timestamp,
    )


def agent_tools(registry, identity, selected_box_ids=None):
    selected_box_ids = [str(value) for value in (selected_box_ids or [])]
    tools = []
    for agent in registry.discover():
        if identity.get("role") not in agent["allowed_roles"]:
            continue
        # Ces capacités doivent être appelées par le coordinateur de scénario,
        # qui fournit à chaque rôle uniquement ses faits et ses sources filtrées.
        # Les exposer ensemble au chat général annulerait ce cloisonnement.
        if agent["agent_id"] in INSTITUTIONAL_POLICY_AGENTS:
            continue
        if agent["agent_id"] in OPERATIONAL_AGENTS and not selected_box_ids:
            continue
        parameters = dict(agent["parameters"])
        parameters["properties"] = dict(parameters.get("properties") or {})
        parameters["required"] = list(parameters.get("required") or [])
        if agent["agent_id"] in OPERATIONAL_AGENTS and len(selected_box_ids) == 1:
            # Le serveur connaît l'unique boîte sélectionnée. Ne pas exposer son
            # identifiant technique au modèle ni lui demander de le répéter.
            parameters["properties"].pop("black_box_id", None)
            parameters["required"] = [key for key in parameters["required"] if key != "black_box_id"]
        if agent["agent_id"] in OPTIONAL_PERSONAL_CONTEXT_AGENTS and not selected_box_ids:
            # Les ports et statistiques sont publics; la propriété de boîte est
            # absente du schéma tant que l'utilisateur n'en a pas choisi une.
            parameters = dict(parameters)
            parameters["properties"] = {
                key: value for key, value in parameters.get("properties", {}).items()
                if key != "black_box_id"
            }
        tools.append({
            "name": agent["agent_id"],
            "description": agent["description"],
            "parameters": parameters,
        })
    return tools


def run_agent_request(message, identity, provider, registry=None, black_box_id=None,
                      black_box_ids=None, trace_id=None, selected_container_refs=None,
                      hidden_identifiers=None):
    registry = registry or build_registry()
    trace_id = trace_id or str(uuid4())
    selected_box_ids = [str(value) for value in (black_box_ids or [])]
    if black_box_id and str(black_box_id) not in selected_box_ids:
        selected_box_ids.append(str(black_box_id))
    selected_box_ids = list(dict.fromkeys(selected_box_ids))
    selected_refs_by_box = {
        str(box_id): str(reference).strip()
        for box_id, reference in (selected_container_refs or {}).items()
        if str(reference or "").strip()
    }
    hidden_identifiers = [str(value) for value in (hidden_identifiers or []) if str(value).strip()]
    enriched_message = _sanitize_scope_text(
        message, set(selected_box_ids), selected_refs_by_box, hidden_identifiers
    )
    if selected_box_ids:
        scope_lines = ["\n\nPérimètre autorisé choisi par l'utilisateur :"]
        if len(selected_box_ids) == 1:
            reference = selected_refs_by_box.get(selected_box_ids[0])
            scope_lines.append(
                f"Un seul conteneur est sélectionné; référence autorisée : {reference}."
                if reference else "Un seul conteneur est sélectionné; ne révèle aucun ID technique."
            )
        else:
            for box_id in selected_box_ids:
                reference = selected_refs_by_box.get(box_id)
                scope_lines.append(
                    f"ID de routage {box_id}; référence autorisée à montrer : {reference}."
                    if reference else f"ID de routage {box_id}; ne révèle aucun ID technique."
                )
        scope_lines.append(
            "Ne consulte et ne cite aucune autre boîte. Les IDs internes servent uniquement "
            "au routage des outils; ne les affiche jamais. Utilise la référence conteneur "
            "autorisée lorsqu'elle existe."
        )
        enriched_message += "\n".join(scope_lines)
    tools = agent_tools(registry, identity, selected_box_ids)
    raw_tool_results = []

    def checked_result(result):
        raw_tool_results.append(result)
        return _sanitize_tool_result(
            result, set(selected_box_ids), selected_refs_by_box, hidden_identifiers
        )

    def invoke_tool(name, arguments):
        arguments = dict(arguments or {})
        if name in OPERATIONAL_AGENTS:
            requested_id = str(arguments.get("black_box_id") or "")
            if len(selected_box_ids) == 1:
                # Avec un seul choix, l'identifiant sélectionné fait autorité
                # même si le modèle tente d'en transmettre un autre.
                requested_id = selected_box_ids[0]
                arguments["black_box_id"] = requested_id
            if not requested_id or requested_id not in selected_box_ids:
                return checked_result(AgentResult(name, "denied", error="Boîte non sélectionnée par l'utilisateur"))
        if name in OPTIONAL_PERSONAL_CONTEXT_AGENTS and arguments.get("black_box_id"):
            requested_id = str(arguments["black_box_id"])
            if len(selected_box_ids) == 1:
                requested_id = selected_box_ids[0]
                arguments["black_box_id"] = requested_id
            if requested_id not in selected_box_ids:
                return checked_result(AgentResult(name, "denied", error="Boîte non sélectionnée par l'utilisateur"))
        return checked_result(registry.execute(name, arguments, identity, trace_id))

    results = provider.generate(
        message=enriched_message,
        tools=tools,
        invoke_tool=invoke_tool,
    )
    consulted_order = []

    def record_agent(item):
        agent_id = item.get("agent_id")
        if agent_id and agent_id not in consulted_order:
            consulted_order.append(agent_id)
        for child in (item.get("data") or {}).get("consumed_results", []):
            record_agent(child)

    tool_results = [item.to_dict() for item in raw_tool_results]
    if not tool_results:
        tool_results = results.get("tool_results", [])
    for item in tool_results:
        record_agent(item)
    consulted = consulted_order
    sources = []
    for item in tool_results:
        sources.extend(item.get("provenance") or [])
        passages = item.get("data", {}).get("passages", [])
        sources.extend({"source": p["source"], "line_start": p["line_start"], "line_end": p["line_end"]} for p in passages)
        sources.extend(item.get("data", {}).get("references", []))
    deduped_sources = []
    seen = set()
    for source in sources:
        key = (source.get("source"), source.get("line_start"), source.get("timestamp"), source.get("black_box_id"))
        if key not in seen:
            seen.add(key)
            deduped_sources.append(source)
    return {
        "reply": _sanitize_scope_text(
            results["reply"], set(selected_box_ids), selected_refs_by_box, hidden_identifiers
        ),
        "trace_id": trace_id,
        "agents_consulted": consulted,
        "agent_results": tool_results,
        "sources": deduped_sources,
        "limitations": ["Les capacités indisponibles ou sans données sont indiquées explicitement."],
    }
