# agroni

Agroni es un sistema que recomienda policultivos para Nicaragua. Usa datos satelitales de Copernicus para identificar la combinacion ideal de cultivos de renta y alimentarios por finca, segun clima, terreno y temporada. Envia sugerencias por WhatsApp a productores para mejorar sus ingresos, resiliencia y seguridad alimentaria.

## MVP actual

Este repositorio ya incluye una API base en FastAPI con un motor de reglas para recomendaciones por zona agroclimatica.

### Requisitos

- Python 3.10+

### Ejecutar local (fish)

```fish
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt

# Configuracion una sola vez
cp .env.example .env
# Edita .env con tus valores reales

uvicorn app.main:app --reload
```

API local: `http://127.0.0.1:8000`

### Endpoints

- `GET /health`
- `POST /v1/recommendations`
- `POST /v1/recommendations/auto`

### Ejemplo de request

```fish
curl -X POST "http://127.0.0.1:8000/v1/recommendations" \
	-H "Content-Type: application/json" \
	-d '{
		"parcel_id": "PAR-001",
		"municipality": "Jinotega",
		"department": "Jinotega",
		"agro_zone": "highland_humid",
		"slope_percent": 14,
		"soil_moisture": 0.62,
		"shade_index": 0.57,
		"stress_index": 0.22,
		"seasonal_forecast": "normal"
	}'
```

### Documentacion tecnica

- `docs/arquitectura-mvp.md`
- `docs/fuentes-datos.md`
- `docs/roadmap-random-forest.md`

### Endpoint automatico (paso siguiente)

`/v1/recommendations/auto` recibe coordenadas de parcela y genera features satelitales desde el cliente GEE.

En esta version, este endpoint funciona solo con Google Earth Engine (sin fallback).
Si GEE no esta configurado, responde `503` con un mensaje de configuracion.

En `/v1/recommendations/auto`, el `seasonal_forecast` se resuelve automaticamente desde C3S.
Si C3S no esta disponible, el endpoint responde `503`.

Variables recomendadas para integracion real con GEE:

- `GEE_ENABLED=true`
- `GEE_PROJECT_ID=<tu-proyecto-gcp>` (opcional, recomendado)

Variables para C3S (si quieres resolver `seasonal_forecast` automatico):

- `C3S_ENABLED=true`
- `C3S_DATASET=seasonal-monthly-single-levels`
- `C3S_VARIABLE=total_precipitation`
- `C3S_ORIGINATING_CENTRE=ecmwf`
- `C3S_SYSTEM=51`
- `C3S_LEADTIME_MONTH=1`
- `C3S_DRY_THRESHOLD=0.04`
- `C3S_WET_THRESHOLD=0.14`

Si prefieres variables directas en terminal (sin .env), en fish:

```fish
source .venv/bin/activate.fish
pip install -r requirements.txt
set -x GEE_ENABLED true
set -x GEE_PROJECT_ID tu-proyecto-gcp
earthengine authenticate

# C3S (recomendado para modo automatico estricto)
set -x C3S_ENABLED true
# Crear ~/.cdsapirc con url y token personal desde CDS
# url: https://cds.climate.copernicus.eu/api
# key: <PERSONAL-ACCESS-TOKEN>

uvicorn app.main:app --reload
```

Flujo recomendado simple:

1. Configura `.env` una sola vez.
2. Levanta con `uvicorn app.main:app --reload`.
3. Ya no necesitas exportar variables en cada corrida.

Si quieres verificar conectividad GEE antes de levantar la API:

```fish
earthengine --help
earthengine authenticate
```

Si quieres verificar C3S:

1. Inicia sesion en CDS y acepta terminos del dataset `seasonal-monthly-single-levels`.
2. Configura `~/.cdsapirc` con token personal.
3. Levanta la API con `C3S_ENABLED=true` y prueba `/v1/recommendations/auto`.

## GEE: que calcula hoy cada capa

- Sentinel-2 (`COPERNICUS/S2_SR_HARMONIZED`): MSAVI2 como proxy de vigor vegetal y sombra.
- Sentinel-1 (`COPERNICUS/S1_GRD`): VV normalizado como proxy de humedad de suelo bajo nubosidad.
- DEM Copernicus (`COPERNICUS/DEM/GLO30`): pendiente media para riesgo de escorrentia.

Con eso, el endpoint devuelve:

- `soil_moisture`
- `shade_index`
- `stress_index`
- `slope_percent`
- `data_source=gee`

Nota: en `/v1/recommendations/auto` el escenario estacional se toma desde C3S para evitar supuestos manuales.

Verificacion en respuesta API (`debug_scores`):

- `seasonal_source=c3s`
- `c3s_dataset=seasonal-monthly-single-levels`
- `c3s_variable=total_precipitation`
- `s1_dataset=COPERNICUS/S1_GRD`
- `s2_dataset=COPERNICUS/S2_SR_HARMONIZED`
- `s2_index=msavi2`
- `dem_dataset=COPERNICUS/DEM/GLO30`

## Siguiente paso recomendado

Calibrar umbrales `C3S_DRY_THRESHOLD` y `C3S_WET_THRESHOLD` por zona agroclimatica con datos historicos de campo.

## Pruebas

Ejecutar pruebas unitarias y de endpoints:

```fish
.venv/bin/python -m pytest -q
```

Ejecutar pruebas por archivo:

```fish
.venv/bin/python -m pytest -q tests/test_rules_engine.py
.venv/bin/python -m pytest -q tests/test_endpoints.py
```
