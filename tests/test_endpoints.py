from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_recommendations_endpoint() -> None:
    response = client.post(
        "/v1/recommendations",
        json={
            "parcel_id": "PAR-001",
            "municipality": "Jinotega",
            "department": "Jinotega",
            "agro_zone": "highland_humid",
            "slope_percent": 14,
            "soil_moisture": 0.62,
            "shade_index": 0.57,
            "stress_index": 0.22,
            "seasonal_forecast": "normal",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["parcel_id"] == "PAR-001"
    assert payload["traffic_light"] in {"verde", "amarillo", "rojo"}
    assert len(payload["recommendations"]) == 1


def test_auto_recommendations_endpoint_requires_gee() -> None:
    def _raise_gee_error(**kwargs: object) -> dict:
        raise RuntimeError(
            "GEE deshabilitado. Define GEE_ENABLED=true y autentica Earth Engine."
        )

    original_get_parcel_features = main_module.gee_client.get_parcel_features
    original_c3s_forecast = main_module.c3s_client.get_seasonal_forecast
    main_module.gee_client.get_parcel_features = _raise_gee_error
    main_module.c3s_client.get_seasonal_forecast = lambda **kwargs: "normal"
    try:
        response = client.post(
            "/v1/recommendations/auto",
            json={
                "parcel_id": "PAR-AUTO-1",
                "municipality": "Jinotega",
                "department": "Jinotega",
                "agro_zone": "highland_humid",
                "lat": 13.1,
                "lon": -86.0,
                "seasonal_forecast": "normal",
            },
        )
    finally:
        main_module.gee_client.get_parcel_features = original_get_parcel_features
        main_module.c3s_client.get_seasonal_forecast = original_c3s_forecast

    assert response.status_code == 503
    payload = response.json()
    assert "GEE" in payload["detail"]


def test_auto_recommendations_endpoint_with_mocked_gee_and_c3s() -> None:
    def _fake_features(**kwargs: object) -> dict:
        return {
            "soil_moisture": 0.6,
            "shade_index": 0.55,
            "stress_index": 0.25,
            "slope_percent": 12.0,
            "source": "gee",
            "lat": kwargs["lat"],
            "lon": kwargs["lon"],
        }

    def _fake_c3s(**kwargs: object) -> str:
        return "wet"

    original_get_parcel_features = main_module.gee_client.get_parcel_features
    original_c3s_forecast = main_module.c3s_client.get_seasonal_forecast
    main_module.gee_client.get_parcel_features = _fake_features
    main_module.c3s_client.get_seasonal_forecast = _fake_c3s
    try:
        response = client.post(
            "/v1/recommendations/auto",
            json={
                "parcel_id": "PAR-AUTO-2",
                "municipality": "Jinotega",
                "department": "Jinotega",
                "agro_zone": "highland_humid",
                "lat": 13.2,
                "lon": -85.9,
                "seasonal_forecast": "normal",
            },
        )
    finally:
        main_module.gee_client.get_parcel_features = original_get_parcel_features
        main_module.c3s_client.get_seasonal_forecast = original_c3s_forecast

    assert response.status_code == 200
    payload = response.json()
    assert payload["parcel_id"] == "PAR-AUTO-2"
    assert payload["data_source"] == "gee"
    assert payload["debug_scores"]["seasonal_source"] == "c3s"
    assert payload["debug_scores"]["seasonal_forecast_used"] == "wet"
    assert "debug_scores" in payload


def test_auto_recommendations_without_seasonal_uses_c3s_when_mocked() -> None:
    def _fake_features(**kwargs: object) -> dict:
        return {
            "soil_moisture": 0.58,
            "shade_index": 0.52,
            "stress_index": 0.28,
            "slope_percent": 10.0,
            "source": "gee",
            "lat": kwargs["lat"],
            "lon": kwargs["lon"],
        }

    def _fake_c3s(**kwargs: object) -> str:
        return "wet"

    original_get_parcel_features = main_module.gee_client.get_parcel_features
    original_c3s_forecast = main_module.c3s_client.get_seasonal_forecast
    main_module.gee_client.get_parcel_features = _fake_features
    main_module.c3s_client.get_seasonal_forecast = _fake_c3s
    try:
        response = client.post(
            "/v1/recommendations/auto",
            json={
                "parcel_id": "PAR-AUTO-3",
                "municipality": "Jinotega",
                "department": "Jinotega",
                "agro_zone": "highland_humid",
                "lat": 13.3,
                "lon": -85.8,
            },
        )
    finally:
        main_module.gee_client.get_parcel_features = original_get_parcel_features
        main_module.c3s_client.get_seasonal_forecast = original_c3s_forecast

    assert response.status_code == 200
    payload = response.json()
    assert payload["parcel_id"] == "PAR-AUTO-3"
    assert payload["debug_scores"]["seasonal_source"] == "c3s"
    assert payload["debug_scores"]["seasonal_forecast_used"] == "wet"
