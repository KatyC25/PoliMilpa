import datetime as dt
from typing import Optional, Dict, List, Tuple


FOS_2026 = {
    "highland_humid": {
        "maiz_110": ("2026-05-11", "2026-05-25"),
        "frijol_75": ("2026-05-11", "2026-05-20"),
        "arroz_120": None,
        "sorgo_120": None,
    },
    "dry_corridor": {
        "maiz_110": ("2026-05-20", "2026-06-10"),
        "frijol_75": ("2026-05-25", "2026-06-10"),
        "arroz_120": None,
        "sorgo_120": ("2026-05-25", "2026-06-25"),
    },
    "subhumid_caribbean": {
        "maiz_110": ("2026-05-11", "2026-05-25"),
        "frijol_75": ("2026-05-15", "2026-05-25"),
        "arroz_120": ("2026-05-10", "2026-07-10"),
        "sorgo_120": None,
    },
    "transition": {
        "maiz_110": ("2026-05-20", "2026-06-10"),
        "frijol_75": ("2026-05-15", "2026-05-25"),
        "arroz_120": ("2026-05-25", "2026-06-10"),
        "sorgo_120": ("2026-05-25", "2026-06-25"),
    },
}

CROP_LABELS = {
    "maiz_110": "Maiz",
    "frijol_75": "Frijol",
    "arroz_120": "Arroz",
    "sorgo_120": "Sorgo",
}

CROP_KEY_MAP = {
    "maiz": "maiz_110",
    "frijol": "frijol_75",
    "arroz": "arroz_120",
    "sorgo": "sorgo_120",
}


def get_fos_status(
    zone: str,
    crop_name: str,
    today: Optional[dt.date] = None,
) -> Optional[Dict]:
    if today is None:
        today = dt.date.today()

    fos_key = CROP_KEY_MAP.get(crop_name)
    if fos_key is None:
        return None

    zone_data = FOS_2026.get(zone, {})
    window = zone_data.get(fos_key)
    if window is None:
        return {"status": "no_aplica", "crop": CROP_LABELS.get(fos_key, crop_name)}

    inicio = dt.date.fromisoformat(window[0])
    fin = dt.date.fromisoformat(window[1])

    if today < inicio:
        dias = (inicio - today).days
        return {
            "status": "proxima",
            "crop": CROP_LABELS.get(fos_key, crop_name),
            "inicio": window[0],
            "fin": window[1],
            "dias_restantes": dias,
        }
    elif inicio <= today <= fin:
        dias_restantes = (fin - today).days
        return {
            "status": "activa",
            "crop": CROP_LABELS.get(fos_key, crop_name),
            "inicio": window[0],
            "fin": window[1],
            "dias_restantes": dias_restantes,
        }
    else:
        dias = (today - fin).days
        return {
            "status": "expirada",
            "crop": CROP_LABELS.get(fos_key, crop_name),
            "inicio": window[0],
            "fin": window[1],
            "dias_desde_cierre": dias,
        }


def get_active_windows(
    zone: str,
    today: Optional[dt.date] = None,
) -> List[Dict]:
    if today is None:
        today = dt.date.today()

    zone_data = FOS_2026.get(zone, {})
    result = []
    for fos_key, (status_info) in [
        (
            k,
            get_fos_status(
                zone,
                k.replace("_110", "").replace("_75", "").replace("_120", ""),
                today,
            ),
        )
        for k in zone_data
    ]:
        if status_info is None:
            continue
        status_info["fos_key"] = fos_key
        result.append(status_info)
    return result


def get_all_windows(
    zone: str,
    today: Optional[dt.date] = None,
) -> Dict[str, List[Dict]]:
    if today is None:
        today = dt.date.today()

    zone_data = FOS_2026.get(zone, {})
    activas = []
    proximas = []
    expiradas = []
    no_aplica = []

    for fos_key in zone_data:
        crop_label = CROP_LABELS.get(fos_key, fos_key)
        crop_simple = crop_label.lower()
        status_info = get_fos_status(zone, crop_simple, today)
        if status_info is None:
            continue
        status_info["fos_key"] = fos_key
        if status_info["status"] == "activa":
            activas.append(status_info)
        elif status_info["status"] == "proxima":
            proximas.append(status_info)
        elif status_info["status"] == "expirada":
            expiradas.append(status_info)
        elif status_info["status"] == "no_aplica":
            no_aplica.append(status_info)

    return {
        "activas": activas,
        "proximas": proximas,
        "expiradas": expiradas,
        "no_aplica": no_aplica,
    }


def get_crop_fos_dates(
    zone: str,
    crop_name: str,
) -> Optional[Dict[str, str]]:
    fos_key = CROP_KEY_MAP.get(crop_name)
    if fos_key is None:
        return None
    zone_data = FOS_2026.get(zone, {})
    window = zone_data.get(fos_key)
    if window is None:
        return None
    return {"inicio": window[0], "fin": window[1]}


NINO_ALERTS = {
    "dry": {
        "level": "seco",
        "label": "Alerta Niño activo",
        "message": (
            "Pronostico seco detectado por C3S/ECMWF. "
            "Se espera precipitacion por debajo de lo habitual. "
            "Prioriza cultivos tolerantes a sequia como sorgo y ajonjoli. "
            "Considera riego complementario."
        ),
        "precipitation_note": "Menos lluvia de lo habitual",
    },
    "normal": {
        "level": "normal",
        "label": "Condiciones normales",
        "message": (
            "Pronostico de precipitacion dentro del rango habitual. "
            "Condiciones favorables para la siembra."
        ),
        "precipitation_note": "Precipitacion dentro del promedio",
    },
    "wet": {
        "level": "humedo",
        "label": "La Niña activa — temporada humeda",
        "message": (
            "Pronostico humedo detectado por C3S/ECMWF. Se espera precipitacion "
            "por encima de lo habitual. Asegura buen drenaje en la parcela "
            "y monitorea riesgo de inundacion."
        ),
        "precipitation_note": "Mas lluvia de lo habitual",
    },
}


def get_nino_alert(seasonal_forecast: str) -> Optional[Dict]:
    return NINO_ALERTS.get(seasonal_forecast)
