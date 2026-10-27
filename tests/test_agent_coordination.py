from app.agents.orchestrator import run_agent_request
from app.agents.registry import AgentRegistry, AgentResult, AgentSpec
from app.agents.specialists import risk_agent
from app.llm.gemini import GeminiToolProvider


IDENTITY = {"role": "superadmin", "user_id": "test-user"}


def _agent(agent_id, handler, description="test agent", parameters=None):
    return AgentSpec(
        agent_id=agent_id,
        version="test-1",
        mission=description,
        capability=f"test.{agent_id}",
        description=description,
        parameters=parameters or {"type": "object", "properties": {"black_box_id": {"type": "string"}}},
        allowed_roles=frozenset({"superadmin"}),
        handler=handler,
    )


def test_risk_agent_consumes_two_other_agents_results():
    calls = []
    registry = AgentRegistry()

    def telemetry(_arguments, _identity, _registry):
        calls.append("iot_monitor")
        return AgentResult("iot_monitor", "success", {"shock": 4.2, "door_open": True}, [{"source": "sensor_readings"}])

    def position(_arguments, _identity, _registry):
        calls.append("gps_route")
        return AgentResult("gps_route", "success", {"source": "last_known", "freshness_min": 95}, [{"source": "iot_position", "timestamp": "2026-10-27T10:00:00Z"}])

    registry.register(_agent("iot_monitor", telemetry))
    registry.register(_agent("gps_route", position))

    result = risk_agent({"black_box_id": "17"}, IDENTITY, registry)

    assert calls == ["iot_monitor", "gps_route"]
    assert result.status == "success"
    assert result.data["signals"] == ["door_open", "shock_above_existing_threshold"]
    assert result.data["stale_position"] is True
    assert [item["agent_id"] for item in result.data["consumed_results"]] == ["iot_monitor", "gps_route"]
    assert len(result.provenance) == 2


class FakeGeminiSession:
    def __init__(self):
        self.payloads = []

    def post(self, _url, **kwargs):
        self.payloads.append(kwargs["json"])
        if len(self.payloads) == 1:
            payload = {"candidates": [{"content": {"role": "model", "parts": [
                {"functionCall": {"name": "iot_monitor", "args": {"black_box_id": "99"}}},
                {"functionCall": {"name": "gps_route", "args": {"black_box_id": "99"}}},
                {"functionCall": {"name": "risk_assessor", "args": {"black_box_id": "99"}}},
                {"functionCall": {"name": "knowledge_retriever", "args": {"query": "cold container"}}},
            ]}}]}
        else:
            payload = {"candidates": [{"content": {"role": "model", "parts": [
                {"text": "Les mesures et la position ont été rapprochées."}
            ]}}]}

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return payload

        return Response()


def test_llm_one_request_invokes_multiple_agents_and_receives_results():
    calls = []
    registry = AgentRegistry()

    def telemetry(arguments, _identity, _registry):
        calls.append(("iot_monitor", arguments["black_box_id"]))
        return AgentResult("iot_monitor", "success", {"temperature": 5.1}, [{"source": "sensor_readings"}])

    def position(arguments, _identity, _registry):
        calls.append(("gps_route", arguments["black_box_id"]))
        return AgentResult("gps_route", "success", {"source": "iot", "lat": 4.05, "lon": 9.7}, [{"source": "positions", "timestamp": "2026-10-27T10:00:00Z"}])

    def knowledge(_arguments, _identity, _registry):
        return AgentResult("knowledge_retriever", "success", {
            "passages": [{"source": "cold-chain.md", "line_start": 4, "line_end": 5, "text": "Keep cargo cold."}]
        }, [{"source": "cold-chain.md", "line_start": 4, "line_end": 5}])

    registry.register(_agent("iot_monitor", telemetry))
    registry.register(_agent("gps_route", position))
    registry.register(_agent("risk_assessor", risk_agent))
    registry.register(_agent("knowledge_retriever", knowledge, parameters={
        "type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]
    }))
    session = FakeGeminiSession()
    provider = GeminiToolProvider(api_key="test-key", model="models/test", session=session, base_url="https://llm.invalid")

    outcome = run_agent_request(
        "Analyse cette boîte", IDENTITY, provider, registry=registry,
        black_box_id="17", trace_id="trace-test",
    )

    assert calls == [
        ("iot_monitor", "17"), ("gps_route", "17"),
        ("iot_monitor", "17"), ("gps_route", "17"),
    ]
    assert outcome["reply"] == "Les mesures et la position ont été rapprochées."
    assert outcome["agents_consulted"] == ["iot_monitor", "gps_route", "risk_assessor", "knowledge_retriever"]
    assert len(outcome["agent_results"]) == 4
    assert outcome["agent_results"][2]["data"]["consumed_results"]
    assert any(source.get("source") == "cold-chain.md" for source in outcome["sources"])
    assert len(session.payloads) == 2
    declarations = session.payloads[0]["tools"][0]["functionDeclarations"]
    assert declarations[0]["parameters"]["type"] == "OBJECT"
    assert declarations[0]["parameters"]["properties"]["black_box_id"]["type"] == "STRING"
    function_responses = session.payloads[1]["contents"][-1]["parts"]
    assert [part["functionResponse"]["name"] for part in function_responses] == [
        "iot_monitor", "gps_route", "risk_assessor", "knowledge_retriever"
    ]
    assert all("data" in part["functionResponse"]["response"] for part in function_responses)


