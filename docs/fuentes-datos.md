# Fuentes de datos recomendadas

## Copernicus y satelital
1. Sentinel-2 SR
- Uso: cobertura vegetal, MSAVI2, vigor.
- Acceso rapido: Sentinel Hub CDSE via Statistical API (`SENTINEL2_L2A`).

2. Sentinel-1 GRD
- Uso: informacion de suelo bajo nubosidad, proxy de humedad.
- Acceso rapido: Sentinel Hub CDSE via Statistical API (`SENTINEL1_GRD`).

3. Copernicus DEM GLO-30
- Uso: pendiente, escorrentia, estabilidad de ladera.
- Acceso rapido: Sentinel Hub CDSE via Statistical API (`COPERNICUS_30`).

## API oficial Copernicus (cuando escales)
- Copernicus Data Space Ecosystem: catalogo y descarga de productos Sentinel.
- Sentinel Hub APIs: procesamiento y tiles para produccion.

## Fuentes nacionales Nicaragua
1. INETER
- Variables: lluvia, temperatura, pronostico, series historicas.
- Uso: ajustar reglas estacionales por zona.

2. INTA
- Variables: calendarios de siembra, variedades por territorio.
- Uso: catalogo de combinaciones policultivo por zona.

3. Cooperativas (ej. CECOCAFEN, SOPPEXCCA)
- Variables: parcelas, validaciones de campo, ventanas de siembra.
- Uso: calibracion y evidencia de impacto.

## Recomendacion de integracion
- MVP hackathon: Sentinel Hub CDSE + C3S + reglas + validacion de tecnico.
- Post-hackathon: integrar INETER/INTA en una tabla maestra de reglas.
