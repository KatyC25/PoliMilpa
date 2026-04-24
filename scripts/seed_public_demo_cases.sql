INSERT INTO public_demo_cases (
    case_code,
    title,
    municipality,
    department,
    agro_zone,
    lat,
    lon,
    recommendation_text,
    whatsapp_text,
    map_reference,
    is_active,
    created_at,
    updated_at
)
VALUES (
    'espinoza-001',
    'Finca Espinoza',
    'Jinotepe',
    'Carazo',
    'transition',
    11.926708,
    -86.586334,
    'Semaforo AMARILLO: sembrar frijol + maiz en zona de menor pendiente esta semana. Evitar sectores con pendiente alta y reforzar cobertura de suelo.',
    'Don Ramon, recomendacion PoliMilpa: esta semana siembra frijol + maiz en las zonas de menor pendiente. Evita laderas fuertes y conserva cobertura para retener humedad.',
    'Finca Espinoza - GEE MSAVI2 + pendiente + semaforo',
    true,
    now(),
    now()
)
ON CONFLICT (case_code) DO UPDATE
SET
    title = EXCLUDED.title,
    municipality = EXCLUDED.municipality,
    department = EXCLUDED.department,
    agro_zone = EXCLUDED.agro_zone,
    lat = EXCLUDED.lat,
    lon = EXCLUDED.lon,
    recommendation_text = EXCLUDED.recommendation_text,
    whatsapp_text = EXCLUDED.whatsapp_text,
    map_reference = EXCLUDED.map_reference,
    is_active = EXCLUDED.is_active,
    updated_at = now();

INSERT INTO public_demo_cases (
    case_code,
    title,
    municipality,
    department,
    agro_zone,
    lat,
    lon,
    recommendation_text,
    whatsapp_text,
    map_reference,
    is_active,
    created_at,
    updated_at
)
VALUES (
    'las-flores-002',
    'Finca Las Flores',
    'Terrabona',
    'Matagalpa',
    'transition',
    12.69595,
    -85.78215,
    'Semaforo AMARILLO: sembrar frijol + maiz en zonas aptas del lote y evitar sectores con mayor pendiente. Priorizar cobertura para conservar humedad y reducir escorrentia.',
    'Recomendacion PoliMilpa: esta semana priorizar frijol + maiz en areas de menor pendiente dentro de Finca Las Flores. Mantener cobertura del suelo para proteger humedad.',
    'Finca Las Flores - GEE MSAVI2 + pendiente + semaforo',
    true,
    now(),
    now()
)
ON CONFLICT (case_code) DO UPDATE
SET
    title = EXCLUDED.title,
    municipality = EXCLUDED.municipality,
    department = EXCLUDED.department,
    agro_zone = EXCLUDED.agro_zone,
    lat = EXCLUDED.lat,
    lon = EXCLUDED.lon,
    recommendation_text = EXCLUDED.recommendation_text,
    whatsapp_text = EXCLUDED.whatsapp_text,
    map_reference = EXCLUDED.map_reference,
    is_active = EXCLUDED.is_active,
    updated_at = now();