def test_knowledge_search_returns_only_local_cited_passages(tmp_path):
    from app.knowledge.rag import search_knowledge

    (tmp_path / "policy.md").write_text("# Chaîne du froid\n\nConserver le conteneur froid et consigner température mesurée.\n", encoding="utf-8")
    (tmp_path / "unrelated.txt").write_text("Registre de maintenance du véhicule.", encoding="utf-8")

    hits = search_knowledge("température conteneur froid", root=tmp_path)

    assert hits
    assert hits[0]["source"] == "policy.md"
    assert "température" in hits[0]["text"]
    assert hits[0]["line_start"] == 3


def test_registry_denies_unlisted_role_and_rejects_extra_arguments():
    from app.agents.registry import AgentRegistry, AgentResult

    registry = AgentRegistry()
    calls = []
    registry.register(_agent("restricted", lambda args, identity, _registry: (
        calls.append((args, identity)) or AgentResult("restricted", "success", {"ok": True})
    )))

    denied = registry.execute("restricted", {"black_box_id": "17"}, {"role": "client"}, "trace")
    invalid = registry.execute(
        "restricted", {"black_box_id": "17", "admin": True}, IDENTITY, "trace"
    )

    assert denied.status == "denied"
    assert invalid.status == "invalid"
    assert calls == []


def test_knowledge_search_does_not_follow_symlink_outside_corpus(tmp_path):
    from app.knowledge.rag import search_knowledge

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    outside = tmp_path / "private.md"
    outside.write_text("Secret transport credentials and access policy.", encoding="utf-8")
    (corpus / "outside.md").symlink_to(outside)

    assert search_knowledge("transport credentials", root=corpus) == []


def test_api_rejects_role_headers_without_a_signed_identity():
    from app import create_app

    app = create_app()
    app.db_initialized = True
    response = app.test_client().get(
        "/api/dashboard/superadmin",
        headers={"X-Role": "superadmin", "X-User-Id": "forged"},
    )

    assert response.status_code == 401
    assert response.get_json()["code"] == "AUTH_REQUIRED"


