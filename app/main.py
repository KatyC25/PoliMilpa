from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Farmer, PublicDemoCase
from app.schemas import (
    AIAdvisoryInput, AIAdvisoryResponse, AgroZone,
    AutoParcelInput, FarmerCreate, FarmerResponse,
    LoginInput, MapTileInput, MapTileResponse,
    ParcelInput, PublicDemoCaseResponse,
    RecommendationResponse, TokenResponse,
    UserResponse, ZoneInfoResponse,
)
from app.services.ai_service import ai_service
from app.services.auth_service import AuthService, UserIdentity
from app.services.c3s_client import C3SClient
from app.services.gee_client import GEEClient
from app.services.ml_service import MLService
from app.services.rules_engine import recommend, ZONE_CATALOG
from app.services.area_utils import compute_area

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    area_m2, area_manzanas = compute_area(farmer.geometry)
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
        geometry=farmer.geometry,
        technician_username=farmer.technician_username,
        is_active=farmer.is_active,
        area_m2=area_m2,
        area_manzanas=area_manzanas,
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
        geometry=payload.geometry,
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
    payload: FarmerUpdate = Body(...),
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

    if payload.farmer_code is not None:
        farmer.farmer_code = payload.farmer_code

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
    if payload.geometry is not None:
        farmer.geometry = payload.geometry
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
        use_c3s = payload.seasonal_forecast is None
        seasonal_source = "manual" if not use_c3s else "c3s"
        seasonal_forecast = payload.seasonal_forecast

        if not gee_client._ensure_initialized():
            raise RuntimeError("GEE: No se pudo inicializar Earth Engine.")

        with ThreadPoolExecutor(max_workers=2) as pool:
            gee_future = pool.submit(
                gee_client.get_parcel_features,
                lat=payload.lat,
                lon=payload.lon,
                agro_zone=payload.agro_zone,
                seasonal_forecast=seasonal_forecast or "normal",
            )
            if use_c3s:
                c3s_future = pool.submit(
                    c3s_client.get_seasonal_forecast,
                    lat=payload.lat,
                    lon=payload.lon,
                )

            futures = [gee_future]
            if use_c3s:
                futures.append(c3s_future)

            for future in as_completed(futures):
                exc = future.exception()
                if exc is not None:
                    raise exc

            features = gee_future.result()
            if use_c3s:
                seasonal_forecast = c3s_future.result()
    except RuntimeError as exc:
        print(f"[503] generate_auto_recommendation fallo: {exc}")
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
        msavi2=features.get("msavi2", 0.0),
    )

    result = recommend(rules_payload)
    adjustment = ml_service.predict_adjustment(result["debug_scores"])
    result["debug_scores"]["model_adjustment"] = adjustment["model_adjustment"]
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
    result["debug_scores"]["msavi2"] = features.get("msavi2", 0.0)
    result["debug_scores"]["slope_percent"] = features["slope_percent"]
    result["debug_scores"]["soil_moisture"] = features["soil_moisture"]
    result["debug_scores"]["shade_index"] = features["shade_index"]
    result["debug_scores"]["stress_index"] = features["stress_index"]
    result["data_source"] = features.get("source", "unknown")

    return RecommendationResponse(**result)


@app.post("/v1/recommendations/auto/map", response_model=MapTileResponse)
def generate_recommendation_map_tiles(
    payload: MapTileInput,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
) -> MapTileResponse:
    del user
    tile = gee_client.get_classification_tile(
        lat=payload.lat,
        lon=payload.lon,
        agro_zone=payload.agro_zone,
        geometry=payload.geometry,
    )
    if tile is None:
        print(f"[503] generate_recommendation_map_tiles: tile nulo para lat={payload.lat}, lon={payload.lon}")
        raise HTTPException(
            status_code=503,
            detail="No se pudo generar el mapa de clasificacion. Verifica GEE.",
        )
    return MapTileResponse(url=tile["url"], center=tile["center"], zoom=16)


