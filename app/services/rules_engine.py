import unicodedata
from typing import Dict, List, Optional, Tuple

from app.schemas import AgroZone, CropRecommendation, ParcelInput


# Parámetros calibrados desde GEE (cálculo real con Sentinel-2 + DEM)
ZONE_PARAMS = {
    AgroZone.HIGHLAND_HUMID: {
        "coverage_min": 0.10,
        "coverage_max": 0.75,
        "weight_cob": 0.75,
        "weight_pen": 0.25,
        "threshold_green": 0.52,
        "threshold_red": 0.32,
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "coverage_min": 0.10,
        "coverage_max": 0.75,
        "weight_cob": 0.75,
        "weight_pen": 0.25,
        "threshold_green": 0.52,
        "threshold_red": 0.32,
    },
    AgroZone.DRY_CORRIDOR: {
        "coverage_min": 0.12,
        "coverage_max": 0.55,
        "weight_cob": 0.80,
        "weight_pen": 0.20,
        "threshold_green": 0.48,
        "threshold_red": 0.32,
    },
    AgroZone.TRANSITION: {
        "coverage_min": 0.12,
        "coverage_max": 0.55,
        "weight_cob": 0.80,
        "weight_pen": 0.20,
        "threshold_green": 0.48,
        "threshold_red": 0.32,
    },
}

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
    AgroZone.HIGHLAND_HUMID: {"jinotega", "matagalpa"},
    AgroZone.SUBHUMID_CARIBBEAN: {"raccn", "raccs", "rio san juan"},
    AgroZone.DRY_CORRIDOR: {
        "madriz", "esteli", "nueva segovia", "leon", "chinandega",
    },
    AgroZone.TRANSITION: {
        "managua", "masaya", "granada", "carazo",
        "rivas", "boaco", "chontales",
    },
}

MUNICIPALITY_ZONE_HINTS = {
    AgroZone.HIGHLAND_HUMID: {
        "jinotega", "san rafael del norte", "wiwili de jinotega",
        "matagalpa", "la dalia", "sebaco",
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "puerto cabezas", "waspan", "siuna", "bluefields",
        "el rama", "nueva guinea", "san carlos", "el castillo",
    },
    AgroZone.DRY_CORRIDOR: {
        "somoto", "palacaguina", "esteli", "condega", "ocotal",
        "jalapa", "leon", "nagarote", "la paz centro",
        "chinandega", "el viejo", "somotillo",
    },
    AgroZone.TRANSITION: {
        "managua", "tipitapa", "mateare", "masaya", "nindiri",
        "catarina", "granada", "diriomo", "nandaime", "jinotepe",
        "diriamba", "san marcos", "rivas", "san juan del sur",
        "belen", "boaco", "camoapa", "teustepe", "juigalpa",
        "acoyapa", "santo tomas",
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


def _coverage_score(msavi2: float, params: dict) -> float:
    """Normaliza MSAVI2 a 0-1 con unitScale calibrado por zona."""
    cmin, cmax = params["coverage_min"], params["coverage_max"]
    if cmax <= cmin:
        return 0.5
    return max(0.0, min(1.0, (msavi2 - cmin) / (cmax - cmin)))


def _slope_score_linear(slope_percent: float) -> float:
    """Pendiente lineal inversa: 0% → 1.0, 12%+ → 0.0."""
    return max(0.0, min(1.0, 1.0 - slope_percent / 12.0))


def _traffic_light(global_score: float, params: dict) -> str:
    if global_score >= params["threshold_green"]:
        return "verde"
    if global_score >= params["threshold_red"]:
        return "amarillo"
    return "rojo"


def recommend(parcel: ParcelInput) -> Dict:
    effective_zone, zone_validation = _resolve_zone(parcel)
    params = ZONE_PARAMS[effective_zone]

    coverage = _coverage_score(parcel.msavi2, params)
    slope = _slope_score_linear(parcel.slope_percent)

    global_score = round(coverage * params["weight_cob"] + slope * params["weight_pen"], 3)
    traffic = _traffic_light(global_score, params)

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
        f"Zona {effective_zone.value}; cobertura={coverage:.2f}, "
        f"pendiente={slope:.2f}, msavi2={parcel.msavi2:.4f}"
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
        f"Parcela {parcel.parcel_id}: {traffic.upper()} "
        f"(score={global_score:.2f}). "
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
            "coverage": coverage,
            "slope": slope,
            "msavi2": parcel.msavi2,
            "weight_cob": params["weight_cob"],
            "weight_pen": params["weight_pen"],
            "threshold_green": params["threshold_green"],
            "threshold_red": params["threshold_red"],
            "zone_validation": zone_validation,
            "zone_used": effective_zone.value,
        },
    }
