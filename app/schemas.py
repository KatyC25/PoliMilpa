from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AgroZone(str, Enum):
    HIGHLAND_HUMID = "highland_humid"
    DRY_CORRIDOR = "dry_corridor"
    SUBHUMID_CARIBBEAN = "subhumid_caribbean"
    TRANSITION = "transition"


class ParcelInput(BaseModel):
    parcel_id: str = Field(..., description="Identificador unico de parcela")
    municipality: str
    department: str
    agro_zone: AgroZone
    slope_percent: float = Field(..., ge=0, le=100)
    soil_moisture: float = Field(..., ge=0, le=1, description="Escala normalizada 0-1")
    shade_index: float = Field(
        ..., ge=0, le=1, description="0 sin sombra, 1 sombra muy densa"
    )
    stress_index: float = Field(
        ..., ge=0, le=1, description="0 saludable, 1 estres alto"
    )
    seasonal_forecast: str = Field(..., description="dry, normal o wet")


class AutoParcelInput(BaseModel):
    parcel_id: str = Field(..., description="Identificador unico de parcela")
    municipality: str
    department: str
    agro_zone: AgroZone
    lat: float
    lon: float
    seasonal_forecast: Optional[str] = Field(
        default=None,
        description="dry, normal o wet. Opcional; si no viene, se intenta resolver desde C3S",
    )


class CropRecommendation(BaseModel):
    rent_crop: str
    food_crop: str
    confidence: float
    reason: str


class RecommendationResponse(BaseModel):
    parcel_id: str
    traffic_light: str
    recommended_window: str
    recommendations: List[CropRecommendation]
    advisory_text: str
    debug_scores: Optional[Dict[str, Union[float, str]]] = None
    data_source: Optional[str] = None
