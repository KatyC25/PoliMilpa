"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Image from "next/image";
import dynamic from "next/dynamic";
import { useAuth } from "../../../../lib/auth-context";
import { getFarmer, getAutoRecommendation, fetchMapTiles, getAIAdvisory, type Farmer, type Recommendation } from "../../../../lib/api";

const FarmMap = dynamic(() => import("../../../../components/FarmMap"), {
  ssr: false,
  loading: () => (
    <div className="farm-map-skeleton">
      <i className="fa-solid fa-map" />
      <span>Cargando mapa...</span>
    </div>
  ),
});

const brandLogo = "/assets/logo-polimilpa.png";

const TRAFFIC_META: Record<string, { label: string; icon: string; color: string }> = {
  verde: { label: "Apto para siembra", icon: "fa-circle-check", color: "#1a9850" },
  amarillo: { label: "Precaución — esperar 7 días", icon: "fa-circle-exclamation", color: "#fdae61" },
  rojo: { label: "No apto para siembra", icon: "fa-circle-xmark", color: "#d73027" },
};

const C3S_META: Record<string, { label: string; icon: string; color: string }> = {
  dry: { label: "Pronóstico seco", icon: "fa-sun", color: "#f08a24" },
  normal: { label: "Pronóstico normal", icon: "fa-cloud", color: "#26a69a" },
  wet: { label: "Pronóstico húmedo", icon: "fa-cloud-rain", color: "#1a8bc0" },
};

const ZONE_LABELS: Record<string, string> = {
  highland_humid: "Húmedo de Altura",
  dry_corridor: "Corredor Seco",
  subhumid_caribbean: "Caribe Subhúmedo",
  transition: "Zona de Transición",
};

const ZONE_COLORS: Record<string, string> = {
  highland_humid: "#56b34f",
  dry_corridor: "#eb5757",
  subhumid_caribbean: "#f2c94c",
  transition: "#f2994a",
};

function LoadingSkeleton() {
  return (
    <main className="dash-shell">
      <div className="dash-loading">
        <i className="fa-solid fa-circle-notch fa-spin" />
        <span>Analizando finca...</span>
      </div>
    </main>
  );
}

