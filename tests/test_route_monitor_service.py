import pytest

from app.services.route_monitor_service import route_deviation, validate_waypoints


def test_route_deviation_score_is_zero_on_planned_corridor():
    route = [[4.0, 13.0], [4.0, 13.1]]
    result = route_deviation(4.0, 13.05, route, corridor_width_m=500)
    assert result["distance_to_route_m"] == 0
    assert result["deviation_score_percent"] == 0
    assert result["is_statistical_probability"] is False


def test_route_deviation_score_crosses_sixty_percent_outside_corridor():
    route = [[4.0, 13.0], [4.0, 13.1]]
    result = route_deviation(4.01, 13.05, route, corridor_width_m=500)
    assert result["deviation_score_percent"] >= 60


def test_gps_accuracy_reduces_route_deviation_score():
    route = [[4.0, 13.0], [4.0, 13.1]]
    precise = route_deviation(4.005, 13.05, route, corridor_width_m=500)
    uncertain = route_deviation(4.005, 13.05, route, corridor_width_m=500, accuracy_m=400)
    assert uncertain["deviation_score_percent"] < precise["deviation_score_percent"]


def test_waypoints_are_validated_and_normalized():
    assert validate_waypoints([{"latitude": 4, "longitude": 13},
                               {"latitude": 5, "longitude": 14}]) == [[4.0, 13.0], [5.0, 14.0]]
    with pytest.raises(ValueError):
        validate_waypoints([[91, 13], [4, 14]])


def test_threshold_read_refuses_actor_without_box_relationship(monkeypatch):
    from app import create_app
    import app.security as security
    from app.routes import telemetry

    monkeypatch.setattr(security, "authenticate_request", lambda: {
        "role": "client", "user_id": "client-with-no-box"
    })
    monkeypatch.setattr(telemetry, "get_caller_identity", lambda: ("client", "client-with-no-box"))
    monkeypatch.setattr(telemetry, "_authorized_box_ids", lambda *_args: [])
    app = create_app()
    app.db_initialized = True

    response = app.test_client().get("/api/config/thresholds/12")

    assert response.status_code == 403
    assert response.get_json()["error"] == "Accès refusé à cette boîte"


def test_monitoring_for_actor_without_boxes_returns_no_data(monkeypatch):
    from app import create_app
    import app.security as security
    from app.routes import telemetry

    monkeypatch.setattr(security, "authenticate_request", lambda: {
        "role": "client", "user_id": "client-with-no-box"
    })
    monkeypatch.setattr(telemetry, "get_caller_identity", lambda: ("client", "client-with-no-box"))
    monkeypatch.setattr(telemetry, "_authorized_box_ids", lambda *_args: [])

    class EmptyRows:
        def fetchall(self):
            return []

    statements = []
    monkeypatch.setattr(telemetry.db.session, "execute",
                        lambda statement, _params=None: (statements.append(str(statement)) or EmptyRows()))
    app = create_app()
    app.db_initialized = True

    response = app.test_client().get("/api/monitoring/data")

    assert response.status_code == 200
    assert response.get_json() == {"containers": [], "alerts": [], "positions": []}
    assert len(statements) == 3
    assert all("FALSE" in statement for statement in statements)