_ZONE_INFO = {
    "norte": {
        "title": "Z1 — Húmedo de Altura",
        "subtitle": "Jinotega, Matagalpa",
        "temp_range": "18° – 28°C",
        "rainfall": "1200 – 2000 mm/año",
        "season": "Mayo – Julio",
        "rainy_season": "Mayo – Octubre",
        "actions": [
            {"icon": "fa-tree", "title": "Sembrar con sombra", "description": "Mantener árboles de sombra para regular temperatura."},
            {"icon": "fa-leaf", "title": "Fertilización orgánica", "description": "Aplicar abono orgánico al inicio de lluvias."},
            {"icon": "fa-droplet", "title": "Monitorear drenaje", "description": "Evitar encharcamientos en épocas lluviosas."},
        ],
        "weather": {"title": "Lluvias regulares", "forecast": "Condiciones favorables para la siembra.", "days": [
            {"day": "Hoy", "icon": "fa-cloud-rain", "temp": "24°/18°"},
            {"day": "Mar", "icon": "fa-cloud-rain", "temp": "25°/18°"},
            {"day": "Mié", "icon": "fa-cloud-rain", "temp": "24°/18°"},
            {"day": "Jue", "icon": "fa-cloud", "temp": "25°/18°"},
            {"day": "Vie", "icon": "fa-sun", "temp": "26°/19°"},
        ], "note": "Temporada de lluvias estable."},
    },
    "sur": {
        "title": "Z2 — Corredor Seco",
        "subtitle": "Madriz, Estelí, N. Segovia, León, Chinandega",
        "temp_range": "25° – 35°C",
        "rainfall": "600 – 1000 mm/año",
        "season": "Mayo – Junio",
        "rainy_season": "Mayo – Octubre",
        "actions": [
            {"icon": "fa-droplet", "title": "Riego complementario", "description": "Aplicar riego en momentos críticos."},
            {"icon": "fa-leaf", "title": "Mulch", "description": "Cubrir suelo para retener humedad."},
            {"icon": "fa-sun", "title": "Cosecha de agua", "description": "Captar agua de lluvia para riego."},
        ],
        "weather": {"title": "Sequía esperada", "forecast": "Planificar riego.", "days": [
            {"day": "Hoy", "icon": "fa-sun", "temp": "28°/19°"},
            {"day": "Mar", "icon": "fa-sun", "temp": "29°/20°"},
            {"day": "Mié", "icon": "fa-sun", "temp": "29°/20°"},
            {"day": "Jue", "icon": "fa-cloud-sun", "temp": "28°/19°"},
            {"day": "Vie", "icon": "fa-sun", "temp": "30°/21°"},
        ], "note": "Temperaturas altas, poca lluvia."},
    },
    "centro": {
        "title": "Z3 — Caribe Subhúmedo",
        "subtitle": "RACCN, RACCS, Río San Juan",
        "temp_range": "24° – 30°C",
        "rainfall": "2500 – 4000 mm/año",
        "season": "Abril – Julio",
        "rainy_season": "Abril – Diciembre",
        "actions": [
            {"icon": "fa-leaf", "title": "Mantener humedad", "description": "Monitorear nivel de humedad del suelo."},
            {"icon": "fa-droplet", "title": "Drenaje", "description": "Evitar exceso de agua."},
            {"icon": "fa-tree", "title": "Sombra parcial", "description": "Establecer árboles de sombra."},
        ],
        "weather": {"title": "Lluvia frecuente", "forecast": "Muy favorable.", "days": [
            {"day": "Hoy", "icon": "fa-cloud-rain", "temp": "26°/21°"},
            {"day": "Mar", "icon": "fa-cloud-rain", "temp": "26°/21°"},
            {"day": "Mié", "icon": "fa-cloud-rain", "temp": "25°/20°"},
            {"day": "Jue", "icon": "fa-cloud-rain", "temp": "26°/21°"},
            {"day": "Vie", "icon": "fa-cloud-sun", "temp": "27°/22°"},
        ], "note": "Precipitaciones regulares."},
    },
    "occidente": {
        "title": "Z4 — Zona de Transición",
        "subtitle": "Managua, Masaya, Granada, Carazo, Rivas, Boaco, Chontales",
        "temp_range": "22° – 32°C",
        "rainfall": "800 – 1400 mm/año",
        "season": "Mayo – Julio",
        "rainy_season": "Mayo – Octubre",
        "actions": [
            {"icon": "fa-leaf", "title": "Monitorear humedad", "description": "Mantener equilibrio riego-drenaje."},
            {"icon": "fa-tree", "title": "Agroforestería", "description": "Integrar árboles con cultivos."},
            {"icon": "fa-droplet", "title": "Preparar variabilidad", "description": "Sistemas de riego y drenaje flexibles."},
        ],
        "weather": {"title": "Condiciones variables", "forecast": "Equilibrio lluvia-sequía.", "days": [
            {"day": "Hoy", "icon": "fa-cloud-sun", "temp": "26°/19°"},
            {"day": "Mar", "icon": "fa-cloud-rain", "temp": "25°/18°"},
            {"day": "Mié", "icon": "fa-cloud-sun", "temp": "26°/19°"},
            {"day": "Jue", "icon": "fa-sun", "temp": "27°/20°"},
            {"day": "Vie", "icon": "fa-cloud-sun", "temp": "27°/19°"},
        ], "note": "Transición con menos precipitaciones."},
    },
}


