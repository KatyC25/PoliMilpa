import unicodedata
from typing import Dict, List, Optional, Tuple

from app.schemas import AgroZone, CropRecommendation, ParcelInput


ZONE_CATALOG = {
    AgroZone.HIGHLAND_HUMID: {
        "macro_region": "centro_norte",
        "rent": ["cafe", "cacao"],
        "food": ["maiz", "frijol", "ayote", "platano"],
    },
    AgroZone.DRY_CORRIDOR: {
        "macro_region": "pacifico_seco",
        "rent": ["ajonjoli", "cafe_resiliente"],
        "food": ["sorgo", "maiz", "frijol_caupi"],
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "macro_region": "caribe_humedo",
        "rent": ["cacao", "platano_comercial"],
        "food": ["yuca", "quequisque", "malanga", "frijol_humedo"],
    },
    AgroZone.TRANSITION: {
        "macro_region": "transicion",
        "rent": ["cafe", "cacao"],
        "food": ["frijol", "maiz", "sorgo"],
    },
}

DEPARTMENT_ZONE_HINTS = {
    AgroZone.DRY_CORRIDOR: {
        "chinandega",
        "leon",
        "managua",
        "masaya",
        "rivas",
        "esteli",
        "madriz",
        "nueva segovia",
    },
    AgroZone.HIGHLAND_HUMID: {
        "jinotega",
        "matagalpa",
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "raccn",
        "raccs",
        "rio san juan",
    },
    AgroZone.TRANSITION: {
        "carazo",
        "boaco",
        "chontales",
    },
}

MUNICIPALITY_ZONE_HINTS = {
    AgroZone.DRY_CORRIDOR: {
        "chinandega",
        "el viejo",
        "leon",
        "nagarote",
        "la paz centro",
        "managua",
        "tipitapa",
        "masaya",
        "nindiri",
        "rivas",
        "belen",
        "esteli",
        "somoto",
        "ocotal",
    },
    AgroZone.HIGHLAND_HUMID: {
        "jinotega",
        "san rafael del norte",
        "matagalpa",
        "la dahlia",
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "bluefields",
        "bilwi",
        "puerto cabezas",
        "siuna",
        "waspan",
        "el rama",
        "san carlos",
    },
    AgroZone.TRANSITION: {
        "jinotepe",
        "diriamba",
        "mombacho",
        "boaco",
        "camoapa",
        "juigalpa",
    },
}


def _normalize_place(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _normalize_department(department: str) -> str:
    return _normalize_place(department)


def _normalize_municipality(municipality: str) -> str:
    return _normalize_place(municipality)


def _infer_zone_from_department(department: str) -> Optional[AgroZone]:
    dep = _normalize_department(department)
    for zone, departments in DEPARTMENT_ZONE_HINTS.items():
        if dep in departments:
            return zone
    return None


def _infer_zone_from_municipality(municipality: str) -> Optional[AgroZone]:
    muni = _normalize_municipality(municipality)
    for zone, municipalities in MUNICIPALITY_ZONE_HINTS.items():
        if muni in municipalities:
            return zone
    return None


def _resolve_zone(parcel: ParcelInput) -> Tuple[AgroZone, str]:
    inferred_zone_by_muni = _infer_zone_from_municipality(parcel.municipality)
    if inferred_zone_by_muni is not None:
        if inferred_zone_by_muni == parcel.agro_zone:
            return parcel.agro_zone, "zone_match_municipality"
        return inferred_zone_by_muni, "zone_adjusted_by_municipality"

    inferred_zone = _infer_zone_from_department(parcel.department)
    if inferred_zone is None:
        return parcel.agro_zone, "unknown_department_and_municipality"
    if inferred_zone == parcel.agro_zone:
        return parcel.agro_zone, "zone_match_department"
    return inferred_zone, "zone_adjusted_by_department"


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
    effective_zone, zone_validation = _resolve_zone(parcel)

    slope = _slope_score(parcel.slope_percent)
    moisture = _moisture_score(parcel.soil_moisture, parcel.seasonal_forecast)
    shade = _shade_score(parcel.shade_index, effective_zone)
    stress = _stress_score(parcel.stress_index)

    global_score = round(
        (0.25 * slope + 0.35 * moisture + 0.2 * shade + 0.2 * stress), 3
    )
    traffic = _traffic_light(global_score)

    catalog = ZONE_CATALOG[effective_zone]
    rent_crop = catalog["rent"][0]
    food_crop = catalog["food"][0]

    if parcel.seasonal_forecast == "dry" and "sorgo" in catalog["food"]:
        food_crop = "sorgo"
    elif parcel.seasonal_forecast == "wet" and "frijol_humedo" in catalog["food"]:
        food_crop = "frijol_humedo"

    window = (
        "sembrar_ahora"
        if traffic == "verde"
        else "esperar_7_dias"
        if traffic == "amarillo"
        else "no_sembrar"
    )

    reason = (
        f"Zona {effective_zone.value}; humedad={moisture:.2f}, pendiente={slope:.2f}, "
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

    if zone_validation == "zone_adjusted_by_municipality":
        advisory += (
            f" Nota: la zona se ajusto automaticamente segun el municipio "
            f"({parcel.municipality})."
        )
    elif zone_validation == "zone_adjusted_by_department":
        advisory += (
            f" Nota: la zona se ajusto automaticamente segun el departamento "
            f"({parcel.department})."
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
            "zone_validation": zone_validation,
            "zone_used": effective_zone.value,
        },
    }
