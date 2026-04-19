from fastapi.testclient import TestClient
from uuid import uuid4

import app.main as main_module
from app.main import app


client = TestClient(app)


def _auth_headers(username: str = "tecnico", password: str = "tecnico123") -> dict:
    login_response = client.post(
        "/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_login_and_me_endpoint() -> None:
    login_response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["username"] == "admin"
    assert me_payload["role"] == "admin"


def test_recommendations_requires_auth() -> None:
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
    assert response.status_code == 401


def test_recommendations_endpoint() -> None:
    response = client.post(
        "/v1/recommendations",
        headers=_auth_headers(),
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
            headers=_auth_headers(),
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
            headers=_auth_headers(),
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
            headers=_auth_headers(),
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


def test_farmer_crud_flow_with_admin() -> None:
    farmer_code = f"FARM-{uuid4().hex[:8]}"

    create_response = client.post(
        "/v1/farmers",
        headers=_auth_headers("admin", "admin123"),
        json={
            "farmer_code": farmer_code,
            "full_name": "Maria Lopez",
            "contact_phone": "8888-0000",
            "farm_name": "Finca El Pino",
            "municipality": "Jinotega",
            "department": "Jinotega",
            "agro_zone": "highland_humid",
            "lat": 13.12,
            "lon": -86.05,
            "technician_username": "tecnico",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    farmer_id = created["id"]
    assert created["farmer_code"] == farmer_code
    assert created["technician_username"] == "tecnico"

    get_response = client.get(
        f"/v1/farmers/{farmer_id}",
        headers=_auth_headers("admin", "admin123"),
    )
    assert get_response.status_code == 200

    update_response = client.put(
        f"/v1/farmers/{farmer_id}",
        headers=_auth_headers("admin", "admin123"),
        json={
            "contact_phone": "8888-1234",
            "farm_name": "Finca El Pino Actualizada",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["contact_phone"] == "8888-1234"

    list_response = client.get(
        "/v1/farmers",
        headers=_auth_headers("admin", "admin123"),
        params={"technician_username": "tecnico"},
    )
    assert list_response.status_code == 200
    listed_codes = {item["farmer_code"] for item in list_response.json()}
    assert farmer_code in listed_codes

    delete_response = client.delete(
        f"/v1/farmers/{farmer_id}",
        headers=_auth_headers("admin", "admin123"),
    )
    assert delete_response.status_code == 204


def test_technician_cannot_reassign_farmer_to_other_technician() -> None:
    farmer_code = f"FARM-{uuid4().hex[:8]}"

    create_response = client.post(
        "/v1/farmers",
        headers=_auth_headers("tecnico", "tecnico123"),
        json={
            "farmer_code": farmer_code,
            "full_name": "Pedro Ruiz",
            "contact_phone": "7777-0000",
            "farm_name": "Finca Las Brisas",
            "municipality": "Matagalpa",
            "department": "Matagalpa",
            "agro_zone": "highland_humid",
            "technician_username": "admin",
        },
    )
    assert create_response.status_code == 403
