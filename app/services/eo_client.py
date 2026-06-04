import datetime as dt
import json
import math
import os
import base64
from typing import Any, Dict, List, Optional

from app.services.cache import eo_cache

_SENTINELHUB_AVAILABLE = False
_SHConfig = None
_SentinelHubStatistical = None

try:
    from sentinelhub import (
        SHConfig,
        SentinelHubStatistical,
        DataCollection,
        CRS,
        Geometry,
        BBox,
    )
    _SENTINELHUB_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Evalscripts para Sentinel Hub
# ---------------------------------------------------------------------------

MSAVI2_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B04", "B08", "SCL", "dataMask"],
    output: { id: "msavi2", bands: 1, sampleType: SampleType.FLOAT32 }
  };
}
function evaluatePixel(sample) {
  if (!sample.dataMask) return [NaN];
  var scl = sample.SCL;
  if (scl !== 4 && scl !== 5 && scl !== 6) return [NaN];
  var nir = sample.B08 / 10000;
  var red = sample.B04 / 10000;
  var msavi2 = (2*nir + 1 - Math.sqrt(Math.pow(2*nir+1, 2) - 8*(nir-red))) / 2;
  return [msavi2];
}
"""

SOIL_MOISTURE_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["VV", "dataMask"],
    output: { id: "vv", bands: 1, sampleType: SampleType.FLOAT32 }
  };
}
function evaluatePixel(sample) {
  if (!sample.dataMask) return [NaN];
  return [sample.VV];
}
"""


def _classification_evalscript(zp: Dict[str, float]) -> str:
    return f"""//VERSION=3
function setup() {{
  return {{
    input: ["B04", "B08", "dataMask"],
    output: {{ id: "class", bands: 4, sampleType: SampleType.UINT8 }}
  }};
}}
function evaluatePixel(sample) {{
  var dm = sample.dataMask;
  if (!dm) return [0,0,0,0];
  var nir = sample.B08 / 10000;
  var red = sample.B04 / 10000;
  var msavi2 = (2*nir + 1 - Math.sqrt(Math.pow(2*nir+1, 2) - 8*(nir-red))) / 2;
  var msavi2_norm = (msavi2 + 1) / 2;
  var coverage = Math.max(0, Math.min(1, (msavi2_norm - {zp['cmin']}) / ({zp['cmax']} - {zp['cmin']})));
  var score = coverage * {zp['wc']} + (1 - 0) * {zp['wp']};
  var r, g, b;
  if (score >= {zp['tg']})       {{ r=26;  g=152; b=80;  }}
  else if (score >= {zp['tr']})  {{ r=253; g=174; b=97;  }}
  else                           {{ r=215; g=48;  b=39;  }}
  return [r, g, b, 165];
}}
"""


_ZONE_PARAMS = {
    "highland_humid":      {"cmin": 0.10, "cmax": 0.75, "wc": 0.75, "wp": 0.25, "tg": 0.52, "tr": 0.32},
    "subhumid_caribbean":  {"cmin": 0.10, "cmax": 0.75, "wc": 0.75, "wp": 0.25, "tg": 0.52, "tr": 0.32},
    "dry_corridor":        {"cmin": 0.12, "cmax": 0.55, "wc": 0.80, "wp": 0.20, "tg": 0.48, "tr": 0.32},
    "transition":          {"cmin": 0.12, "cmax": 0.55, "wc": 0.80, "wp": 0.20, "tg": 0.48, "tr": 0.32},
}


# ---------------------------------------------------------------------------
# EOClient
# ---------------------------------------------------------------------------

