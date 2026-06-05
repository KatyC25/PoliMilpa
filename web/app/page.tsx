"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";

const brandLogo = "/assets/logo-polimilpa.png";
const nicaraguaMap = "/assets/nicaragua.svg";
const API = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://polimilpabackend.onrender.com").replace(/\/+$/, "");

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
    title: "Z1 — Húmedo de Altura",
    subtitle: "Jinotega, Matagalpa",
    temp_range: "18° – 28°C",
    rainfall: "1200 – 2000 mm/año",
    season: "Mayo – Julio",
    rainy_season: "Mayo – Octubre",
    weather: { title: "Lluvias regulares", forecast: "Favorable.", days: [
      { day: "Hoy", icon: "fa-cloud-rain", temp: "24°/18°" },
      { day: "Mar", icon: "fa-cloud-rain", temp: "25°/18°" },
      { day: "Mié", icon: "fa-cloud-rain", temp: "24°/18°" },
      { day: "Jue", icon: "fa-cloud", temp: "25°/18°" },
      { day: "Vie", icon: "fa-sun", temp: "26°/19°" },
    ], note: "Temporada estable." },
  },
  sur: {
    title: "Z2 — Corredor Seco",
    subtitle: "Madriz, Estelí, N. Segovia, León, Chinandega",
    temp_range: "25° – 35°C",
    rainfall: "600 – 1000 mm/año",
    season: "Mayo – Junio",
    rainy_season: "Mayo – Octubre",
    weather: { title: "Época seca", forecast: "Planificar riego.", days: [
      { day: "Hoy", icon: "fa-sun", temp: "28°/19°" },
      { day: "Mar", icon: "fa-sun", temp: "29°/20°" },
      { day: "Mié", icon: "fa-sun", temp: "29°/20°" },
      { day: "Jue", icon: "fa-cloud-sun", temp: "28°/19°" },
      { day: "Vie", icon: "fa-sun", temp: "30°/21°" },
    ], note: "Poca lluvia." },
  },
  centro: {
    title: "Z3 — Caribe Subhúmedo",
    subtitle: "RACCN, RACCS, Río San Juan",
    temp_range: "24° – 30°C",
    rainfall: "2500 – 4000 mm/año",
    season: "Abril – Julio",
    rainy_season: "Abril – Diciembre",
    weather: { title: "Lluvia frecuente", forecast: "Muy favorable.", days: [
      { day: "Hoy", icon: "fa-cloud-rain", temp: "26°/21°" },
      { day: "Mar", icon: "fa-cloud-rain", temp: "26°/21°" },
      { day: "Mié", icon: "fa-cloud-rain", temp: "25°/20°" },
      { day: "Jue", icon: "fa-cloud-rain", temp: "26°/21°" },
      { day: "Vie", icon: "fa-cloud-sun", temp: "27°/22°" },
    ], note: "Precipitaciones regulares." },
  },
  occidente: {
    title: "Z4 — Zona de Transición",
    subtitle: "Managua, Masaya, Granada, Carazo, Rivas, Boaco, Chontales",
    temp_range: "22° – 32°C",
    rainfall: "800 – 1400 mm/año",
    season: "Mayo – Julio",
    rainy_season: "Mayo – Octubre",
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
  const [view, setView] = useState<'map' | 'results'>('map');

  const selectZone = useCallback((zoneId: string) => {
    setView('results');
    setSelectedZone(zoneId);
    setLoading(true);
    setRec(null);

    fetch(`${API}/v1/zones/${zoneId}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) setRec({ ...FALLBACK_REC[zoneId], ...data });
        else setRec(FALLBACK_REC[zoneId] ?? null);
      })
      .catch(() => setRec(FALLBACK_REC[zoneId] ?? null))
      .finally(() => setLoading(false));
  }, []);

  const goBack = useCallback(() => {
    setView('map');
    setSelectedZone(null);
    setRec(null);
    attached.current = false;
  }, []);

  const [satData] = useState<{ loading: boolean }>({ loading: false });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const zone = params.get("zone");
    if (zone && (zone === "norte" || zone === "sur" || zone === "centro" || zone === "occidente")) {
      selectZone(zone);
    }
  }, [selectZone]);

  useEffect(() => {
    const obj = svgRef.current;
    if (!obj || attached.current) return;

    const onLoad = () => {
      attached.current = true;
      const doc = obj.contentDocument;
      if (!doc) return;

      const paths = doc.querySelectorAll("path[id]");
      paths.forEach((path) => {
        const el = path as SVGPathElement;
        const zoneId = DEPT_ZONE[el.id];
        if (!zoneId) return;

        el.style.cursor = "pointer";
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          selectZone(zoneId);
        });
      });
    };

    obj.addEventListener("load", onLoad);
    if (obj.contentDocument?.readyState === "complete") onLoad();
    return () => obj.removeEventListener("load", onLoad);
  }, [selectZone, view]);

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
    for (const path of doc.querySelectorAll("path[id]")) {
      const el = path as SVGPathElement;
      const zoneId = DEPT_ZONE[el.id];
      if (!zoneId) continue;
      if (zoneId === targetZone && !firstPath) {
        firstPath = el;
      }
    }

    if (firstPath) {
      firstPath.style.outline = `3px solid ${ZONE_COLORS[targetZone] ?? "#999"}`;
      firstPath.style.outlineOffset = "2px";
      activePathRef.current = firstPath;
    }
  }, [selectedZone]);

  return (
    <main className="app-shell" id="inicio">
      {view === 'map' ? (
        <>
          <header className="topbar">
            <a className="brand" href="https://poli-milpa.vercel.app" aria-label="PoliMilpa">
              <Image className="brand-logo" src={brandLogo} alt="PoliMilpa" width={44} height={44} priority />
              <span className="brand-name">PoliMilpa</span>
            </a>
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
        </>
      ) : (
        <div className="results-view">
          <button className="results-back" onClick={goBack}>
            <i className="fa-solid fa-arrow-left" /> Volver a zonas
          </button>

          {loading ? (
            <div className="dash-loading" style={{ minHeight: 200 }}>
              <i className="fa-solid fa-circle-notch fa-spin" />
              <span>Cargando datos de la zona...</span>
            </div>
          ) : rec ? (
            <div className="zone-detail">
              <div className="zone-hero">
                <div className="zone-hero-top">
                  <h1>{rec.title}</h1>
                  <span className="zone-hero-badge" style={{ backgroundColor: ZONE_COLORS[selectedZone ?? ""] ?? "#999" }}>
                    <i className="fa-solid fa-circle-check" />
                    Zona seleccionada
                  </span>
                </div>
                <p className="zone-subtitle">{rec.subtitle ?? ""}</p>
              </div>

              {rec.nino_alert && (
                <div className={`zone-nino zone-nino--${rec.nino_alert.level}`}>
                  <div className="zone-nino-icon">
                    <i className={`fa-solid ${rec.nino_alert.level === "seco" ? "fa-sun" : rec.nino_alert.level === "humedo" ? "fa-cloud-rain" : "fa-circle-check"}`} />
                  </div>
                  <div className="zone-nino-body">
                    <strong>{rec.nino_alert.label as string}</strong>
                    <p>{rec.nino_alert.message as string}</p>
                    {rec.nino_alert.disclaimer && (
                      <span className="zone-nino-disclaimer">{rec.nino_alert.disclaimer as string}</span>
                    )}
                  </div>
                </div>
              )}

              {rec.fos_windows && (() => {
                const all = [
                  ...(rec.fos_windows.activas || []),
                  ...(rec.fos_windows.proximas || []),
                  ...(rec.fos_windows.expiradas || []),
                  ...(rec.fos_windows.no_aplica || []),
                ];
                if (all.length === 0) return null;
                return (
                  <div className="zone-fos">
                    <div className="zone-fos-header">
                      <i className="fa-solid fa-calendar-check" />
                      <h2>Ventanas de siembra (FOS MAG 2026)</h2>
                    </div>
                    <div className="zone-fos-grid">
                      {all.map((w: any) => {
                        const statusCls = w.status === "activa" ? "active" : w.status === "proxima" ? "upcoming" : "closed";
                        const tag = w.status === "activa" ? "Activa" : w.status === "proxima" ? "Próxima" : w.status === "expirada" ? "Cerrada" : "N/A";
                        const tagCls = w.status === "activa" ? "active" : w.status === "proxima" ? "upcoming" : "";
                        let date = "—";
                        if (w.status === "activa") date = `${w.inicio} – ${w.fin}`;
                        else if (w.status === "proxima") date = `En ${w.dias_restantes} días`;
                        return (
                          <div key={w.fos_key} className="zone-fos-row">
                            <span className={`zone-fos-dot ${statusCls}`} />
                            <span className="zone-fos-crop">{w.crop}</span>
                            <span className={`zone-fos-date ${tagCls}`}>{date}</span>
                            <span className={`zone-fos-tag ${tagCls}`}>{tag}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              <div className="main-crops">
                <div className="main-crops-header">
                  <i className="fa-solid fa-seedling" />
                  <h2>Cultivos principales</h2>
                </div>
                <div className="main-crops-grid">
                  <div className="main-crop-card">
                    <i className="fa-solid fa-leaf" />
                    <div>
                      <span className="main-crop-label">Cultivo de renta</span>
                      <span className="main-crop-name">{rec.rent_crop || "—"}</span>
                    </div>
                  </div>
                  <div className="main-crop-card">
                    <i className="fa-solid fa-wheat-awn" />
                    <div>
                      <span className="main-crop-label">Cultivo estable</span>
                      <span className="main-crop-name">{rec.food_crop || "—"}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="climate-block">
                <div className="climate-block-header">
                  <i className="fa-solid fa-cloud-sun" />
                  <h2>Clima de la zona</h2>
                </div>
                <div className="climate-grid-2x2">
                  <div className="climate-card">
                    <i className="fa-solid fa-temperature-high" />
                    <span className="climate-card-label">Temperatura</span>
                    <span className="climate-card-value">{rec.temp_range || "—"}</span>
                  </div>
                  <div className="climate-card">
                    <i className="fa-solid fa-droplet" />
                    <span className="climate-card-label">Lluvia anual</span>
                    <span className="climate-card-value">{rec.rainfall || "—"}</span>
                  </div>
                  <div className="climate-card">
                    <i className="fa-solid fa-calendar" />
                    <span className="climate-card-label">Temporada de lluvias</span>
                    <span className="climate-card-value">{rec.rainy_season || "—"}</span>
                  </div>
                  <div className="climate-card">
                    <i className="fa-solid fa-seedling" />
                    <span className="climate-card-label">Época de siembra</span>
                    <span className="climate-card-value">{rec.season || "—"}</span>
                  </div>
                </div>
              </div>

              {rec.actions && rec.actions.length > 0 && (
                <div className="zone-actions">
                  <div className="zone-actions-header">
                    <i className="fa-solid fa-circle-check" />
                    <h2>Acciones esta semana</h2>
                  </div>
                  <div className="zone-actions-grid">
                    {(rec.actions as any[]).map((action: any, i: number) => (
                      <div key={i} className="zone-action-card">
                        <div className="zone-action-icon"><i className={`fa-solid ${action.icon}`} /></div>
                        <div>
                          <span className="zone-action-title">{action.title}</span>
                          <p className="zone-action-desc">{action.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {rec.weather && rec.weather.days && (
                <div className="zone-forecast">
                  <div className="zone-forecast-header">
                    <i className="fa-solid fa-cloud-sun" />
                    <h2>Pronóstico</h2>
                    <span>{rec.weather.forecast || rec.weather.title || ""}</span>
                  </div>
                  <div className="zone-forecast-days">
                    {(rec.weather.days as any[]).map((day: any, i: number) => (
                      <div key={i} className="zone-forecast-day">
                        <span className="zone-forecast-day-name">{day.day}</span>
                        <i className={`fa-solid ${day.icon}`} />
                        <span className="zone-forecast-day-temp">{day.temp}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="sat-section">
                <div className="sat-header">
                  <i className="fa-solid fa-satellite" />
                  <h2>Pulso satelital</h2>
                </div>
                {satData.loading ? (
                  <div className="sat-shimmer">
                    <i className="fa-solid fa-circle-notch fa-spin" />
                    <span>Cargando datos satelitales...</span>
                  </div>
                ) : (
                  <div className="sat-fallback">
                    <i className="fa-solid fa-info-circle" />
                    <span>
                      Datos satelitales disponibles para técnicos y cooperativas
                    </span>
                  </div>
                )}
              </div>

              <div className="zone-footer">
                <div className="zone-footer-line" />
                <p>
                  Plataforma PoliMilpa — Monitoreo satelital para la agricultura
                  nicaragüense
                </p>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </main>
  );
}
