import json
from typing import Optional, Tuple

from shapely.geometry import shape
from shapely.ops import transform
import pyproj


def compute_area(geometry_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not geometry_str:
        return None, None

    try:
        geom = json.loads(geometry_str)
    except (json.JSONDecodeError, TypeError):
        return None, None

    try:
        if isinstance(geom, dict) and geom.get("type") == "Feature":
            geom = geom.get("geometry", geom)
        polygon = shape(geom)
    except Exception:
        return None, None

    if polygon.is_empty or not polygon.is_valid:
        return None, None

    centroid = polygon.centroid
    utm_zone = _utm_zone(centroid.y, centroid.x)
    crs_wgs = pyproj.CRS("EPSG:4326")
    crs_utm = pyproj.CRS(f"EPSG:{utm_zone}")
    transformer = pyproj.Transformer.from_crs(crs_wgs, crs_utm, always_xy=True)
    projected = transform(transformer.transform, polygon)

    area_m2 = projected.area
    area_manzanas = area_m2 / 7050.0
    return round(area_m2, 2), round(area_manzanas, 2)


def _utm_zone(lat: float, lon: float) -> int:
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone
    return 32700 + zone
