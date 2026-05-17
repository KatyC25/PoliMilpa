"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";

const brandLogo = "/assets/logo-polimilpa.png";
const nicaraguaMap = "/assets/nicaragua.svg";
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const DEPT_ZONE: Record<string, string> = {
  "NI-JI": "norte", "NI-MT": "norte",
  "NI-MD": "sur", "NI-ES": "sur", "NI-NS": "sur", "NI-LE": "sur", "NI-CI": "sur",
  "NI-AN": "centro", "NI-AS": "centro", "NI-SJ": "centro",
  "NI-MN": "occidente", "NI-MS": "occidente", "NI-GR": "occidente",
  "NI-CA": "occidente", "NI-RI": "occidente", "NI-BO": "occidente", "NI-CO": "occidente",
};

const zoneGroups = [
  { id: "norte", title: "Z1 — Húmedo de Altura", description: "Jinotega, Matagalpa. Alta humedad y lluvias abundantes.", icon: "fa-cloud-rain", color: "green" },
  { id: "sur", title: "Z2 — Corredor Seco", description: "Madriz, Estelí, N. Segovia, León, Chinandega. Condiciones secas.", icon: "fa-solid fa-temperature-high", color: "red" },
  { id: "centro", title: "Z3 — Caribe Subhúmedo", description: "RACCN, RACCS, Río San Juan. Humedad constante.", icon: "fa-cloud-sun", color: "amber" },
  { id: "occidente", title: "Z4 — Zona de Transición", description: "Managua, Masaya, Granada, Carazo, Rivas, Boaco, Chontales. Condiciones variables.", icon: "fa-solid fa-arrows-left-right", color: "orange" },
];

const legendItems = [
  { label: "Z1 — Húmedo de Altura", color: "#56b34f" },
  { label: "Z2 — Corredor Seco", color: "#eb5757" },
  { label: "Z3 — Caribe Subhúmedo", color: "#f2c94c" },
  { label: "Z4 — Zona de Transición", color: "#f2994a" },
];

const ZONE_COLORS: Record<string, string> = {
  norte: "#56b34f", sur: "#eb5757", centro: "#f2c94c", occidente: "#f2994a",
};

const FALLBACK_REC: Record<string, any> = {
  norte: {
    title: "Z1 — Húmedo de Altura", subtitle: "Condiciones para siembra",
    main_crop: { name: "Café", status: "Recomendado", description: "Clima fresco ideal para café.", benefits: ["Excelente calidad"] },
    alt_crop: { name: "Maíz", status: "Alternativa", description: "Cultivo tradicional.", benefits: [] },
    actions: [
      { icon: "fa-tree", title: "Sembrar con sombra", description: "Regular temperatura con sombra." },
      { icon: "fa-leaf", title: "Fertilización", description: "Abono orgánico al inicio." },
    ],
    weather: { title: "Lluvias regulares", forecast: "Favorable.", days: [
      { day: "Hoy", icon: "fa-cloud-rain", temp: "24°/18°" },
      { day: "Mar", icon: "fa-cloud-rain", temp: "25°/18°" },
      { day: "Mié", icon: "fa-cloud-rain", temp: "24°/18°" },
      { day: "Jue", icon: "fa-cloud", temp: "25°/18°" },
      { day: "Vie", icon: "fa-sun", temp: "26°/19°" },
    ], note: "Temporada estable." },
  },
  sur: {
    title: "Z2 — Corredor Seco", subtitle: "Condiciones para siembra",
    main_crop: { name: "Sorgo", status: "Recomendado", description: "Resistente a sequía.", benefits: ["Alta resistencia"] },
    alt_crop: { name: "Frijol caupí", status: "Alternativa", description: "Tolerante a estrés.", benefits: [] },
    actions: [
      { icon: "fa-droplet", title: "Riego", description: "Complementar en momentos críticos." },
      { icon: "fa-leaf", title: "Mulch", description: "Retener humedad." },
    ],
    weather: { title: "Sequía", forecast: "Planificar riego.", days: [
      { day: "Hoy", icon: "fa-sun", temp: "28°/19°" },
      { day: "Mar", icon: "fa-sun", temp: "29°/20°" },
      { day: "Mié", icon: "fa-sun", temp: "29°/20°" },
      { day: "Jue", icon: "fa-cloud-sun", temp: "28°/19°" },
      { day: "Vie", icon: "fa-sun", temp: "30°/21°" },
    ], note: "Poca lluvia." },
  },
  centro: {
    title: "Z3 — Caribe Subhúmedo", subtitle: "Condiciones para siembra",
    main_crop: { name: "Cacao", status: "Recomendado", description: "Humedad constante.", benefits: ["Excelente adaptación"] },
    alt_crop: { name: "Yuca", status: "Alternativa", description: "Opción resistente.", benefits: [] },
    actions: [
      { icon: "fa-leaf", title: "Humedad", description: "Monitorear nivel." },
      { icon: "fa-droplet", title: "Drenaje", description: "Evitar exceso." },
    ],
    weather: { title: "Lluvia frecuente", forecast: "Muy favorable.", days: [
      { day: "Hoy", icon: "fa-cloud-rain", temp: "26°/21°" },
      { day: "Mar", icon: "fa-cloud-rain", temp: "26°/21°" },
      { day: "Mié", icon: "fa-cloud-rain", temp: "25°/20°" },
      { day: "Jue", icon: "fa-cloud-rain", temp: "26°/21°" },
      { day: "Vie", icon: "fa-cloud-sun", temp: "27°/22°" },
    ], note: "Precipitaciones regulares." },
  },
  occidente: {
    title: "Z4 — Zona de Transición", subtitle: "Condiciones para siembra",
    main_crop: { name: "Café", status: "Recomendado", description: "Condiciones mixtas.", benefits: ["Equilibrio humedad"] },
    alt_crop: { name: "Frijol", status: "Alternativa", description: "Versátil.", benefits: [] },
    actions: [
      { icon: "fa-leaf", title: "Monitorear", description: "Equilibrio riego-drenaje." },
      { icon: "fa-tree", title: "Agroforestería", description: "Integrar árboles." },
    ],
    weather: { title: "Variables", forecast: "Equilibrio.", days: [
      { day: "Hoy", icon: "fa-cloud-sun", temp: "26°/19°" },
      { day: "Mar", icon: "fa-cloud-rain", temp: "25°/18°" },
      { day: "Mié", icon: "fa-cloud-sun", temp: "26°/19°" },
      { day: "Jue", icon: "fa-sun", temp: "27°/20°" },
      { day: "Vie", icon: "fa-cloud-sun", temp: "27°/19°" },
    ], note: "Transicional." },
  },
};

