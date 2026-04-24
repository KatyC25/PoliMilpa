from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Farmer, PublicDemoCase
from app.schemas import (
    AutoParcelInput,
    FarmerCreate,
    FarmerResponse,
    FarmerUpdate,
    LoginInput,
    ParcelInput,
    PublicDemoCaseResponse,
    RecommendationResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService, UserIdentity
from app.services.c3s_client import C3SClient
from app.services.gee_client import GEEClient
from app.services.ml_service import MLService
from app.services.rules_engine import recommend

load_dotenv()

app = FastAPI(title=settings.app_name, version=settings.app_version)
gee_client = GEEClient()
c3s_client = C3SClient()
ml_service = MLService()
auth_service = AuthService()
bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> UserIdentity:
    if credentials is None:
        raise _unauthorized("Falta token de acceso")
    try:
        return auth_service.decode_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError) as exc:
        raise _unauthorized("Token invalido o expirado") from exc


def require_roles(*roles: str):
    def _dependency(user: UserIdentity = Depends(get_current_user)) -> UserIdentity:
        if not auth_service.has_required_role(user.role, roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta accion",
            )
        return user

    return _dependency


def _farmer_to_response(farmer: Farmer) -> FarmerResponse:
    return FarmerResponse(
        id=farmer.id,
        farmer_code=farmer.farmer_code,
        full_name=farmer.full_name,
        contact_phone=farmer.contact_phone,
        farm_name=farmer.farm_name,
        municipality=farmer.municipality,
        department=farmer.department,
        agro_zone=farmer.agro_zone,
        lat=farmer.lat,
        lon=farmer.lon,
        technician_username=farmer.technician_username,
        is_active=farmer.is_active,
    )


def _validate_technician_scope(user: UserIdentity, technician_username: str) -> None:
    if user.role == "tecnico" and technician_username != user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un tecnico solo puede gestionar agricultores asignados a su usuario",
        )


