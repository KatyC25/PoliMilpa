from app.schemas import AgroZone, ParcelInput
from app.services.rules_engine import recommend


def test_recommendation_green_for_good_conditions() -> None:
    payload = ParcelInput(
        parcel_id="PAR-TEST-1",
        municipality="Jinotega",
        department="Jinotega",
        agro_zone=AgroZone.HIGHLAND_HUMID,
        slope_percent=10,
        soil_moisture=0.7,
        shade_index=0.6,
        stress_index=0.1,
        seasonal_forecast="normal",
    )

    result = recommend(payload)

    assert result["traffic_light"] == "verde"
    assert result["recommended_window"] == "sembrar_ahora"
    assert result["recommendations"][0].rent_crop == "cafe"


def test_recommendation_red_for_bad_conditions() -> None:
    payload = ParcelInput(
        parcel_id="PAR-TEST-2",
        municipality="Esteli",
        department="Esteli",
        agro_zone=AgroZone.DRY_CORRIDOR,
        slope_percent=40,
        soil_moisture=0.1,
        shade_index=0.0,
        stress_index=0.9,
        seasonal_forecast="dry",
    )

    result = recommend(payload)

    assert result["traffic_light"] == "rojo"
    assert result["recommended_window"] == "no_sembrar"


def test_dry_forecast_prioritizes_sorghum_when_available() -> None:
    payload = ParcelInput(
        parcel_id="PAR-TEST-3",
        municipality="Leon",
        department="Leon",
        agro_zone=AgroZone.DRY_CORRIDOR,
        slope_percent=15,
        soil_moisture=0.4,
        shade_index=0.4,
        stress_index=0.3,
        seasonal_forecast="dry",
    )

    result = recommend(payload)

    assert result["recommendations"][0].food_crop == "sorgo"


def test_department_zone_adjustment_when_input_zone_conflicts() -> None:
    payload = ParcelInput(
        parcel_id="PAR-TEST-4",
        municipality="Bluefields",
        department="RACCS",
        agro_zone=AgroZone.DRY_CORRIDOR,
        slope_percent=11,
        soil_moisture=0.58,
        shade_index=0.62,
        stress_index=0.2,
        seasonal_forecast="wet",
    )

    result = recommend(payload)

    assert result["debug_scores"]["zone_validation"] == "zone_adjusted_by_municipality"
    assert result["debug_scores"]["zone_used"] == AgroZone.SUBHUMID_CARIBBEAN.value
    assert "zona se ajusto automaticamente" in result["advisory_text"].lower()


def test_unknown_department_keeps_input_zone() -> None:
    payload = ParcelInput(
        parcel_id="PAR-TEST-5",
        municipality="N/A",
        department="Departamento Inventado",
        agro_zone=AgroZone.TRANSITION,
        slope_percent=16,
        soil_moisture=0.5,
        shade_index=0.5,
        stress_index=0.3,
        seasonal_forecast="normal",
    )

    result = recommend(payload)

    assert (
        result["debug_scores"]["zone_validation"]
        == "unknown_department_and_municipality"
    )
    assert result["debug_scores"]["zone_used"] == AgroZone.TRANSITION.value


def test_municipality_has_priority_over_department_when_they_conflict() -> None:
    payload = ParcelInput(
        parcel_id="PAR-TEST-6",
        municipality="Diriamba",
        department="RACCS",
        agro_zone=AgroZone.SUBHUMID_CARIBBEAN,
        slope_percent=14,
        soil_moisture=0.55,
        shade_index=0.5,
        stress_index=0.2,
        seasonal_forecast="normal",
    )

    result = recommend(payload)

    assert result["debug_scores"]["zone_validation"] == "zone_adjusted_by_municipality"
    assert result["debug_scores"]["zone_used"] == AgroZone.TRANSITION.value
