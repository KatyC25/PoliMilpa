# agroni

Agroni es un sistema que recomienda policultivos para Nicaragua. Usa datos satelitales de Copernicus para identificar la combinacion ideal de cultivos de renta y alimentarios por finca, segun clima, terreno y temporada. Envia sugerencias por WhatsApp a productores para mejorar sus ingresos, resiliencia y seguridad alimentaria.

## MVP actual

Este repositorio ya incluye una API base en FastAPI con un motor de reglas para recomendaciones por zona agroclimatica.

### Requisitos

- Python 3.10+

### Ejecutar local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API local: `http://127.0.0.1:8000`

### Endpoints

- `GET /health`
- `POST /v1/recommendations`
- `POST /v1/recommendations/auto`

### Ejemplo de request

```bash
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

En esta version, si no hay integracion GEE activa, usa fallback reproducible para demo.

Variable opcional:

- `GEE_ENABLED=true` para activar futura integracion real.

## Siguiente paso recomendado

Conectar el endpoint con una rutina de extraccion en Google Earth Engine para que `soil_moisture`, `shade_index` y `stress_index` se calculen automaticamente desde Sentinel-1/Sentinel-2/DEM.
