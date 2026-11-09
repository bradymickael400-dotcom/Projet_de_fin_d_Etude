from datetime import datetime, timezone

import pytest

from app.services.terrestrial_simulation_service import (
    SCENARIOS,
    build_simulated_telemetry_contract,
    build_scenario_tick,
    fetch_osrm_route,
    offset_laterally,
    position_on_route,
)


ROUTE = {
    "geometry": {"type": "LineString", "coordinates": [[9.7, 4.0], [9.8, 4.0], [9.9, 4.1]]},
    "distance_m": 300_000,
    "duration_s": 36_000,
}
STARTED = datetime(2026, 10, 29, tzinfo=timezone.utc)


def test_only_the_two_declared_central_africa_scenarios_are_available():
    assert tuple(SCENARIOS) == ("douala_ndjamena", "kribi_bertoua")


def test_route_interpolation_returns_valid_position_and_heading():
    lat, lon, heading = position_on_route(ROUTE["geometry"], 0.5)
    assert 4.0 <= lat <= 4.1
    assert 9.7 <= lon <= 9.9
    assert 0 <= heading < 360


def test_lateral_offset_moves_simulated_position_from_reference_route():
    lat, lon, _ = position_on_route(ROUTE["geometry"], 0.5)
    offset = offset_laterally(lat, lon, 90, 1_200)
    assert offset != (lat, lon)


def test_stable_scenario_has_no_invented_operational_events():
    sample = build_scenario_tick(session_uid="demo", scenario_code="douala_ndjamena",
                                 route=ROUTE, elapsed_wall_s=300, time_scale=5,
                                 sequence=1, started_at=STARTED)
    assert sample["active_events"] == []
    assert sample["provenance"]["dataOrigin"] == "SYNTHETIC"
    assert sample["batch_uid"]
    assert sample["speed_kmh"] > 0
    assert sample["eta_current_at"]


def test_generated_payload_matches_iot_contract_and_stays_marked_synthetic():
    sample = build_scenario_tick(session_uid="demo-session", scenario_code="douala_ndjamena",
                                 route=ROUTE, elapsed_wall_s=30, time_scale=5,
                                 sequence=1, started_at=STARTED)
    payload = build_simulated_telemetry_contract(sample, 17, "CONT-17")
    assert payload["type"] == "telemetry"
    assert payload["blackBoxId"] == 17
    assert payload["containerId"] == "CONT-17"
    assert payload["quality"]["dataOrigin"] == "SYNTHETIC"
    assert payload["deviceUid"].startswith("ARGOS-SIM-")


def test_kribi_scenario_labels_deviation_and_shock_as_simulated():
    sample = build_scenario_tick(session_uid="demo", scenario_code="kribi_bertoua",
                                 route=ROUTE, elapsed_wall_s=120, time_scale=5,
                                 sequence=1, started_at=STARTED, shock_threshold_g=4.0)
    event_types = {event["event_type"] for event in sample["active_events"]}
    assert "route_deviation_simulated" in event_types
    assert "shock_episode_simulated" in event_types
    assert sample["rule_assessments"]["route_deviation_definition"]["simulated_offset_m"] == 1_200


def test_immobilization_sets_zero_speed_and_increases_eta():
    sample = build_scenario_tick(session_uid="demo", scenario_code="kribi_bertoua",
                                 route=ROUTE, elapsed_wall_s=40 * 60, time_scale=5,
                                 sequence=40, started_at=STARTED)
    assert sample["vehicle_state"] == "stopped"
    assert sample["speed_kmh"] == 0
    assert sample["stopped_seconds"] > 0
    assert sample["eta_delay_seconds"] > 0


def test_osrm_invalid_json_shape_returns_controlled_error(monkeypatch):
    import app.services.terrestrial_simulation_service as service

    places = iter(({"latitude": 4.0, "longitude": 9.7},
                   {"latitude": 4.1, "longitude": 9.9}))
    monkeypatch.setattr(service, "_geocode", lambda _query: next(places))

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return []

    monkeypatch.setattr(service.requests, "get", lambda *_args, **_kwargs: Response())
    with pytest.raises(RuntimeError, match="réponse invalide"):
        fetch_osrm_route("douala_ndjamena")


def test_scenario_event_timing_is_configurable():
    sample = build_scenario_tick(
        session_uid="demo", scenario_code="kribi_bertoua", route=ROUTE,
        elapsed_wall_s=90, time_scale=1, sequence=2, started_at=STARTED,
        scenario_config={"events": {"immobilization_minutes": [1, 4]}},
    )
    assert sample["vehicle_state"] == "stopped"
    assert sample["stopped_seconds"] == 30


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/api/terrestrial-simulations", None),
    ("post", "/api/terrestrial-simulations", {"mode": "SIMULATION"}),
])
def test_non_manager_cannot_read_or_start_terrestrial_sessions(monkeypatch, method, path, payload):
    from app import create_app
    import app.security as security
    from app.routes import terrestrial_simulations as routes

    monkeypatch.setattr(security, "authenticate_request", lambda: {
        "role": "driver", "user_id": "driver-1"
    })
    monkeypatch.setattr(routes, "get_caller_identity", lambda: ("driver", "driver-1"))
    app = create_app()
    app.db_initialized = True
    client = app.test_client()
    response = getattr(client, method)(path, json=payload)
    assert response.status_code == (200 if method == "get" else 403)
