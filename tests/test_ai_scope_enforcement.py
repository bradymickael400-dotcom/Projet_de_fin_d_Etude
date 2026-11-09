from app.agents.orchestrator import (
    _sanitize_scope_text,
    agent_tools,
    run_agent_request,
)
from app.agents.registry import AgentRegistry, AgentResult, AgentSpec


def _operational_registry(handler):
    registry = AgentRegistry()
    registry.register(AgentSpec(
        agent_id="iot_monitor",
        version="test",
        mission="Read selected box telemetry",
        capability="test.telemetry",
        description="Read telemetry for one selected box",
        parameters={
            "type": "object",
            "properties": {"black_box_id": {"type": "string"}},
            "required": ["black_box_id"],
        },
        allowed_roles=frozenset({"superadmin"}),
        handler=handler,
    ))
    return registry


def test_single_box_scope_hides_internal_id_and_masks_other_box_references():
    result = _sanitize_scope_text(
        "Boîte ARGOS #17 et boîte 18 (CONT-18), puis CONT-99, ont été comparées.",
        {"17"},
        {"17": "CONT-17"},
        ["CONT-18"],
    )

    assert result == "le conteneur CONT-17 et une boîte hors périmètre ([référence hors périmètre]), puis [référence de conteneur masquée], ont été comparées."


def test_one_selected_box_is_server_injected_and_tool_context_is_redacted():
    calls = []

    def telemetry(arguments, _identity, _registry):
        calls.append(arguments["black_box_id"])
        return AgentResult("iot_monitor", "success", {
            "black_box_id": 17,
            "container_id": "CONT-17",
            "temperature": 5.2,
        })

    registry = _operational_registry(telemetry)

    class Provider:
        model_tool_result = None
        message = None
        tools = None

        def generate(self, message, tools, invoke_tool):
            Provider.message = message
            Provider.tools = tools
            # A malicious or confused model requests another box. The server
            # must bind the tool call to the one selected by the user.
            result = invoke_tool("iot_monitor", {"black_box_id": "18"})
            Provider.model_tool_result = result.to_dict()
            return {
                "reply": "La boîte #18 (CONT-18) est à comparer avec boîte 17.",
                "tool_results": [Provider.model_tool_result],
            }

    outcome = run_agent_request(
        "Analyse la boîte 17 et CONT-18",
        {"role": "superadmin", "user_id": "test"},
        Provider(),
        registry=registry,
        black_box_ids=["17"],
        selected_container_refs={"17": "CONT-17"},
        hidden_identifiers=["CONT-18"],
    )

    assert calls == ["17"]
    properties = Provider.tools[0]["parameters"]["properties"]
    assert "black_box_id" not in properties
    assert "black_box_id" not in Provider.message
    assert "CONT-18" not in Provider.message
    assert "black_box_id" not in Provider.model_tool_result["data"]
    assert Provider.model_tool_result["data"]["container_id"] == "CONT-17"
    assert "CONT-18" not in outcome["reply"]
    assert "boîte hors périmètre" in outcome["reply"]
    assert "CONT-17" in outcome["reply"]
    # The audit payload retains only the server-selected internal ID.
    assert outcome["agent_results"][0]["data"]["black_box_id"] == 17


def test_selected_scope_does_not_remove_box_id_parameter_for_explicit_comparisons():
    registry = _operational_registry(lambda *_args: AgentResult("iot_monitor", "empty"))

    tools = agent_tools(registry, {"role": "superadmin"}, ["17", "18"])

    assert tools[0]["parameters"]["properties"]["black_box_id"]["type"] == "string"
    assert tools[0]["parameters"]["required"] == ["black_box_id"]


def test_ai_picker_lists_all_non_archived_boxes_in_the_profile_scope(monkeypatch):
    from types import SimpleNamespace
    import app.routes.dashboard as dashboard

    captured = {}

    class Session:
        def execute(self, statement, parameters):
            captured["sql"] = str(statement).lower()
            captured["parameters"] = parameters
            return SimpleNamespace(fetchall=lambda: [
                (17, "CONT-17", "SN-17"),
                (18, None, "SN-18"),
            ])

    monkeypatch.setattr(dashboard.db, "session", Session())
    monkeypatch.setattr(dashboard, "_visible_boites_for", lambda role, user_id: [17, 18])

    available = dashboard._ai_available_containers({"role": "client", "user_id": "client-1"})

    assert available == [
        {
            "black_box_id": "17", "container_id": "CONT-17", "box_label": "SN-17",
            "label": "SN-17 — conteneur CONT-17",
        },
        {
            "black_box_id": "18", "container_id": None, "box_label": "SN-18",
            "label": "SN-18 — sans conteneur associé",
        },
    ]
    assert "coalesce(b.archived, false) = false" in captured["sql"]
    assert "lower(coalesce(b.status, '')) = 'active'" not in captured["sql"]
    assert "b.id_conteneurs is not null" not in captured["sql"]
    assert "lower(coalesce(a.status, '')) = 'actif'" in captured["sql"]
    assert captured["parameters"]["actor_id"] == "client-1"


def test_legacy_ai_route_uses_the_same_profile_and_selection_gate(monkeypatch):
    from app import create_app
    import app.security as security
    import app.routes.dashboard as dashboard

    identity = {"role": "client", "user_id": "client-1"}
    monkeypatch.setattr(security, "authenticate_request", lambda: identity)
    monkeypatch.setattr(dashboard, "_ai_available_containers", lambda _identity: [{
        "black_box_id": "17", "container_id": "CONT-17", "label": "CONT-17",
    }])
    app = create_app()
    app.config.update(TESTING=True, API_KEY="configured")
    app.db_initialized = True
    client = app.test_client()

    selection = client.post("/api/ai/deepseek", json={"message": "Analyse ma boîte."})
    denied = client.post("/api/ai/deepseek", json={
        "message": "Analyse cette boîte.", "black_box_ids": ["18"],
    })

    assert selection.status_code == 200
    assert selection.get_json()["status"] == "needs_container_selection"
    assert [row["black_box_id"] for row in selection.get_json()["available_containers"]] == ["17"]
    assert denied.status_code == 403