_ZONE_TO_AGRO = {
    "norte": AgroZone.HIGHLAND_HUMID,
    "sur": AgroZone.DRY_CORRIDOR,
    "centro": AgroZone.SUBHUMID_CARIBBEAN,
    "occidente": AgroZone.TRANSITION,
}

_CROP_DISPLAY = {
    "cafe": "Café", "cacao": "Cacao",
    "maiz": "Maíz", "frijol": "Frijol",
    "sorgo": "Sorgo", "yuca": "Yuca",
    "ajonjoli": "Ajonjolí", "mani": "Maní",
    "platano": "Plátano",
    "papa": "Papa", "arroz": "Arroz",
    "tabaco": "Tabaco", "chiltoma": "Chiltoma",
    "tomate": "Tomate",
    "quequisque": "Quequisque", "malanga": "Malanga",
}

def _display_crop(name: str) -> str:
    return _CROP_DISPLAY.get(name, name.title())

@app.get("/v1/zones/{zone_id}", response_model=ZoneInfoResponse)
def get_zone_info(zone_id: str) -> ZoneInfoResponse:
    info = _ZONE_INFO.get(zone_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Zona '{zone_id}' no encontrada")

    agro_key = _ZONE_TO_AGRO.get(zone_id)
    if agro_key:
        catalog = ZONE_CATALOG.get(agro_key, {})
        rent_list = catalog.get("rent", [])
        food_list = catalog.get("food", [])
        rent_crop = _display_crop(rent_list[0]) if rent_list else ""
        food_crop = _display_crop(food_list[0]) if food_list else ""
        info = {
            **info,
            "rent_crop": rent_crop,
            "food_crop": food_crop,
            "main_crop": {
                "name": rent_crop,
                "status": "Recomendado",
                "description": f"Cultivo de renta principal para {info['title']}.",
                "benefits": [],
            },
            "alt_crop": {
                "name": food_crop,
                "status": "Alternativa",
                "description": f"Cultivo alimenticio complementario para {info['title']}.",
                "benefits": [],
            },
        }

    return ZoneInfoResponse(zone_id=zone_id, **info)


@app.post("/v1/recommendations/ai-advisory", response_model=AIAdvisoryResponse)
def generate_ai_advisory(
    payload: AIAdvisoryInput,
    user: UserIdentity = Depends(require_roles("superadmin", "admin", "tecnico")),
) -> AIAdvisoryResponse:
    del user
    result = ai_service.generate_advisory(payload)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="No se pudo generar advisory IA. Verifica GEMINI_API_KEY en .env",
        )
    return result
