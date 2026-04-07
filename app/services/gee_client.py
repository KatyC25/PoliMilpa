import os
from typing import Dict

from app.schemas import AgroZone


class GEEClient:
    """
    Cliente inicial para extraer features satelitales por parcela.
    Esta version usa un fallback deterministico para que el MVP funcione
    aun sin credenciales GEE configuradas.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("GEE_ENABLED", "false").lower() == "true"

    def get_parcel_features(
        self,
        lat: float,
        lon: float,
        agro_zone: AgroZone,
        seasonal_forecast: str,
    ) -> Dict[str, float]:
        if self.enabled:
            # Placeholder para integracion real con Earth Engine:
            # 1) Definir region de interes alrededor del punto/parcela
            # 2) Consultar Sentinel-2 para MSAVI2
            # 3) Consultar Sentinel-1 para humedad proxy
            # 4) Consultar DEM para pendiente
            pass

        # Fallback MVP reproducible para demo.
        base = 0.55 if agro_zone == AgroZone.HIGHLAND_HUMID else 0.45
        if seasonal_forecast == "dry":
            base -= 0.1
        elif seasonal_forecast == "wet":
            base += 0.08

        moisture = max(0.1, min(0.95, base))
        shade = max(0.15, min(0.9, base + 0.05))
        stress = max(0.05, min(0.9, 1 - moisture))
        slope = 12 if agro_zone == AgroZone.HIGHLAND_HUMID else 8

        return {
            "soil_moisture": moisture,
            "shade_index": shade,
            "stress_index": stress,
            "slope_percent": float(slope),
            "source": "fallback_mvp",
            "lat": lat,
            "lon": lon,
        }
