from typing import Dict, List

from app.schemas import AgroZone, CropRecommendation, ParcelInput


ZONE_CATALOG = {
    AgroZone.HIGHLAND_HUMID: {
        "rent": ["cafe", "cacao"],
        "food": ["frijol_sombra", "platano", "malanga"],
    },
    AgroZone.DRY_CORRIDOR: {
        "rent": ["ajonjoli", "cafe_resiliente"],
        "food": ["sorgo", "frijol_caupi", "maiz_ciclo_corto"],
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "rent": ["cacao", "platano_comercial"],
        "food": ["yuca", "frijol_humedo", "quequisque"],
    },
    AgroZone.TRANSITION: {
        "rent": ["cafe", "cacao"],
        "food": ["frijol", "maiz", "sorgo"],
    },
}


def _slope_score(slope_percent: float) -> float:
    if slope_percent <= 12:
        return 1.0
    if slope_percent <= 20:
        return 0.7
    if slope_percent <= 30:
        return 0.4
    return 0.1


def _moisture_score(soil_moisture: float, seasonal_forecast: str) -> float:
    modifier = {"dry": -0.1, "normal": 0.0, "wet": 0.1}.get(seasonal_forecast, 0.0)
    adjusted = max(0.0, min(1.0, soil_moisture + modifier))
    return adjusted


def _shade_score(shade_index: float, agro_zone: AgroZone) -> float:
    if agro_zone == AgroZone.HIGHLAND_HUMID:
        optimal_min, optimal_max = 0.45, 0.75
    elif agro_zone == AgroZone.DRY_CORRIDOR:
        optimal_min, optimal_max = 0.25, 0.55
    else:
        optimal_min, optimal_max = 0.35, 0.7

    if optimal_min <= shade_index <= optimal_max:
        return 1.0
    if shade_index < optimal_min:
        return max(0.0, 1.0 - (optimal_min - shade_index) * 2)
    return max(0.0, 1.0 - (shade_index - optimal_max) * 2)


def _stress_score(stress_index: float) -> float:
    return 1.0 - stress_index


def _traffic_light(global_score: float) -> str:
    if global_score >= 0.7:
        return "verde"
    if global_score >= 0.45:
        return "amarillo"
    return "rojo"


def recommend(parcel: ParcelInput) -> Dict:
    slope = _slope_score(parcel.slope_percent)
    moisture = _moisture_score(parcel.soil_moisture, parcel.seasonal_forecast)
    shade = _shade_score(parcel.shade_index, parcel.agro_zone)
    stress = _stress_score(parcel.stress_index)

    global_score = round((0.25 * slope + 0.35 * moisture + 0.2 * shade + 0.2 * stress), 3)
    traffic = _traffic_light(global_score)

    catalog = ZONE_CATALOG[parcel.agro_zone]
    rent_crop = catalog["rent"][0]
    food_crop = catalog["food"][0]

    if parcel.seasonal_forecast == "dry" and "sorgo" in catalog["food"]:
        food_crop = "sorgo"
    elif parcel.seasonal_forecast == "wet" and "frijol_humedo" in catalog["food"]:
        food_crop = "frijol_humedo"

    window = "sembrar_ahora" if traffic == "verde" else "esperar_7_dias" if traffic == "amarillo" else "no_sembrar"

    reason = (
        f"Zona {parcel.agro_zone.value}; humedad={moisture:.2f}, pendiente={slope:.2f}, "
        f"sombra={shade:.2f}, estres={stress:.2f}"
    )

    recommendations: List[CropRecommendation] = [
        CropRecommendation(
            rent_crop=rent_crop,
            food_crop=food_crop,
            confidence=global_score,
            reason=reason,
        )
    ]

    advisory = (
        f"Parcela {parcel.parcel_id}: {traffic.upper()}. "
        f"Recomendacion: combinar {rent_crop} + {food_crop}. "
        f"Accion: {window.replace('_', ' ')}."
    )

    return {
        "parcel_id": parcel.parcel_id,
        "traffic_light": traffic,
        "recommended_window": window,
        "recommendations": recommendations,
        "advisory_text": advisory,
        "debug_scores": {
            "global": global_score,
            "slope": slope,
            "moisture": moisture,
            "shade": shade,
            "stress": stress,
        },
    }