def _public_case_to_response(case: PublicDemoCase) -> PublicDemoCaseResponse:
    return PublicDemoCaseResponse(
        id=case.id,
        case_code=case.case_code,
        title=case.title,
        municipality=case.municipality,
        department=case.department,
        agro_zone=case.agro_zone,
        lat=case.lat,
        lon=case.lon,
        recommendation_text=case.recommendation_text,
        whatsapp_text=case.whatsapp_text,
        map_reference=case.map_reference,
    )


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/v1/demo/cases", response_model=list[PublicDemoCaseResponse])
def list_public_demo_cases(
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[PublicDemoCaseResponse]:
    query = db.query(PublicDemoCase)
    if active_only:
        query = query.filter(PublicDemoCase.is_active.is_(True))

    cases = query.order_by(PublicDemoCase.id.desc()).all()
    return [_public_case_to_response(case) for case in cases]


@app.get("/v1/demo/cases/{case_code}", response_model=PublicDemoCaseResponse)
def get_public_demo_case(
    case_code: str,
    db: Session = Depends(get_db),
) -> PublicDemoCaseResponse:
    case = (
        db.query(PublicDemoCase)
        .filter(PublicDemoCase.case_code == case_code)
        .filter(PublicDemoCase.is_active.is_(True))
        .first()
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso demo no encontrado",
        )
    return _public_case_to_response(case)


@app.post("/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginInput, request: Request) -> TokenResponse:
    user = auth_service.authenticate(
        payload.username,
        payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if user is None:
        raise _unauthorized("Credenciales invalidas")
    token = auth_service.create_access_token(user)
    return TokenResponse(access_token=token)


@app.get("/v1/auth/me", response_model=UserResponse)
def me(user: UserIdentity = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        username=user.username,
        role=user.role,
        full_name=user.full_name,
    )


@app.post(
    "/v1/farmers", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED
)
def create_farmer(
    payload: FarmerCreate,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
    db: Session = Depends(get_db),
) -> FarmerResponse:
    existing = (
        db.query(Farmer).filter(Farmer.farmer_code == payload.farmer_code).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un agricultor con ese farmer_code",
        )

    assigned_technician = payload.technician_username or user.username
    _validate_technician_scope(user, assigned_technician)

    farmer = Farmer(
        farmer_code=payload.farmer_code,
        full_name=payload.full_name,
        contact_phone=payload.contact_phone,
        farm_name=payload.farm_name,
        municipality=payload.municipality,
        department=payload.department,
        agro_zone=payload.agro_zone.value,
        lat=payload.lat,
        lon=payload.lon,
        technician_username=assigned_technician,
        is_active=True,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return _farmer_to_response(farmer)


@app.get("/v1/farmers", response_model=list[FarmerResponse])
def list_farmers(
    municipality: str | None = Query(default=None),
    department: str | None = Query(default=None),
    agro_zone: str | None = Query(default=None),
    technician_username: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
    db: Session = Depends(get_db),
) -> list[FarmerResponse]:
    query = db.query(Farmer)

    if user.role == "tecnico":
        query = query.filter(Farmer.technician_username == user.username)

    effective_technician = technician_username
    if user.role == "tecnico":
        effective_technician = user.username
    if effective_technician:
        query = query.filter(Farmer.technician_username == effective_technician)
    if municipality:
        query = query.filter(Farmer.municipality == municipality)
    if department:
        query = query.filter(Farmer.department == department)
    if agro_zone:
        query = query.filter(Farmer.agro_zone == agro_zone)
    if active_only:
        query = query.filter(Farmer.is_active.is_(True))

    farmers = query.order_by(Farmer.id.desc()).all()
    return [_farmer_to_response(farmer) for farmer in farmers]


@app.get("/v1/farmers/{farmer_id}", response_model=FarmerResponse)
def get_farmer(
    farmer_id: int,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
    db: Session = Depends(get_db),
) -> FarmerResponse:
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if farmer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agricultor no encontrado"
        )

    _validate_technician_scope(user, farmer.technician_username)
    return _farmer_to_response(farmer)


@app.put("/v1/farmers/{farmer_id}", response_model=FarmerResponse)
def update_farmer(
    farmer_id: int,
    payload: FarmerUpdate,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
    db: Session = Depends(get_db),
) -> FarmerResponse:
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if farmer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agricultor no encontrado"
        )

    _validate_technician_scope(user, farmer.technician_username)

    if payload.technician_username is not None:
        _validate_technician_scope(user, payload.technician_username)
        farmer.technician_username = payload.technician_username

    if payload.full_name is not None:
        farmer.full_name = payload.full_name
    if payload.contact_phone is not None:
        farmer.contact_phone = payload.contact_phone
    if payload.farm_name is not None:
        farmer.farm_name = payload.farm_name
    if payload.municipality is not None:
        farmer.municipality = payload.municipality
    if payload.department is not None:
        farmer.department = payload.department
    if payload.agro_zone is not None:
        farmer.agro_zone = payload.agro_zone.value
    if payload.lat is not None:
        farmer.lat = payload.lat
    if payload.lon is not None:
        farmer.lon = payload.lon
    if payload.is_active is not None:
        farmer.is_active = payload.is_active

    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return _farmer_to_response(farmer)


@app.delete("/v1/farmers/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer(
    farmer_id: int,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
    db: Session = Depends(get_db),
) -> None:
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if farmer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agricultor no encontrado"
        )

    _validate_technician_scope(user, farmer.technician_username)
    db.delete(farmer)
    db.commit()


@app.post("/v1/recommendations", response_model=RecommendationResponse)
def generate_recommendation(
    payload: ParcelInput,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
) -> RecommendationResponse:
    del user
    result = recommend(payload)
    return RecommendationResponse(**result)


@app.post("/v1/recommendations/auto", response_model=RecommendationResponse)
def generate_auto_recommendation(
    payload: AutoParcelInput,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
) -> RecommendationResponse:
    del user
    try:
        seasonal_forecast = c3s_client.get_seasonal_forecast(
            lat=payload.lat,
            lon=payload.lon,
        )
        seasonal_source = "c3s"

        features = gee_client.get_parcel_features(
            lat=payload.lat,
            lon=payload.lon,
            agro_zone=payload.agro_zone,
            seasonal_forecast=seasonal_forecast,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    rules_payload = ParcelInput(
        parcel_id=payload.parcel_id,
        municipality=payload.municipality,
        department=payload.department,
        agro_zone=payload.agro_zone,
        slope_percent=features["slope_percent"],
        soil_moisture=features["soil_moisture"],
        shade_index=features["shade_index"],
        stress_index=features["stress_index"],
        seasonal_forecast=seasonal_forecast,
    )

    result = recommend(rules_payload)
    adjustment = ml_service.predict_adjustment(result["debug_scores"])
    result["debug_scores"]["confidence_delta"] = adjustment["confidence_delta"]
    result["debug_scores"]["model_version"] = adjustment["model_version"]
    result["debug_scores"]["seasonal_source"] = seasonal_source
    result["debug_scores"]["seasonal_forecast_used"] = seasonal_forecast
    result["debug_scores"]["c3s_dataset"] = c3s_client.dataset
    result["debug_scores"]["c3s_variable"] = c3s_client.variable
    result["debug_scores"]["c3s_leadtime_month"] = c3s_client.leadtime_month
    result["debug_scores"]["s1_dataset"] = features.get("s1_dataset", "unknown")
    result["debug_scores"]["s2_dataset"] = features.get("s2_dataset", "unknown")
    result["debug_scores"]["s2_index"] = features.get("s2_index", "unknown")
    result["debug_scores"]["dem_dataset"] = features.get("dem_dataset", "unknown")
    result["data_source"] = features.get("source", "unknown")

    return RecommendationResponse(**result)