def test_ai_api_requests_scope_before_provider_even_when_not_configured(monkeypatch):
    from app import create_app
    import app.security as security

    app = create_app()
    app.config["TESTING"] = True
    app.config["API_KEY"] = ""
    app.db_initialized = True
    monkeypatch.setattr(security, "authenticate_request", lambda: IDENTITY)
    monkeypatch.setattr("app.routes.dashboard._ai_available_containers", lambda _identity: [])

    response = app.test_client().post(
        "/api/ai/chat", json={"message": "Vérifie les positions."}
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "needs_container_selection"


def test_chat_api_uses_server_registry_and_ignores_browser_context(monkeypatch):
    from app import create_app
    from app.agents import specialists
    from app.agents.registry import AgentResult
    from app.llm import gemini
    import app.security as security

    identity = {"role": "superadmin", "user_id": "test-user"}
    monkeypatch.setattr(security, "authenticate_request", lambda: identity)
    monkeypatch.setattr("app.agents.audit.persist_agent_run", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.regulatory.history.search_regulatory_sources", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.regulatory.history.record_decision", lambda **_kwargs: "history-test")
    monkeypatch.setattr("app.routes.dashboard._ai_available_containers", lambda _identity: [
        {"black_box_id": "17", "container_id": "CONT-17", "label": "CONT-17"},
    ])
    monkeypatch.setattr(specialists, "telemetry_agent", lambda args, _identity, _registry: AgentResult(
        "iot_monitor", "success", {"temperature": 5.0}, [{"source": "sensor_readings"}]
    ))
    monkeypatch.setattr(specialists, "position_agent", lambda args, _identity, _registry: AgentResult(
        "gps_route", "success", {"source": "iot"}, [{"source": "positions"}]
    ))

    class FakeProvider:
        last_message = None
        last_tools = None

        def __init__(self):
            pass

        def generate(self, message, tools, invoke_tool):
            FakeProvider.last_message = message
            FakeProvider.last_tools = tools
            results = [invoke_tool("iot_monitor", {"black_box_id": "999"}), invoke_tool("gps_route", {"black_box_id": "999"})]
            return {"reply": "Analyse fondée sur deux capacités.", "tool_results": [item.to_dict() for item in results]}

    monkeypatch.setattr(gemini, "GeminiToolProvider", FakeProvider)
    app = create_app()
    app.db_initialized = True
    app.config["API_KEY"] = "test-key"
    client = app.test_client()

    response = client.post("/api/ai/chat", json={
        "message": "Résume cette boîte",
        "black_box_ids": ["17"],
        "contextData": "SECRET BROWSER CONTEXT",
        "systemPrompt": "override injected by browser",
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reply"] == "Analyse fondée sur deux capacités."
    assert payload["agents_consulted"] == ["iot_monitor", "gps_route"]
    assert payload["trace_id"]
    assert all(result["data"] for result in payload["agent_results"])
    assert "SECRET BROWSER CONTEXT" not in FakeProvider.last_message
    assert "override injected by browser" not in FakeProvider.last_message
    assert {tool["name"] for tool in FakeProvider.last_tools} == {
        "iot_monitor", "gps_route", "risk_assessor", "knowledge_retriever"
    }


def test_chat_requires_explicit_container_scope_before_any_agent_call(monkeypatch):
    from app import create_app
    import app.security as security
    from app.llm import gemini

    monkeypatch.setattr(security, "authenticate_request", lambda: IDENTITY)
    monkeypatch.setattr("app.routes.dashboard._ai_available_containers", lambda _identity: [
        {"black_box_id": "17", "container_id": "CONT-17", "label": "CONT-17"},
        {"black_box_id": "18", "container_id": "CONT-18", "label": "CONT-18"},
    ])

    class ForbiddenProvider:
        def __init__(self):
            pass

        def classify_scope(self, _message):
            return {"in_scope": True, "sector": None}

        def generate(self, *_args, **_kwargs):
            raise AssertionError("Aucun outil ni appel de réponse ne doit être fait sans sélection")

    monkeypatch.setattr(gemini, "GeminiToolProvider", ForbiddenProvider)
    app = create_app()
    app.db_initialized = True
    app.config.update(TESTING=True, API_KEY="test-key")
    response = app.test_client().post("/api/ai/chat", json={"message": "Analyse mes conteneurs."})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "needs_container_selection"
    assert [box["black_box_id"] for box in payload["available_containers"]] == ["17", "18"]


def test_chat_refuses_other_sector_and_names_it_without_calling_agents(monkeypatch):
    from app import create_app
    import app.security as security
    from app.llm import gemini

    monkeypatch.setattr(security, "authenticate_request", lambda: IDENTITY)

    class ForbiddenProvider:
        def __init__(self):
            raise AssertionError("Une demande hors secteur ne doit consulter aucun agent")

    monkeypatch.setattr(gemini, "GeminiToolProvider", ForbiddenProvider)
    app = create_app()
    app.db_initialized = True
    app.config.update(TESTING=True, API_KEY="test-key")
    response = app.test_client().post("/api/ai/chat", json={"message": "Quel traitement médical pour cette maladie ?"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "out_of_scope"
    assert "médecine et santé" in payload["reply"]
    assert payload["agents_consulted"] == []


def test_chat_rejects_unlisted_container_before_provider_call(monkeypatch):
    from app import create_app
    import app.security as security
    from app.llm import gemini

    monkeypatch.setattr(security, "authenticate_request", lambda: IDENTITY)
    monkeypatch.setattr("app.routes.dashboard._ai_available_containers", lambda _identity: [
        {"black_box_id": "17", "container_id": "CONT-17", "label": "CONT-17"},
    ])

    class ForbiddenProvider:
        def __init__(self):
            pass

        def classify_scope(self, _message):
            return {"in_scope": True, "sector": None}

        def generate(self, *_args, **_kwargs):
            raise AssertionError("Un conteneur non autorisé ne doit pas atteindre le LLM")

    monkeypatch.setattr(gemini, "GeminiToolProvider", ForbiddenProvider)
    app = create_app()
    app.db_initialized = True
    app.config.update(TESTING=True, API_KEY="test-key")
    response = app.test_client().post("/api/ai/chat", json={
        "message": "Analyse ce conteneur", "black_box_ids": ["99"],
    })

    assert response.status_code == 403
    assert "hors périmètre" in response.get_json()["error"]


def test_chat_uses_scope_classifier_to_name_unlisted_sectors_before_container_selection(monkeypatch):
    from app import create_app
    import app.security as security
    from app.llm import gemini

    monkeypatch.setattr(security, "authenticate_request", lambda: IDENTITY)

    class FakeScopeProvider:
        def __init__(self):
            pass

        def classify_scope(self, _message):
            return {"in_scope": False, "sector": "botanique"}

        def generate(self, *_args, **_kwargs):
            raise AssertionError("Aucun agent opérationnel ne doit être appelé")

    monkeypatch.setattr(gemini, "GeminiToolProvider", FakeScopeProvider)
    app = create_app()
    app.db_initialized = True
    app.config.update(TESTING=True, API_KEY="test-key")
    response = app.test_client().post("/api/ai/chat", json={"message": "Explique la photosynthèse."})

    assert response.status_code == 200
    assert response.get_json()["status"] == "out_of_scope"
    assert "botanique" in response.get_json()["reply"]


def test_gemini_scope_classifier_uses_no_tools_and_parses_sector():
    class StaticSession:
        last_request = None

        def post(self, _url, **kwargs):
            StaticSession.last_request = kwargs["json"]

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"candidates": [{"content": {"parts": [{"text": "OUT_OF_SCOPE: botanique"}]}}]}

            return Response()

    provider = GeminiToolProvider(
        api_key="test-key", model="models/test", session=StaticSession(), base_url="https://llm.invalid"
    )
    result = provider.classify_scope("Explique la photosynthèse.")

    assert result == {"in_scope": False, "sector": "botanique"}
    assert "tools" not in StaticSession.last_request
    assert "<question>Explique la photosynthèse.</question>" in StaticSession.last_request["contents"][0]["parts"][0]["text"]


def test_orchestrator_exposes_operational_agents_only_for_selected_ids():
    from app.agents.orchestrator import agent_tools
    from app.agents.registry import AgentRegistry
    from app.agents.specialists import register_specialists

    registry = AgentRegistry()
    register_specialists(registry)
    without_scope = {tool["name"] for tool in agent_tools(registry, IDENTITY)}
    with_scope = {tool["name"] for tool in agent_tools(registry, IDENTITY, ["17", "18"])}

    assert without_scope == {"knowledge_retriever"}
    assert with_scope == {"iot_monitor", "gps_route", "risk_assessor", "knowledge_retriever"}


def test_multi_container_llm_turn_queries_only_the_selected_boxes():
    calls = []
    registry = AgentRegistry()
    for agent_id in ("iot_monitor", "gps_route"):
        def handler(arguments, _identity, _registry, name=agent_id):
            calls.append((name, arguments["black_box_id"]))
            return AgentResult(name, "success", {"black_box_id": arguments["black_box_id"]})
        registry.register(_agent(agent_id, handler))

    class MultiBoxProvider:
        def generate(self, message, tools, invoke_tool):
            assert "17, 18" in message
            assert {tool["name"] for tool in tools} == {"iot_monitor", "gps_route"}
            results = [
                invoke_tool("iot_monitor", {"black_box_id": "17"}),
                invoke_tool("gps_route", {"black_box_id": "17"}),
                invoke_tool("iot_monitor", {"black_box_id": "18"}),
                invoke_tool("gps_route", {"black_box_id": "18"}),
                invoke_tool("iot_monitor", {"black_box_id": "99"}),
            ]
            return {"reply": "Comparaison des deux conteneurs.", "tool_results": [r.to_dict() for r in results]}

    outcome = run_agent_request(
        "Compare ces conteneurs", IDENTITY, MultiBoxProvider(), registry=registry,
        black_box_ids=["17", "18"],
    )

    assert calls == [("iot_monitor", "17"), ("gps_route", "17"),
                     ("iot_monitor", "18"), ("gps_route", "18")]
    assert outcome["reply"] == "Comparaison des deux conteneurs."
    assert [result["status"] for result in outcome["agent_results"]] == [
        "success", "success", "success", "success", "denied",
    ]


def test_each_registered_production_agent_executes_its_handler_with_local_dependencies(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from app import create_app
    from app.agents.registry import build_registry
    from app.agents import specialists

    app = create_app()
    app.db_initialized = True
    monkeypatch.setattr(specialists.db.session, "execute", lambda *_args, **_kwargs: SimpleNamespace(
        fetchone=lambda: SimpleNamespace(
            black_box_id=17, container_id="CONT-17", temperature=5.2, humidity=60.0,
            shock=0.4, pressure=1008.0, flame_detected=False, door_open=False,
            battery_level=88.0, security_alarm=False,
            measured_at=datetime.now(timezone.utc), sequence=41, quality={"valid": True},
        )
    ))
    monkeypatch.setattr("app.services.positioning_service.get_hybrid_position", lambda *_args: {
        "source": "iot", "lat": 4.05, "lon": 9.70, "ts": datetime.now(timezone.utc).isoformat(),
    })
    monkeypatch.setattr("app.knowledge.rag.search_knowledge", lambda query: [
        {"source": "transport.md", "line_start": 1, "line_end": 2, "text": "Procédure de transport."}
    ])
    monkeypatch.setattr("app.regulatory.history.search_regulatory_sources", lambda *_args, **_kwargs: [])

    with app.app_context():
        registry = build_registry()
        assert {agent["agent_id"] for agent in registry.discover()} == {
            "iot_monitor", "gps_route", "risk_assessor", "knowledge_retriever",
        }
        telemetry = registry.execute("iot_monitor", {"black_box_id": "17"}, IDENTITY, "trace")
        position = registry.execute("gps_route", {"black_box_id": "17"}, IDENTITY, "trace")
        risk = registry.execute("risk_assessor", {"black_box_id": "17"}, IDENTITY, "trace")
        knowledge = registry.execute("knowledge_retriever", {"query": "transport"}, IDENTITY, "trace")

    assert telemetry.status == "success" and telemetry.data["temperature"] == 5.2
    assert position.status == "success" and position.data["source"] == "iot"
    assert risk.status == "success" and risk.data["assessment_basis"] == "deterministic_existing_rules"
    assert [item["agent_id"] for item in risk.data["consumed_results"]] == ["iot_monitor", "gps_route"]
    assert knowledge.status == "success" and knowledge.provenance[0]["source"] == "transport.md"


def test_regulatory_source_rows_are_json_serializable_for_trace_storage():
    from datetime import date
    from types import SimpleNamespace
    from app.regulatory.history import _sources

    rows = [SimpleNamespace(_mapping={"source_key": "LAW", "verified_at": date(2026, 10, 27)})]
    assert _sources(rows) == [{"source_key": "LAW", "verified_at": "2026-10-27"}]