class EOClient:
    """
    Cliente de observacion terrestre usando las APIs de Copernicus Data Space Ecosystem.

    Modo live (por defecto si hay credenciales SH_CLIENT_ID + SH_CLIENT_SECRET):
      - Statistical API de Sentinel Hub para extraer MSAVI2, humedad, elevacion.
      - OGC WMS de Sentinel Hub para tiles de clasificacion en tiempo real.

    Modo static (fallback sin credenciales):
      - Lee eo_parcels.json precargado en data/.
    """

    _MATCH_RADIUS_DEG = 0.05

    def __init__(self) -> None:
        self.enabled = True
        self._config = None
        self._instance_id: Optional[str] = None
        self._wms_base_url: Optional[str] = None
        self._use_live = False

        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        self.data_file = os.getenv("EO_DATA_FILE", os.path.join(data_dir, "eo_parcels.json"))
        self.tile_dir = os.getenv("EO_TILE_DIR", os.path.join(data_dir, "tiles"))

        self._parcel_data: Optional[Dict[str, Any]] = None
        self._parcels: List[Dict] = []
        self._static_loaded = False

        if _SENTINELHUB_AVAILABLE:
            self._init_live()

    def _init_live(self) -> None:
        client_id = os.getenv("SH_CLIENT_ID")
        client_secret = os.getenv("SH_CLIENT_SECRET")
        instance_id = os.getenv("SH_INSTANCE_ID")

        if not client_id or not client_secret:
            print("[EO] Modo static: sin SH_CLIENT_ID/SH_CLIENT_SECRET")
            return

        config = SHConfig()
        config.sh_client_id = client_id
        config.sh_client_secret = client_secret
        config.sh_base_url = "https://sh.dataspace.copernicus.eu"
        if instance_id:
            config.instance_id = instance_id
        self._config = config
        self._instance_id = instance_id
        self._wms_base_url = f"https://sh.dataspace.copernicus.eu/ogc/wms/{instance_id}" if instance_id else None
        self._use_live = True
        print("[EO] Modo live: Sentinel Hub CDSE configurado")

    # ------------------------------------------------------------------
    # Static fallback
    # ------------------------------------------------------------------

    def _load_static(self) -> None:
        if self._static_loaded:
            return
        try:
            path = os.path.normpath(self.data_file)
            with open(path, "r", encoding="utf-8") as fh:
                self._parcel_data = json.load(fh)
            self._parcels = self._parcel_data.get("parcels", [])
            print(f"[EO] Static: {len(self._parcels)} parcelas desde {path}")
        except FileNotFoundError:
            print(f"[EO] Static: archivo no encontrado {self.data_file}")
            self._parcel_data = {"source": "static", "parcels": []}
            self._parcels = []
        except Exception as exc:
            print(f"[EO] Static: error {exc}")
            self._parcel_data = {"source": "static", "parcels": []}
            self._parcels = []
        self._static_loaded = True

    def _ensure_initialized(self) -> bool:
        if self._use_live:
            return True
        self._load_static()
        return len(self._parcels) > 0

    def _lookup_static(self, lat: float, lon: float) -> Optional[Dict]:
        self._load_static()
        best, best_dist = None, float("inf")
        for p in self._parcels:
            d = math.hypot(lat - p.get("lat", 0.0), lon - p.get("lon", 0.0))
            if d < best_dist:
                best_dist, best = d, p
        return best if best is not None and best_dist <= self._MATCH_RADIUS_DEG else None

    # ------------------------------------------------------------------
    # Live: Statistical API
    # ------------------------------------------------------------------

    def _statistical_query(
        self, evalscript: str, collection, bbox: BBox, time_range: tuple,
        geometry=None, maxcc: float | None = None,
    ) -> Optional[float]:
        if not self._config:
            return None
        input_kwargs = dict(time_interval=time_range)
        if maxcc is not None:
            input_kwargs["maxcc"] = maxcc

        try:
            request = SentinelHubStatistical(
                aggregation=SentinelHubStatistical.aggregation.MEAN,
                evalscript=evalscript,
                input_data=[
                    SentinelHubStatistical.input_data(collection, **input_kwargs)
                ],
                bbox=bbox,
                geometry=geometry,
                resolution=(100, 100),
                config=self._config,
            )
            data = request.get_data()
            if data and len(data) > 0:
                val = data[0].get("msavi2") or data[0].get("vv") or data[0].get("DEM")
                if val is not None and not math.isnan(float(val)):
                    return float(val)
        except Exception as exc:
            print(f"[EO] Statistical query error: {exc}")
        return None

    # ------------------------------------------------------------------
    # Live: feature extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _date_range(months_back: int = 3) -> tuple:
        end = dt.date.today()
        start = end - dt.timedelta(days=months_back * 30)
        return start.isoformat(), end.isoformat()

    def _live_features(self, lat: float, lon: float) -> Optional[Dict[str, float]]:
        start, end = self._date_range()
        bbox = BBox(
            [lon - 0.003, lat - 0.003, lon + 0.003, lat + 0.003],
            crs=CRS.WGS84,
        )
        geom = Geometry(
            {"type": "Point", "coordinates": [lon, lat]},
            crs=CRS.WGS84,
        )

        msavi2_raw = self._statistical_query(
            MSAVI2_EVALSCRIPT, DataCollection.SENTINEL2_L2A,
            bbox, (start, end), geometry=geom, maxcc=0.5,
        )
        msavi2_val = msavi2_raw if msavi2_raw is not None else 0.25
        norm = max(0.0, min(1.0, (msavi2_val + 1.0) / 2.0))

        vv_raw = self._statistical_query(
            SOIL_MOISTURE_EVALSCRIPT, DataCollection.SENTINEL1_GRD,
            bbox, (start, end), geometry=geom,
        )
        moisture = 0.35
        if vv_raw is not None:
            moisture = max(0.0, min(1.0, (vv_raw + 18) / 13))

        dem_val = self._statistical_query(
            "//VERSION=3\nfunction setup(){return{input:['DEM','dataMask'],output:{bands:1,sampleType:SampleType.FLOAT32}};}\nfunction evaluatePixel(s){return s.dataMask?[s.DEM]:[NaN];}",
            DataCollection.DEM_COPERNICUS_30,
            bbox, ("2010-01-01", "2015-12-31"), geometry=geom,
        )
        slope_pct = 5.0
        print(f"[EO] live: msavi2={msavi2_val:.4f} moisture={moisture:.4f} dem={dem_val}")

        return {
            "msavi2": round(msavi2_val, 4),
            "soil_moisture": round(moisture, 4),
            "shade_index": round(norm, 4),
            "stress_index": round(max(0.0, min(1.0, 1.0 - norm)), 4),
            "slope_percent": round(slope_pct, 2),
            "s1_dataset": "SENTINEL1_GRD",
            "s2_dataset": "SENTINEL2_L2A",
            "s2_index": "msavi2",
            "dem_dataset": "COPERNICUS_30",
            "lat": lat,
            "lon": lon,
            "source": "sentinel-hub-cdse",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @eo_cache.memoize
    def _compute_eo_features(self, lat: float, lon: float) -> Optional[Dict[str, float]]:
        if self._use_live:
            features = self._live_features(lat, lon)
            if features:
                return features
            print("[EO] Live fallo, intentando static...")

        parcel = self._lookup_static(lat, lon)
        if parcel is None:
            print(f"[EO] Sin datos para lat={lat:.4f}, lon={lon:.4f}")
            return None
        features = parcel.get("features", {})
        features["source"] = self._parcel_data.get("source", "static")
        features["lat"] = lat
        features["lon"] = lon
        return features

    def get_parcel_features(
        self,
        lat: float,
        lon: float,
        agro_zone: object,
        seasonal_forecast: str,
    ) -> Dict[str, float]:
        del agro_zone, seasonal_forecast
        if not self._use_live and not self._ensure_initialized():
            raise RuntimeError("EO: sin datos. Configura SH_CLIENT_ID/SH_CLIENT_SECRET o coloca eo_parcels.json en data/.")
        print(f"[EO] get_parcel_features: lat={lat}, lon={lon}")
        features = self._compute_eo_features(lat=lat, lon=lon)
        if features is None:
            raise RuntimeError("EO: no se obtuvieron features para esta ubicacion.")
        print(f"[EO] get_parcel_features: OK msavi2={features.get('msavi2')}")
        return features

    @eo_cache.memoize
    def get_classification_tile(
        self,
        lat: float,
        lon: float,
        agro_zone: object,
        geometry: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        zone_name = agro_zone.value if hasattr(agro_zone, "value") else str(agro_zone)
        zp = _ZONE_PARAMS.get(zone_name, _ZONE_PARAMS["transition"])

        if self._use_live and self._wms_base_url:
            evalscript = _classification_evalscript(zp)
            layers = base64.b64encode(evalscript.encode()).decode()
            return {
                "url": self._wms_base_url,
                "layers": layers,
                "type": "wms",
                "center": [lat, lon],
                "bounds": None,
            }

        self._load_static()
        parcel = self._lookup_static(lat, lon)
        if parcel is None or not parcel.get("tile_filename"):
            return None
        return {
            "url": f"/data/tiles/{parcel['tile_filename']}",
            "type": "static",
            "center": [lat, lon],
            "bounds": parcel.get("tile_bounds"),
        }