export default function Home() {
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [rec, setRec] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const svgRef = useRef<HTMLObjectElement>(null);
  const activePathRef = useRef<SVGPathElement | null>(null);
  const attached = useRef(false);

  const selectZone = useCallback((zoneId: string) => {
    setSelectedZone(zoneId);
    setLoading(true);
    setRec(null);

    fetch(`${API}/v1/zones/${zoneId}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) setRec(data);
        else setRec(FALLBACK_REC[zoneId] ?? null);
      })
      .catch(() => setRec(FALLBACK_REC[zoneId] ?? null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const obj = svgRef.current;
    if (!obj || attached.current) return;

    const onLoad = () => {
      attached.current = true;
      const doc = obj.contentDocument;
      if (!doc) return;

      const paths = doc.querySelectorAll("path[id]");
      paths.forEach((path) => {
        const zoneId = DEPT_ZONE[path.id];
        if (!zoneId) return;

        path.style.cursor = "pointer";
        path.addEventListener("click", (e) => {
          e.stopPropagation();
          selectZone(zoneId);
        });
      });
    };

    obj.addEventListener("load", onLoad);
    if (obj.contentDocument?.readyState === "complete") onLoad();
    return () => obj.removeEventListener("load", onLoad);
  }, [selectZone]);

  useEffect(() => {
    const obj = svgRef.current;
    if (!obj || !selectedZone) return;
    const doc = obj.contentDocument;
    if (!doc) return;

    if (activePathRef.current) {
      activePathRef.current.style.outline = "";
      activePathRef.current.style.outlineOffset = "";
    }

    const targetZone = selectedZone;
    let firstPath: SVGPathElement | null = null;
    doc.querySelectorAll("path[id]").forEach((path) => {
      const el = path as SVGPathElement;
      const zoneId = DEPT_ZONE[el.id];
      if (!zoneId) return;
      if (zoneId === targetZone && !firstPath) {
        firstPath = el;
      }
    });

    if (firstPath) {
      firstPath.style.outline = `3px solid ${ZONE_COLORS[targetZone] ?? "#999"}`;
      firstPath.style.outlineOffset = "2px";
      activePathRef.current = firstPath;
    }
  }, [selectedZone]);

  return (
    <main className="app-shell" id="inicio">
      <header className="topbar">
        <a className="brand" href="http://127.0.0.1:5500/landing/" aria-label="PoliMilpa">
          <Image className="brand-logo" src={brandLogo} alt="PoliMilpa" width={44} height={44} priority />
          <span className="brand-name">PoliMilpa</span>
        </a>
        <nav className="topnav" aria-label="Principal">
          <a href="#inicio">Inicio</a>
          <a href="#zonas">Productores</a>
        </nav>
        <a className="primary-button" href="/login">Iniciar sesión</a>
      </header>

      <section className="platform-grid" id="zonas">
        <div className="zone-panel">
          <p className="section-kicker">Selecciona tu zona</p>
          <h2>Elige la región donde te encuentras</h2>
          <p className="section-copy">Elige en el mapa o en la lista.</p>

          <section className="zone-list" aria-label="Zonas agroclimáticas">
            {zoneGroups.map((group) => (
              <article
                className={`zone-card ${selectedZone === group.id ? "active" : ""}`}
                key={group.id}
                onClick={() => selectZone(group.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") selectZone(group.id); }}
              >
                <div className={`zone-icon ${group.color}`} aria-hidden="true">
                  <i className={`fa-solid ${group.icon}`} />
                </div>
                <div className="zone-copy">
                  <h2>{group.title}</h2>
                  <p>{group.description}</p>
                </div>
                <i className="fa-solid fa-chevron-right zone-chevron" aria-hidden="true" />
              </article>
            ))}
          </section>
        </div>

        <section className="map-panel" aria-label="Mapa de zonas agroclimáticas">
          <div className="map-frame">
            <div className="map-bg" aria-hidden="true" />
            <object
              ref={svgRef}
              className="map-object"
              data={nicaraguaMap}
              type="image/svg+xml"
              aria-label="Mapa de Nicaragua con zonas agroclimáticas"
            >
              Mapa de Nicaragua con zonas agroclimáticas
            </object>

            <div className="map-legend">
              <strong>Zonas agroclimáticas</strong>
              {legendItems.map((item) => (
                <div className="legend-row" key={item.label}>
                  <span style={{ backgroundColor: item.color }} aria-hidden="true" />
                  <small>{item.label}</small>
                </div>
              ))}
            </div>
          </div>
        </section>
      </section>

      {selectedZone && rec && !loading && (
        <section className="recommendation-panel">
          <div className="rec-header">
            <div>
              <h1>{rec.title}</h1>
              <div className="rec-badge"><i className="fa-solid fa-circle-check" /> Zona seleccionada</div>
            </div>
            <p className="rec-subtitle">{rec.subtitle}</p>
          </div>

          <div className="rec-grid">
            <div className="rec-left">
              <div className="rec-section">
                <div className="rec-section-header">
                  <i className="fa-solid fa-leaf" />
                  <h2>Esta semana te recomendamos:</h2>
                </div>
                <div className="crop-card recommended">
                  <div className="crop-image"><div className="crop-placeholder"><i className="fa-solid fa-leaf" /></div></div>
                  <div className="crop-info">
                    <h3>{rec.main_crop?.name ?? "—"}</h3>
                    <span className="crop-badge recommended">{rec.main_crop?.status ?? ""}</span>
                    <p>{rec.main_crop?.description ?? ""}</p>
                    {rec.main_crop?.benefits?.length > 0 && (
                      <div className="crop-benefits">
                        {(rec.main_crop.benefits as string[]).map((b: string, i: number) => (
                          <span key={i}><i className="fa-solid fa-check" /> {b}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="crop-card alternative">
                  <div className="crop-image"><div className="crop-placeholder"><i className="fa-solid fa-leaf" /></div></div>
                  <div className="crop-info">
                    <h3>{rec.alt_crop?.name ?? "—"}</h3>
                    <span className="crop-badge alternative">{rec.alt_crop?.status ?? ""}</span>
                    <p>{rec.alt_crop?.description ?? ""}</p>
                  </div>
                </div>
                <div className="rec-note">
                  <i className="fa-solid fa-circle-info" />
                  <span>Recomendaciones con datos satelitales (Copernicus) y climáticos.</span>
                </div>
              </div>

              <div className="rec-section">
                <h2>¿Qué puedes hacer esta semana?</h2>
                <div className="actions-grid">
                  {(rec.actions ?? []).map((a: any, i: number) => (
                    <div key={i} className="action-card">
                      <div className="action-icon"><i className={`fa-solid ${a.icon}`} /></div>
                      <h3>{a.title}</h3>
                      <p>{a.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rec-right">
              <div className="rec-section weather-section">
                <div className="weather-header">
                  <i className="fa-solid fa-cloud" />
                  <h2>Clima en tu zona</h2>
                </div>
                <h3 className="weather-title">{rec.weather?.title ?? ""}</h3>
                <p className="weather-forecast">{rec.weather?.forecast ?? ""}</p>
                <div className="forecast-days">
                  {(rec.weather?.days ?? []).map((d: any, i: number) => (
                    <div key={i} className="forecast-day">
                      <span className="day-name">{d.day}</span>
                      <i className={`fa-solid ${d.icon}`} />
                      <span className="day-temp">{d.temp}</span>
                    </div>
                  ))}
                </div>
                <div className="weather-note">
                  <i className="fa-solid fa-wave" />
                  <span>{rec.weather?.note ?? ""}</span>
                </div>
              </div>

              <div className="rec-section tech-section">
                <div className="tech-icon"><i className="fa-solid fa-user-tie" /></div>
                <h2>¿Quieres recomendaciones precisas para tu finca?</h2>
                <p>Un técnico puede analizar tu parcela.</p>
                <button type="button" className="tech-cta" onClick={() => window.location.href = "/login"}>
                  <i className="fa-solid fa-lock" /> Sin compromiso
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {selectedZone && loading && (
        <section className="recommendation-panel">
          <div className="dash-loading" style={{ minHeight: 200 }}>
            <i className="fa-solid fa-circle-notch fa-spin" />
            <span>Cargando datos de la zona...</span>
          </div>
        </section>
      )}
    </main>
  );
}
