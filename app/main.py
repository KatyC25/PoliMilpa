from fastapi import FastAPI

from app.config import settings
from app.schemas import AutoParcelInput, ParcelInput, RecommendationResponse
from app.services.gee_client import GEEClient
from app.services.ml_service import MLService
from app.services.rules_engine import recommend

app = FastAPI(title=settings.app_name, version=settings.app_version)
gee_client = GEEClient()
ml_service = MLService()


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.post("/v1/recommendations", response_model=RecommendationResponse)
def generate_recommendation(payload: ParcelInput) -> RecommendationResponse:
    result = recommend(payload)
    return RecommendationResponse(**result)


@app.post("/v1/recommendations/auto", response_model=RecommendationResponse)
def generate_auto_recommendation(payload: AutoParcelInput) -> RecommendationResponse:
    features = gee_client.get_parcel_features(
        lat=payload.lat,
        lon=payload.lon,
        agro_zone=payload.agro_zone,
        seasonal_forecast=payload.seasonal_forecast,
    )

    rules_payload = ParcelInput(
        parcel_id=payload.parcel_id,
        municipality=payload.municipality,
        department=payload.department,
        agro_zone=payload.agro_zone,
        slope_percent=features["slope_percent"],
        soil_moisture=features["soil_moisture"],
        shade_index=features["shade_index"],
        stress_index=features["stress_index"],
        seasonal_forecast=payload.seasonal_forecast,
    )

    result = recommend(rules_payload)
    adjustment = ml_service.predict_adjustment(result["debug_scores"])
    result["debug_scores"]["confidence_delta"] = adjustment["confidence_delta"]
    result["debug_scores"]["model_version"] = adjustment["model_version"]
    result["data_source"] = features.get("source", "unknown")

    return RecommendationResponse(**result)
