# Arquitectura MVP Agroni

## Objetivo tecnico (hackathon)
Construir un flujo funcional que genere recomendaciones de policultivo por parcela usando datos satelitales y reglas agroclimaticas.

## Componentes
1. Ingesta satelital: Google Earth Engine (GEE) con colecciones Sentinel y DEM.
2. Motor de decision: API FastAPI con reglas por zona agroclimatica.
3. Entrega: mensaje corto para WhatsApp/SMS.
4. Validacion: tecnico de cooperativa compara recomendacion con observacion de campo.

## Flujo
1. Se recibe parcela (poligono o punto) y zona agroclimatica.
2. GEE calcula variables semanales: humedad proxy, cobertura/sombra, pendiente.
3. API calcula score y recomienda combinacion renta + alimentario.
4. Se emite salida Verde/Amarillo/Rojo + texto accionable.

## Capas minimas
- Capa 1: Sentinel-2 SR (MSAVI2 y cobertura vegetal).
- Capa 2: Copernicus DEM GLO-30 (pendiente y riesgo de escorrentia).
- Capa 3: Sentinel-1 GRD (condicion de humedad en alta nubosidad).

## Roadmap corto
- Fase 1: reglas expertas por zona (actual MVP).
- Fase 2: Random Forest para ajustar clasificacion por parcela.
- Fase 3: activacion de alertas automatizadas por WhatsApp.
