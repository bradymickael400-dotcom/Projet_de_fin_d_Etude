"""Appels d'outils autorisés et coordination multi-agents."""

from uuid import uuid4

from app.agents import build_registry


OPERATIONAL_AGENTS = {"iot_monitor", "gps_route", "risk_assessor"}


def agent_tools(registry, identity, selected_box_ids=None):
    tools = []
    for agent in registry.discover():
        if identity.get("role") not in agent["allowed_roles"]:
            continue
        if agent["agent_id"] in OPERATIONAL_AGENTS and not selected_box_ids:
            continue
        tools.append({
            "name": agent["agent_id"],
            "description": agent["description"],
            "parameters": agent["parameters"],
        })
    return tools


def run_agent_request(message, identity, provider, registry=None, black_box_id=None,
                      black_box_ids=None, trace_id=None):
    registry = registry or build_registry()
    trace_id = trace_id or str(uuid4())
    selected_box_ids = [str(value) for value in (black_box_ids or [])]
    if black_box_id and str(black_box_id) not in selected_box_ids:
        selected_box_ids.append(str(black_box_id))
    selected_box_ids = list(dict.fromkeys(selected_box_ids))
    enriched_message = message
    if selected_box_ids:
        enriched_message += (
            "\n\nPérimètre explicitement choisi par l'utilisateur (boîtes noires): "
            + ", ".join(selected_box_ids)
            + ". N'analyse aucune autre boîte. Pour une comparaison, consulte les capacités "
              "opérationnelles pour chaque identifiant choisi et rapproche les résultats."
        )
    tools = agent_tools(registry, identity, selected_box_ids)

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
                from app.agents.registry import AgentResult
                return AgentResult(name, "denied", error="Boîte non sélectionnée par l'utilisateur")
        return registry.execute(name, arguments, identity, trace_id)

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

    for item in results["tool_results"]:
        record_agent(item)
    consulted = consulted_order
    sources = []
    for item in results["tool_results"]:
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
        "reply": results["reply"],
        "trace_id": trace_id,
        "agents_consulted": consulted,
        "agent_results": results["tool_results"],
        "sources": deduped_sources,
        "limitations": ["Les capacités indisponibles ou sans données sont indiquées explicitement."],
    }
