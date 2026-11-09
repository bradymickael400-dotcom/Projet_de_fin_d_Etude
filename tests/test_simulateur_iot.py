import json

import simulateur_iot


def test_automatic_sequence_reserves_a_new_range_for_each_run(tmp_path, monkeypatch):
    state_path = tmp_path / "simulator-sequences.json"
    monkeypatch.setattr(simulateur_iot.time, "time_ns", lambda: 1_800_000_000_000_000_000)

    first = simulateur_iot._reserve_start_sequence("ARGOS-DEMO", state_path)
    second = simulateur_iot._reserve_start_sequence("ARGOS-DEMO", state_path)

    assert first == 1_800_000_000_000_000
    assert second == first + simulateur_iot.DURATION_SECONDS
    assert json.loads(state_path.read_text()) == {
        "ARGOS-DEMO": second + simulateur_iot.DURATION_SECONDS - 1,
    }


def test_route_restarts_at_douala_for_every_scenario_run():
    latitude, longitude, _heading = simulateur_iot._route_point(0)

    assert (latitude, longitude) == simulateur_iot.ROUTE[0]


def test_explicit_sequence_must_not_overlap_a_reserved_run(tmp_path):
    state_path = tmp_path / "simulator-sequences.json"
    first = simulateur_iot._reserve_start_sequence("ARGOS-DEMO", state_path, requested_start=10)

    try:
        simulateur_iot._reserve_start_sequence("ARGOS-DEMO", state_path, requested_start=10)
    except ValueError as error:
        assert "pas supérieur à la dernière plage réservée" in str(error)
    else:
        raise AssertionError("Une plage déjà réservée ne doit pas être réutilisée")

    assert first == 10
