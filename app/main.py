from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from app.config import settings
from app.schemas import AutoParcelInput, ParcelInput, RecommendationResponse
from app.services.c3s_client import C3SClient
from app.services.gee_client import GEEClient
from app.services.ml_service import MLService
from app.services.rules_engine import recommend

load_dotenv()

app = FastAPI(title=settings.app_name, version=settings.app_version)
gee_client = GEEClient()
c3s_client = C3SClient()
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
    try:
        seasonal_forecast = c3s_client.get_seasonal_forecast(
            lat=payload.lat,
            lon=payload.lon,
        )
        seasonal_source = "c3s"

        features = gee_client.get_parcel_features(
            lat=payload.lat,
            lon=payload.lon,
            agro_zone=payload.agro_zone,
            seasonal_forecast=seasonal_forecast,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    rules_payload = ParcelInput(
        parcel_id=payload.parcel_id,
        municipality=payload.municipality,
        department=payload.department,
        agro_zone=payload.agro_zone,
        slope_percent=features["slope_percent"],
        soil_moisture=features["soil_moisture"],
        shade_index=features["shade_index"],
        stress_index=features["stress_index"],
        seasonal_forecast=seasonal_forecast,
    )

    result = recommend(rules_payload)
    adjustment = ml_service.predict_adjustment(result["debug_scores"])
    result["debug_scores"]["confidence_delta"] = adjustment["confidence_delta"]
    result["debug_scores"]["model_version"] = adjustment["model_version"]
    result["debug_scores"]["seasonal_source"] = seasonal_source
    result["debug_scores"]["seasonal_forecast_used"] = seasonal_forecast
    result["debug_scores"]["c3s_dataset"] = c3s_client.dataset
    result["debug_scores"]["c3s_variable"] = c3s_client.variable
    result["debug_scores"]["c3s_leadtime_month"] = c3s_client.leadtime_month
    result["debug_scores"]["s1_dataset"] = features.get("s1_dataset", "unknown")
    result["debug_scores"]["s2_dataset"] = features.get("s2_dataset", "unknown")
    result["debug_scores"]["s2_index"] = features.get("s2_index", "unknown")
    result["debug_scores"]["dem_dataset"] = features.get("dem_dataset", "unknown")
    result["data_source"] = features.get("source", "unknown")

    return RecommendationResponse(**result)
