# Polimilpa

API en FastAPI para generar recomendaciones productivas por parcela.

Estado actual del repo:

- Login JWT con roles (`superadmin`, `admin`, `tecnico`).
- CRUD de agricultores.
- Recomendacion manual (`/v1/recommendations`).
- Recomendacion automatica (`/v1/recommendations/auto`) con GEE + C3S.
- Persistencia local con SQLite por defecto.

## Requisitos

- Python 3.10 o superior.
- Entorno virtual (`venv`).

## Levantar el proyecto (macOS + fish)

```fish
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

La API queda en:

- `http://127.0.0.1:8000`
- Docs Swagger: `http://127.0.0.1:8000/docs`

## Variables de entorno

La base ya viene en `.env.example`. Las claves principales son:

```env
GEE_ENABLED=true
GEE_PROJECT_ID=<tu-proyecto-gcp>

C3S_ENABLED=true
C3S_DATASET=seasonal-monthly-single-levels
C3S_VARIABLE=total_precipitation
C3S_ORIGINATING_CENTRE=ecmwf
C3S_SYSTEM=51
C3S_LEADTIME_MONTH=1
C3S_DRY_THRESHOLD=0.04
C3S_WET_THRESHOLD=0.14

JWT_SECRET_KEY=<tu-clave>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=sqlite:///./polimilpa.db
```

## GEE integrado

`/v1/recommendations/auto` usa Google Earth Engine para calcular features de parcela.

Si no hay autenticacion o configuracion de GEE, el endpoint responde `503`.

Autenticacion inicial:

```fish
source .venv/bin/activate.fish
earthengine authenticate
```

Capas que se usan actualmente:

- `COPERNICUS/S2_SR_HARMONIZED` (MSAVI2)
- `COPERNICUS/S1_GRD` (VV)
- `COPERNICUS/DEM/GLO30` (pendiente)

## C3S integrado

`/v1/recommendations/auto` obtiene `seasonal_forecast` desde C3S.

Si C3S no esta activo o falla, el endpoint responde `503`.

Para C3S necesitas:

1. Cuenta en CDS con terminos aceptados del dataset `seasonal-monthly-single-levels`.
2. Archivo `~/.cdsapirc` con `url` y `key`.

## Usuarios iniciales

Si no defines `POLIMILPA_USERS_JSON`, se crean estos usuarios:

- `superadmin / superadmin123`
- `admin / admin123`
- `tecnico / tecnico123`

## Endpoints

- `GET /health`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/farmers`
- `GET /v1/farmers`
- `GET /v1/farmers/{farmer_id}`
- `PUT /v1/farmers/{farmer_id}`
- `DELETE /v1/farmers/{farmer_id}`
- `POST /v1/recommendations`
- `POST /v1/recommendations/auto`

## Pruebas

```fish
.venv/bin/python -m pytest -q
```

Por archivo:

```fish
.venv/bin/python -m pytest -q tests/test_rules_engine.py
.venv/bin/python -m pytest -q tests/test_endpoints.py
```

## Documentacion del proyecto

- `docs/arquitectura-mvp.md`
- `docs/fuentes-datos.md`
- `docs/roadmap-random-forest.md`
