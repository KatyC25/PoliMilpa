import datetime as dt
import json
import os
from typing import Any, Dict, Optional

from app.services.cache import gee_cache


class GEEClient:
    """
    Cliente para extraer features satelitales por parcela usando
    Google Earth Engine (GEE) 
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("GEE_ENABLED", "false").lower() == "true"
        self.project_id = os.getenv("GEE_PROJECT_ID")
        self._ee: Optional[Any] = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        if not self.enabled:
            print("[GEE] Deshabilitado: GEE_ENABLED no es true")
            return False

        if self._initialized:
            return self._ee is not None

        self._initialized = True
        try:
            import ee  # type: ignore

            key_json = os.getenv("GEE_SERVICE_ACCOUNT_KEY")
            print(f"[GEE] Inicializando... project={self.project_id}, key_present={key_json is not None}")
            if key_json:
                import json as _json

                creds_data = _json.loads(key_json)
                credentials = ee.ServiceAccountCredentials(
                    creds_data["client_email"], key_data=creds_data["private_key"]
                )
                ee.Initialize(credentials, project=self.project_id)
            elif self.project_id:
                ee.Initialize(project=self.project_id)
            else:
                ee.Initialize()
            self._ee = ee
            print("[GEE] Inicializado correctamente")
            return True
        except Exception as exc:
            print(f"[GEE] Error al inicializar: {exc}")
            self._ee = None
            return False

    @gee_cache.memoize
    def _compute_gee_features(
        self, lat: float, lon: float
    ) -> Optional[Dict[str, float]]:
        if not self._ensure_initialized():
            print(f"[GEE] _compute_gee_features: no inicializado para lat={lat}, lon={lon}")
            return None
        if self._ee is None:
            print(f"[GEE] _compute_gee_features: ee is None para lat={lat}, lon={lon}")
            return None

        ee = self._ee
        point = ee.Geometry.Point([lon, lat])
        roi = point.buffer(120).bounds()
        start_date, end_date = self._gee_date_range()

        # Sentinel-2: MSAVI2 como proxy de vigor/cobertura para sombra y estres.
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        )
        s2_img = ee.Image(s2.median())
        nir = s2_img.select("B8")
        red = s2_img.select("B4")
        msavi2 = (
            nir.multiply(2)
            .add(1)
            .subtract(
                nir.multiply(2)
                .add(1)
                .pow(2)
                .subtract(nir.subtract(red).multiply(8))
                .sqrt()
            )
            .divide(2)
            .rename("msavi2")
        )

        # Sentinel-1: VV como proxy simple de humedad superficial, normalizado a 0-1.
        s1 = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        )
        s1_img = ee.Image(s1.select("VV").median())
        moisture = s1_img.unitScale(-18, -5).clamp(0, 1).rename("soil_moisture")

        # Copernicus DEM GLO-30 para pendiente
        dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM').mosaic()
        slope = ee.Terrain.slope(dem).rename("slope")

        combined = ee.Image.cat([moisture, msavi2, slope]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=30,
            bestEffort=True,
            maxPixels=1_000_000,
        )
        try:
            values = combined.getInfo() or {}
        except Exception as exc:
            print(f"[GEE] combined.getInfo() fallo para lat={lat}, lon={lon}: {exc}")
            return None

        msavi2_value = values.get("msavi2")
        moisture_value = values.get("soil_moisture")
        slope_value = values.get("slope")
        if msavi2_value is None or moisture_value is None:
            print(f"[GEE] valores criticos nulos: msavi2={msavi2_value}, moisture={moisture_value}")
            return None
        if slope_value is None:
            print(f"[GEE] slope nulo para lat={lat}, lon={lon}, usando 0.0 como fallback")
            slope_value = 0.0

        msavi2_normalized = max(0.0, min(1.0, (float(msavi2_value) + 1.0) / 2.0))
        shade = msavi2_normalized
        stress = max(0.0, min(1.0, 1.0 - msavi2_normalized))

        return {
            "soil_moisture": max(0.0, min(1.0, float(moisture_value))),
            "shade_index": shade,
            "stress_index": stress,
            "slope_percent": max(0.0, min(100.0, float(slope_value))),
            "msavi2": round(float(msavi2_value), 4),
            "source": "gee",
            "s1_dataset": "COPERNICUS/S1_GRD",
            "s2_dataset": "COPERNICUS/S2_SR_HARMONIZED",
            "s2_index": "msavi2",
            "dem_dataset": "COPERNICUS/DEM/GLO30",
            "lat": lat,
            "lon": lon,
        }

    @staticmethod
    def _gee_date_range(months_back: int = 24) -> tuple[str, str]:
        end = dt.date.today()
        start = end - dt.timedelta(days=months_back * 30)
        return start.isoformat(), end.isoformat()

    def get_parcel_features(
        self,
        lat: float,
        lon: float,
        agro_zone: object,
        seasonal_forecast: str,
    ) -> Dict[str, float]:
        del agro_zone
        del seasonal_forecast

        if not self.enabled:
            print("[GEE] get_parcel_features: deshabilitado")
            raise RuntimeError(
                "GEE deshabilitado. Define GEE_ENABLED=true y autentica Earth Engine."
            )

        print(f"[GEE] get_parcel_features: lat={lat}, lon={lon}")
        gee_features = self._compute_gee_features(lat=lat, lon=lon)
        if gee_features is None:
            print(f"[GEE] get_parcel_features: features nulos para lat={lat}, lon={lon}")
            raise RuntimeError(
                "GEE: No fue posible obtener features. Revisa logs de Render para el error exacto."
            )
        print(f"[GEE] get_parcel_features: OK msavi2={gee_features.get('msavi2')}")
        return gee_features

    def get_classification_tile(
        self,
        lat: float,
        lon: float,
        agro_zone: object,
        geometry: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self._ensure_initialized() or self._ee is None:
            print(f"[GEE] get_classification_tile: no inicializado para lat={lat}, lon={lon}")
            return None

        ee = self._ee
        start_date, end_date = self._gee_date_range()

        if geometry:
            try:
                coords = json.loads(geometry)
                if coords.get("type") == "Polygon":
                    roi = ee.Geometry.Polygon(coords["coordinates"])
                elif coords.get("type") == "Feature" and coords.get("geometry", {}).get("type") == "Polygon":
                    roi = ee.Geometry.Polygon(coords["geometry"]["coordinates"])
                else:
                    roi = ee.Geometry.Point([lon, lat]).buffer(120).bounds()
            except Exception:
                roi = ee.Geometry.Point([lon, lat]).buffer(120).bounds()
        else:
            roi = ee.Geometry.Point([lon, lat]).buffer(120).bounds()

        zone_name = agro_zone.value if hasattr(agro_zone, "value") else str(agro_zone)
        zp = _ZONE_PARAMS.get(zone_name, _ZONE_PARAMS["transition"])

        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        )
        s2_img = ee.Image(s2.median()).clip(roi)
        nir = s2_img.select("B8")
        red = s2_img.select("B4")
        msavi2 = (
            nir.multiply(2)
            .add(1)
            .subtract(
                nir.multiply(2)
                .add(1)
                .pow(2)
                .subtract(nir.subtract(red).multiply(8))
                .sqrt()
            )
            .divide(2)
        )

        msavi2_norm = msavi2.add(1).divide(2).clamp(zp["cmin"], zp["cmax"])
        coverage = msavi2_norm.subtract(zp["cmin"]).divide(zp["cmax"] - zp["cmin"]).clamp(0, 1)

        dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM').mosaic()
        slope = ee.Terrain.slope(dem)
        slope_norm = slope.clamp(0, 12).divide(12)
        slope_score = ee.Image(1).subtract(slope_norm)

        score_img = coverage.multiply(zp["wc"]).add(slope_score.multiply(zp["wp"]))
        tgreen, tred = zp["tg"], zp["tr"]

        classified = (
            ee.Image(1)
            .where(score_img.gte(tgreen), 3)
            .where(score_img.lt(tgreen).And(score_img.gte(tred)), 2)
            .where(score_img.lt(tred), 1)
            .clip(roi)
        )

        vis = classified.visualize(
            min=1,
            max=3,
            palette=["d73027", "fdae61", "1a9850"],
            opacity=0.7,
        )

        try:
            map_id = vis.getMapId()
            mid = map_id["mapid"]
            tile_url = f"https://earthengine.googleapis.com/v1/{mid}/tiles/{{z}}/{{x}}/{{y}}"
            return {
                "url": tile_url,
                "mapid": mid,
                "center": [lat, lon],
            }
        except Exception as exc:
            print(f"[GEE] get_classification_tile: getMapId fallo: {exc}")
            return None


_ZONE_PARAMS = {
    "highland_humid": {"cmin": 0.10, "cmax": 0.75, "wc": 0.75, "wp": 0.25, "tg": 0.52, "tr": 0.32},
    "subhumid_caribbean": {"cmin": 0.10, "cmax": 0.75, "wc": 0.75, "wp": 0.25, "tg": 0.52, "tr": 0.32},
    "dry_corridor": {"cmin": 0.12, "cmax": 0.55, "wc": 0.80, "wp": 0.20, "tg": 0.48, "tr": 0.32},
    "transition": {"cmin": 0.12, "cmax": 0.55, "wc": 0.80, "wp": 0.20, "tg": 0.48, "tr": 0.32},
}
