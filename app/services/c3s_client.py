import datetime as dt
import os
import tempfile
from typing import Optional


class C3SClient:
    """
    Cliente para inferir pronostico estacional (dry/normal/wet)
    usando Copernicus C3S via CDS API.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("C3S_ENABLED", "false").lower() == "true"
        self.dataset = os.getenv("C3S_DATASET", "seasonal-monthly-single-levels")
        self.variable = os.getenv("C3S_VARIABLE", "total_precipitation")
        self.originating_centre = os.getenv("C3S_ORIGINATING_CENTRE", "ecmwf")
        self.system = os.getenv("C3S_SYSTEM", "51")
        self.leadtime_month = os.getenv("C3S_LEADTIME_MONTH", "1")
        self.format_key = os.getenv("C3S_FORMAT_KEY", "data_format")
        self.data_format = os.getenv("C3S_DATA_FORMAT", "netcdf")
        self.dry_threshold = float(os.getenv("C3S_DRY_THRESHOLD", "0.04"))
        self.wet_threshold = float(os.getenv("C3S_WET_THRESHOLD", "0.14"))

    def _build_request(self, lat: float, lon: float) -> dict:
        now = dt.datetime.utcnow()
        north = min(90.0, lat + 0.5)
        south = max(-90.0, lat - 0.5)
        west = max(-180.0, lon - 0.5)
        east = min(180.0, lon + 0.5)

        request = {
            "originating_centre": [self.originating_centre],
            "system": [self.system],
            "variable": [self.variable],
            "product_type": ["monthly_mean"],
            "year": [f"{now.year:04d}"],
            "month": [f"{now.month:02d}"],
            "leadtime_month": [self.leadtime_month],
            "area": [north, west, south, east],
        }
        request[self.format_key] = self.data_format
        return request

    def _extract_precip_value(self, nc_path: str) -> float:
        try:
            from netCDF4 import Dataset  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Falta dependencia netCDF4 para leer respuesta C3S. Instala requirements.txt."
            ) from exc

        with Dataset(nc_path) as ds:
            if self.variable in ds.variables:
                data = ds.variables[self.variable][:]
                return float(data.mean())

            for name, variable in ds.variables.items():
                if name.lower() in {
                    "latitude",
                    "longitude",
                    "lat",
                    "lon",
                    "time",
                    "number",
                }:
                    continue
                if getattr(variable, "ndim", 0) >= 1:
                    return float(variable[:].mean())

        raise RuntimeError(
            "No se encontro variable de precipitacion valida en archivo C3S. "
            "Ajusta C3S_VARIABLE o revisa el dataset."
        )

    def _fetch_monthly_precip(self, lat: float, lon: float) -> float:
        try:
            import cdsapi  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Falta dependencia cdsapi para consultar C3S. Instala requirements.txt."
            ) from exc

        request = self._build_request(lat=lat, lon=lon)
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            target = tmp.name

        try:
            client = cdsapi.Client(quiet=True)
            client.retrieve(self.dataset, request, target)
            return self._extract_precip_value(target)
        except Exception as exc:
            raise RuntimeError(
                "Fallo consulta a C3S. Verifica .cdsapirc, terminos del dataset y parametros "
                f"(dataset={self.dataset}, variable={self.variable})."
            ) from exc
        finally:
            try:
                os.remove(target)
            except OSError:
                pass

    def get_seasonal_forecast(self, lat: float, lon: float) -> str:
        if not self.enabled:
            raise RuntimeError(
                "C3S deshabilitado. Define C3S_ENABLED=true o envia seasonal_forecast en el payload."
            )

        precip_value = self._fetch_monthly_precip(lat=lat, lon=lon)

        if precip_value <= self.dry_threshold:
            return "dry"
        if precip_value >= self.wet_threshold:
            return "wet"
        return "normal"
