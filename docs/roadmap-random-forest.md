# Random Forest en Agroni (fase 2)

## Objetivo
Mejorar la precision de recomendacion reemplazando parte de reglas fijas por un modelo supervisado.

## Etiquetas iniciales sugeridas
- Clase de cobertura: cafe_sombra, cacao, suelo_desnudo, alimentario.
- Aptitud de siembra: apto, esperar, no_apto.

## Features base
- MSAVI2 (Sentinel-2).
- VV/VH y derivados SAR (Sentinel-1).
- Pendiente y altitud (DEM Copernicus).
- Precipitacion acumulada 7/15 dias (INETER o CHIRPS si no hay feed directo).

## Pipeline
1. Recolectar muestras etiquetadas con cooperativas.
2. Entrenar Random Forest baseline.
3. Validar por zona agroclimatica (no mezclar todas sin segmentar).
4. Publicar modelo versionado y comparar contra motor de reglas.

## KPI minimo para presentacion
- Accuracy por clase.
- F1 para clase `apto`.
- Mejora porcentual respecto a baseline de reglas.
