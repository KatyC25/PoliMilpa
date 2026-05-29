import datetime as dt
import unicodedata
from typing import Dict, List, Optional, Tuple

from app.schemas import AgroZone, CropRecommendation, ParcelInput
from app.services.fos_data import (
    get_all_windows,
    get_crop_fos_dates,
    get_fos_status,
    get_nino_alert,
)


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
        "food": ["maiz", "frijol", "papa"],
    },
    AgroZone.DRY_CORRIDOR: {
        "macro_region": "pacifico_seco",
        "rent": ["ajonjoli", "mani"],
        "food": ["sorgo", "maiz", "frijol"],
    },
    AgroZone.SUBHUMID_CARIBBEAN: {
        "macro_region": "caribe_humedo",
        "rent": ["cacao", "platano"],
        "food": ["yuca", "quequisque", "malanga", "arroz"],
    },
    AgroZone.TRANSITION: {
        "macro_region": "transicion",
        "rent": ["mani", "platano"],
        "food": ["frijol", "maiz", "sorgo"],
    },
}

# Catalogo departamental: cultivos por departamento segun datos MAG/INTA.
# Si un departamento no aparece aqui, se usa ZONE_CATALOG como fallback.
DEPARTMENT_CATALOG = {
    "jinotega":     {"rent": ["cafe"],              "food": ["maiz", "frijol", "papa"]},
    "matagalpa":    {"rent": ["cafe"],              "food": ["maiz", "frijol", "tomate"]},
    "chinandega":   {"rent": ["ajonjoli"],           "food": ["sorgo", "maiz", "frijol"]},
    "leon":         {"rent": ["mani"],              "food": ["sorgo", "maiz", "frijol"]},
    "nueva segovia":{"rent": ["cafe"],              "food": ["frijol", "maiz", "sorgo"]},
    "esteli":       {"rent": ["tabaco"],            "food": ["frijol", "maiz", "papa"]},
    "madriz":       {"rent": ["ajonjoli"],           "food": ["sorgo", "maiz", "frijol"]},
    "managua":      {"rent": ["platano"],           "food": ["maiz", "frijol", "sorgo"]},
    "masaya":       {"rent": ["mani"],              "food": ["sorgo", "maiz", "frijol"]},
    "granada":      {"rent": ["mani"],              "food": ["arroz", "frijol", "maiz"]},
    "carazo":       {"rent": ["mani"],              "food": ["sorgo", "maiz", "frijol"]},
    "rivas":        {"rent": ["platano"],           "food": ["arroz", "frijol", "sorgo"]},
    "boaco":        {"rent": ["mani"],              "food": ["maiz", "frijol", "sorgo"]},
    "chontales":    {"rent": ["platano"],           "food": ["yuca", "maiz", "frijol"]},
    "raccs":        {"rent": ["cacao"],             "food": ["yuca", "quequisque", "malanga"]},
    "raccn":        {"rent": ["cacao"],             "food": ["platano", "arroz", "yuca"]},
    "rio san juan": {"rent": ["cacao"],             "food": ["arroz", "platano", "yuca"]},
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


def _get_ciclo() -> dict:
    mes = dt.date.today().month
    if 5 <= mes <= 8:
        return {"name": "primera", "months": "mayo-agosto",
                "prefiere": ["maiz", "arroz", "yuca", "papa", "mani"]}
    if 9 <= mes <= 12:
        return {"name": "postrera", "months": "septiembre-diciembre",
                "prefiere": ["frijol", "sorgo", "papa", "tomate"]}
    return {"name": "apante", "months": "enero-abril (requiere riego)",
            "prefiere": ["frijol", "chiltoma", "tomate", "hortalizas"]}


def _next_ciclo(actual: str) -> dict:
    ciclos = {"primera": ("postrera", "septiembre-diciembre"),
              "postrera": ("apante", "enero-abril"),
              "apante": ("primera", "mayo-agosto")}
    name, months = ciclos[actual]
    return {"name": name, "months": months}


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

    dep_key = _normalize_department(parcel.department)
    catalog = DEPARTMENT_CATALOG.get(dep_key, ZONE_CATALOG[effective_zone])

    rent_crop = catalog["rent"][0]
    ciclo = _get_ciclo()

    preferidos = [c for c in ciclo["prefiere"] if c in catalog["food"]]
    food_crop = preferidos[0] if preferidos else catalog["food"][0]

    if parcel.seasonal_forecast == "dry" and "sorgo" in catalog["food"]:
        food_crop = "sorgo"
    elif parcel.seasonal_forecast == "wet" and "arroz" in catalog["food"]:
        food_crop = "arroz"
    elif parcel.seasonal_forecast == "wet" and "quequisque" in catalog["food"]:
        food_crop = "quequisque"

    zone_str = effective_zone.value
    fos_all = get_all_windows(zone_str)
    rent_fos = get_fos_status(zone_str, rent_crop)
    food_fos = get_fos_status(zone_str, food_crop)

    rent_dates = get_crop_fos_dates(zone_str, rent_crop)
    food_dates = get_crop_fos_dates(zone_str, food_crop)
    planting_dates = {}
    if rent_dates:
        planting_dates["rent_crop"] = {
            "crop": rent_crop,
            "inicio": rent_dates["inicio"],
            "fin": rent_dates["fin"],
        }
    if food_dates:
        planting_dates["food_crop"] = {
            "crop": food_crop,
            "inicio": food_dates["inicio"],
            "fin": food_dates["fin"],
        }

    food_status = food_fos["status"] if food_fos else "sin_datos"
    if food_status == "activa":
        window = f"{food_dates['inicio']} al {food_dates['fin']}" if food_dates else "sembrar_ahora"
    elif food_status == "proxima" and food_fos:
        window = f"proxima: {food_fos['inicio']} al {food_fos['fin']}"
    elif food_status == "expirada":
        if traffic == "verde":
            window = "fuera de ventana optima (condiciones satelitales favorables)"
        elif traffic == "amarillo":
            window = "fuera de ventana optima (esperar mejora de condiciones)"
        else:
            window = "no_sembrar"
    else:
        window = (
            "sembrar_ahora"
            if traffic == "verde"
            else "esperar_7_dias"
            if traffic == "amarillo"
            else "no_sembrar"
        )

    nino_alert = get_nino_alert(parcel.seasonal_forecast)

    reason = (
        f"Zona {effective_zone.value}; cobertura={coverage:.2f}, "
        f"pendiente={slope:.2f}, msavi2={parcel.msavi2:.4f}"
    )

    prox = _next_ciclo(ciclo["name"])
    otros = [c for c in catalog["food"] if c != food_crop]
    if otros:
        seasonal_context = (
            f"Ciclo {ciclo['name']} ({ciclo['months']}): siembra {food_crop}. "
            f"Para {prox['name']} ({prox['months']}) considera {otros[0]}."
        )
    else:
        seasonal_context = (
            f"Ciclo {ciclo['name']} ({ciclo['months']}): siembra {food_crop}."
        )

    parcela_nombre = parcel.parcel_id or "tu parcela"
    window_display = window.replace("_", " ")
    advisory = (
        f"Parcela {parcela_nombre}: {traffic.upper()} "
        f"(score={global_score:.2f}). "
        f"Estas en ciclo de {ciclo['name']} ({ciclo['months']}). "
        f"Te recomendamos combinar {rent_crop} + {food_crop}. "
        f"Accion: {window_display}."
    )

    if food_fos and food_fos["status"] == "activa" and food_dates:
        advisory += (
            f" Ventana optima FOS MAG para {food_crop}: "
            f"{food_dates['inicio']} al {food_dates['fin']}. Estas a tiempo."
        )
    elif food_fos and food_fos["status"] == "proxima":
        advisory += (
            f" Ventana FOS MAG para {food_crop} inicia el {food_fos['inicio']}. "
            f"Faltan {food_fos['dias_restantes']} dias."
        )
    elif food_fos and food_fos["status"] == "expirada":
        if traffic in ("verde", "amarillo"):
            advisory += (
                f" Ventana optima FOS MAG para {food_crop} ya paso "
                f"({food_dates['inicio']} al {food_dates['fin']}), "
                f"pero las condiciones satelitales actuales son favorables. "
                f"Puedes sembrar evaluando riesgos."
            )
        else:
            advisory += (
                f" Ventana optima FOS MAG para {food_crop} ya paso "
                f"({food_dates['inicio']} al {food_dates['fin']}). "
                f"No se recomienda sembrar en este momento."
            )

    if nino_alert and nino_alert["level"] == "seco":
        advisory += (
            f" ALERTA NINO: {nino_alert['precipitation_note']}. "
            f"Prioriza cultivos tolerantes a sequia."
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

    recommendations: List[CropRecommendation] = [
        CropRecommendation(
            rent_crop=rent_crop,
            food_crop=food_crop,
            confidence=global_score,
            reason=reason,
            seasonal_context=seasonal_context,
        )
    ]

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
        "nino_alert": nino_alert,
        "fos_windows": fos_all,
        "planting_dates": planting_dates,
    }