export default function FarmerDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { token, loading: authLoading, user } = useAuth();
  const [farmer, setFarmer] = useState<Farmer | null>(null);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [tileUrl, setTileUrl] = useState<string | null>(null);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [aiAdvisory, setAiAdvisory] = useState<{ advisory: string; whatsapp_preview: string } | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [showTech, setShowTech] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.replace("/login");
      return;
    }

    const id = Number(params.id);
    if (!id) {
      setError("ID de finca inválido");
      setFetching(false);
      return;
    }

    let cancelled = false;

    getFarmer(id)
      .then(async (f) => {
        if (cancelled) return;
        if (!f) {
          setError("Finca no encontrada");
          return;
        }
        setFarmer(f);

        if (f.lat && f.lon) {
          const [r, tile] = await Promise.all([
            getAutoRecommendation(f.farmer_code, f.municipality, f.department, f.agro_zone, f.lat, f.lon),
            fetchMapTiles(f.lat, f.lon, f.geometry).catch(() => null),
          ]);
          if (!cancelled) {
            setRec(r);
            if (tile) setTileUrl(tile.url);
          }

          if (r && !cancelled) {
            setAiLoading(true);
            setAiError(false);
            getAIAdvisory({
              parcel_id: f.farmer_code,
              traffic_light: r.traffic_light,
              global_score: typeof r.debug_scores?.global === "number" ? r.debug_scores.global : 0,
              rent_crop: r.recommendations[0]?.rent_crop ?? "",
              food_crop: r.recommendations[0]?.food_crop ?? "",
              window: r.recommended_window,
              msavi2: typeof r.debug_scores?.msavi2 === "number" ? r.debug_scores.msavi2 : 0,
              slope_percent: typeof r.debug_scores?.slope_percent === "number" ? r.debug_scores.slope_percent : 0,
              soil_moisture: typeof r.debug_scores?.soil_moisture === "number" ? r.debug_scores.soil_moisture : 0,
              seasonal_forecast: typeof r.debug_scores?.seasonal_forecast_used === "string" ? r.debug_scores.seasonal_forecast_used : "normal",
              zone: f.agro_zone,
              department: f.department,
              municipality: f.municipality,
            }).then((ai) => {
              if (!cancelled && ai) {
                setAiAdvisory(ai);
                setEditText(ai.advisory);
              } else {
                setAiError(true);
              }
            }).catch(() => {
              if (!cancelled) setAiError(true);
            }).finally(() => {
              if (!cancelled) setAiLoading(false);
            });
          }
        }
      })
      .catch(() => {
        if (!cancelled) setError("Error al cargar la finca");
      })
      .finally(() => {
        if (!cancelled) setFetching(false);
      });

    return () => { cancelled = true; };
  }, [token, authLoading, params.id, router]);

  const handleBack = () => router.push("/dashboard");

  if (authLoading || fetching) {
    return <LoadingSkeleton />;
  }

  const c3sValue = rec?.debug_scores?.seasonal_forecast_used;
  const zoneColor = farmer ? ZONE_COLORS[farmer.agro_zone] ?? "#999" : "#999";
  const zoneLabel = farmer ? ZONE_LABELS[farmer.agro_zone] ?? farmer.agro_zone : "";

  return (
    <main className="dash-shell">
      <header className="dash-topbar">
        <div className="dash-brand">
          <Image src={brandLogo} alt="PoliMilpa" width={36} height={36} style={{ width: "auto", height: "1.8rem" }} />
          <span className="dash-brand-name">PoliMilpa</span>
        </div>
        <div className="dash-nav">
          {user && <span className="dash-user"><i className="fa-regular fa-user" /> {user.full_name}</span>}
          <button className="dash-back" onClick={handleBack} type="button">
            <i className="fa-solid fa-arrow-left" /> Volver
          </button>
        </div>
      </header>

      <section className="dash-content">
        {error ? (
          <div className="dash-empty">
            <i className="fa-solid fa-triangle-exclamation" />
            <p>{error}</p>
            <button className="dash-retry" onClick={handleBack} type="button">Volver</button>
          </div>
        ) : farmer ? (
          <>
            <div className="fd-header">
              <div className="fd-header-left">
                <h1>{farmer.farm_name}</h1>
                <p className="fd-header-sub">
                  {farmer.full_name} &middot; {farmer.municipality}, {farmer.department}
                </p>
              </div>
              <span className="fd-zone-badge" style={{ backgroundColor: zoneColor }}>
                {zoneLabel}
              </span>
            </div>

            <div className="fd-grid">
              <div className="fd-left">
                <div className="fd-map-wrap">
                  <FarmMap
                    geometry={farmer.geometry ?? null}
                    lat={farmer.lat}
                    lon={farmer.lon}
                    trafficLight={rec?.traffic_light ?? null}
                    tileUrl={tileUrl}
                  />
                </div>

                {rec ? (
                  <div className="rec-section">
                    <div
                      className="rec-traffic"
                      style={{ backgroundColor: TRAFFIC_META[rec.traffic_light]?.color ?? "#999" }}
                    >
                      <i className={`fa-solid ${TRAFFIC_META[rec.traffic_light]?.icon}`} />
                      <div className="rec-traffic-text">
                        <strong>{TRAFFIC_META[rec.traffic_light]?.label}</strong>
                        <span>Score global: {(typeof rec.debug_scores?.global === "number" ? rec.debug_scores.global : 0).toFixed(3)}</span>
                      </div>
                    </div>

                    <div className="rec-crops">
                      <div className="rec-crop-card">
                        <div className="rec-crop-icon" style={{ backgroundColor: "#e8f5e9" }}>
                          <i className="fa-solid fa-seedling" style={{ color: "#2e7d32" }} />
                        </div>
                        <div className="rec-crop-body">
                          <span className="rec-crop-label">Cultivo de renta</span>
                          <span className="rec-crop-name">{rec.recommendations[0]?.rent_crop ?? "—"}</span>
                        </div>
                      </div>
                      <div className="rec-crop-card">
                        <div className="rec-crop-icon" style={{ backgroundColor: "#fff3e0" }}>
                          <i className="fa-solid fa-bowl-food" style={{ color: "#e65100" }} />
                        </div>
                        <div className="rec-crop-body">
                          <span className="rec-crop-label">Cultivo alimentario</span>
                          <span className="rec-crop-name">{rec.recommendations[0]?.food_crop ?? "—"}</span>
                        </div>
                      </div>
                      <div className="rec-crop-card">
                        <div className="rec-crop-icon" style={{ backgroundColor: "#e3f2fd" }}>
                          <i className="fa-solid fa-clock" style={{ color: "#1565c0" }} />
                        </div>
                        <div className="rec-crop-body">
                          <span className="rec-crop-label">Ventana de siembra</span>
                          <span className="rec-crop-name">{rec.recommended_window.replace(/_/g, " ")}</span>
                        </div>
                      </div>
                    </div>

                    <div className="ai-card">
                      <div className="ai-card-head">
                        <div className="ai-card-head-left">
                          <i className="fa-solid fa-wand-magic-sparkles" />
                          <h3>Asistente IA</h3>
                        </div>
                        {aiLoading && <i className="fa-solid fa-circle-notch fa-spin ai-spin" />}
                      </div>

                      {aiAdvisory ? (
                        <>
                          {editing ? (
                            <textarea
                              className="ai-textarea"
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              rows={6}
                            />
                          ) : (
                            <p className="ai-text">{aiAdvisory.advisory}</p>
                          )}

                          <div className="ai-actions">
                            <button
                              type="button"
                              className={`ai-btn ${editing ? "ai-btn-save" : "ai-btn-edit"}`}
                              onClick={() => {
                                if (editing) {
                                  setAiAdvisory({ ...aiAdvisory, advisory: editText });
                                  setEditing(false);
                                } else {
                                  setEditText(aiAdvisory.advisory);
                                  setEditing(true);
                                }
                              }}
                            >
                              <i className={`fa-solid ${editing ? "fa-check" : "fa-pen"}`} />
                              {editing ? "Guardar cambios" : "Editar texto"}
                            </button>

                            {farmer.contact_phone && (
                              <a
                                href={`https://wa.me/${farmer.contact_phone.replace(/[^0-9]/g, "")}?text=${encodeURIComponent(editText)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="ai-btn ai-btn-whatsapp"
                              >
                                <i className="fa-brands fa-whatsapp" />
                                Enviar por WhatsApp
                              </a>
                            )}
                          </div>

                          <div className="ai-whatsapp-preview">
                            <i className="fa-brands fa-whatsapp" />
                            <div>
                              <strong>Vista previa WhatsApp</strong>
                              <p>{aiAdvisory.whatsapp_preview}</p>
                            </div>
                          </div>
                        </>
                      ) : aiLoading ? (
                        <div className="ai-generating">
                          <div className="ai-generating-dots">
                            <span /><span /><span />
                          </div>
                          <span>Generando recomendación con IA...</span>
                        </div>
                      ) : (
                        <div className="ai-empty">
                          <i className="fa-solid fa-cloud-exclamation" />
                          <div>
                            <strong>No disponible</strong>
                            <p>{aiError ? "Error al generar el análisis con IA. Verifica la conexión." : "Completa el análisis satelital primero."}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="rec-advisory-card">
                      <div className="rec-advisory-head">
                        <i className="fa-solid fa-file-lines" />
                        <h3>Análisis de la parcela</h3>
                      </div>
                      <p>{rec.advisory_text}</p>
                    </div>

                    <div className="tech-card">
                      <button
                        type="button"
                        className="tech-card-toggle"
                        onClick={() => setShowTech(!showTech)}
                      >
                        <i className="fa-solid fa-microchip" />
                        <span>Datos técnicos del análisis</span>
                        <i className={`fa-solid fa-chevron-down tech-chevron ${showTech ? "open" : ""}`} />
                      </button>

                      {showTech && rec.debug_scores && (
                        <div className="tech-card-body">
                          <div className="tech-grid">
                            {Object.entries(rec.debug_scores).map(([k, v]) => (
                              <div key={k} className="tech-item">
                                <span className="tech-label">{k}</span>
                                <span className={`tech-value ${typeof v === "string" ? "tech-str" : ""}`}>
                                  {typeof v === "number" ? v.toFixed(3) : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                          {rec.data_source && (
                            <p className="tech-source">
                              <i className="fa-solid fa-satellite" /> Fuente: {rec.data_source}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rec-empty">
                    <i className="fa-solid fa-cloud" />
                    <p>No se pudo generar la recomendación. Verifica que GEE esté habilitado.</p>
                  </div>
                )}
              </div>

              <div className="fd-right">
                <div className="side-card">
                  <div className="side-card-head">
                    <i className="fa-solid fa-circle-info" />
                    <h3>Datos de la finca</h3>
                  </div>
                  <dl className="side-list">
                    <div className="side-list-row">
                      <dt>Código</dt>
                      <dd>{farmer.farmer_code}</dd>
                    </div>
                    <div className="side-list-row">
                      <dt>Productor</dt>
                      <dd>{farmer.full_name}</dd>
                    </div>
                    <div className="side-list-row">
                      <dt>Municipio</dt>
                      <dd>{farmer.municipality}</dd>
                    </div>
                    <div className="side-list-row">
                      <dt>Departamento</dt>
                      <dd>{farmer.department}</dd>
                    </div>
                    <div className="side-list-row">
                      <dt>Zona</dt>
                      <dd>
                        <span className="mini-badge" style={{ backgroundColor: zoneColor }}>
                          {zoneLabel}
                        </span>
                      </dd>
                    </div>
                    <div className="side-list-row">
                      <dt>Teléfono</dt>
                      <dd>
                        {farmer.contact_phone ? (
                          <a href={`tel:${farmer.contact_phone}`} className="side-phone">
                            {farmer.contact_phone}
                          </a>
                        ) : "—"}
                      </dd>
                    </div>
                  </dl>
                </div>

                {c3sValue && typeof c3sValue === "string" && C3S_META[c3sValue] ? (
                  <div className="side-card c3s-card" style={{ borderLeftColor: C3S_META[c3sValue].color }}>
                    <div className="side-card-head">
                      <i className={`fa-solid ${C3S_META[c3sValue].icon}`} style={{ color: C3S_META[c3sValue].color }} />
                      <h3>Pronóstico de precipitación</h3>
                    </div>
                    <div className="c3s-body">
                      <span className="c3s-badge" style={{ backgroundColor: C3S_META[c3sValue].color }}>
                        {C3S_META[c3sValue].label}
                      </span>
                      <p className="c3s-footnote">
                        <i className="fa-solid fa-cloud" /> C3S / ECMWF
                      </p>
                    </div>
                  </div>
                ) : null}

                <div className="side-card support-card-side">
                  <div className="side-card-head">
                    <i className="fa-solid fa-headset" />
                    <h3>¿Necesitas ayuda?</h3>
                  </div>
                  <p className="support-text">Si tienes dudas sobre la recomendación, contacta al equipo de PoliMilpa.</p>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
