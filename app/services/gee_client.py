import datetime as dt
import os
from typing import Any, Dict, Optional


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
            return False

        if self._initialized:
            return self._ee is not None

        self._initialized = True
        try:
            import ee  # type: ignore

            if self.project_id:
                ee.Initialize(project=self.project_id)
            else:
                ee.Initialize()
            self._ee = ee
            return True
        except Exception:
            self._ee = None
            return False

    def _compute_gee_features(
        self, lat: float, lon: float
    ) -> Optional[Dict[str, float]]:
        if not self._ensure_initialized() or self._ee is None:
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

        # DEM Copernicus para pendiente. Este dataset se publica como ImageCollection.
        dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic()
        slope = ee.Terrain.slope(dem).rename("slope")

        combined = ee.Image.cat([moisture, msavi2, slope]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=30,
            bestEffort=True,
            maxPixels=1_000_000,
        )
        values = combined.getInfo() or {}

        msavi2_value = values.get("msavi2")
        moisture_value = values.get("soil_moisture")
        slope_value = values.get("slope")
        if msavi2_value is None or moisture_value is None or slope_value is None:
            return None

        msavi2_normalized = max(0.0, min(1.0, (float(msavi2_value) + 1.0) / 2.0))
        shade = msavi2_normalized
        stress = max(0.0, min(1.0, 1.0 - msavi2_normalized))

        return {
            "soil_moisture": max(0.0, min(1.0, float(moisture_value))),
            "shade_index": shade,
            "stress_index": stress,
            "slope_percent": max(0.0, min(100.0, float(slope_value))),
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
            raise RuntimeError(
                "GEE deshabilitado. Define GEE_ENABLED=true y autentica Earth Engine."
            )

        gee_features = self._compute_gee_features(lat=lat, lon=lon)
        if gee_features is None:
            raise RuntimeError(
                "No fue posible obtener features desde GEE. Verifica autenticacion, "
                "proyecto y disponibilidad de imagenes para la coordenada."
            )
        return gee_features
