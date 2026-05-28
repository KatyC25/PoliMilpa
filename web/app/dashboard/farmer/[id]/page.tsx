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
          const rPromise = getAutoRecommendation(f.farmer_code, f.municipality, f.department, f.agro_zone, f.lat, f.lon);
          const tilePromise = fetchMapTiles(f.lat, f.lon, f.geometry, f.agro_zone).catch(() => null);

          const r = await rPromise;
          if (!cancelled) setRec(r);

          tilePromise.then((tile) => {
            if (!cancelled && tile) setTileUrl(tile.url);
          });

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
            <div className="fd3-head">
              <div>
                <h1 className="fd3-head-name">{farmer.farm_name}</h1>
                <p className="fd3-head-sub">
                  {farmer.full_name} &middot; {farmer.municipality}, {farmer.department} &middot; {farmer.farmer_code}
                </p>
              </div>
              <span className="fd3-zone" style={{ backgroundColor: zoneColor }}>
                {zoneLabel}
              </span>
            </div>

            <div className="fd3-body">
              <div className="fd3-left">
                <div className="fd3-map">
                  <FarmMap
                    geometry={farmer.geometry ?? null}
                    lat={farmer.lat}
                    lon={farmer.lon}
                    trafficLight={rec?.traffic_light ?? null}
                    tileUrl={tileUrl}
                  />
                </div>

                {rec ? (
                  <>
                    <div
                      className="fd3-traffic"
                      style={{ backgroundColor: TRAFFIC_META[rec.traffic_light]?.color ?? "#999" }}
                    >
                      <i className={`fa-solid ${TRAFFIC_META[rec.traffic_light]?.icon}`} />
                      <div className="fd3-traffic-body">
                        <strong>{TRAFFIC_META[rec.traffic_light]?.label}</strong>
                        <span>Score global: {(typeof rec.debug_scores?.global === "number" ? rec.debug_scores.global : 0).toFixed(3)}</span>
                      </div>
                    </div>

                    <div className="fd3-crops">
                      <div className="fd3-crop fd3-crop--renta">
                        <div className="fd3-crop-icon"><i className="fa-solid fa-seedling" /></div>
                        <span className="fd3-crop-label">Renta</span>
                        <span className="fd3-crop-name">{rec.recommendations[0]?.rent_crop ?? "—"}</span>
                      </div>
                      <div className="fd3-crop fd3-crop--food">
                        <div className="fd3-crop-icon"><i className="fa-solid fa-bowl-food" /></div>
                        <span className="fd3-crop-label">Alimentario</span>
                        <span className="fd3-crop-name">{rec.recommendations[0]?.food_crop ?? "—"}</span>
                      </div>
                      <div className="fd3-crop fd3-crop--window">
                        <div className="fd3-crop-icon"><i className="fa-solid fa-calendar-check" /></div>
                        <span className="fd3-crop-label">Ventana</span>
                        <span className="fd3-crop-name">{rec.recommended_window.replace(/_/g, " ")}</span>
                      </div>
                    </div>
                  </>
                  ) : null}

                    {rec && (
                      <div className="fd3-tech">
                        <button
                          type="button"
                          className="fd3-tech-toggle"
                          onClick={() => setShowTech(!showTech)}
                        >
                          <i className="fa-solid fa-microchip" />
                          <span>Datos técnicos</span>
                          <i className={`fa-solid fa-chevron-down fd3-tech-chevron ${showTech ? "open" : ""}`} />
                        </button>

                        {showTech && rec.debug_scores && (
                          <div className="fd3-tech-body">
                            <div className="fd3-tech-grid">
                              {Object.entries(rec.debug_scores).map(([k, v]) => (
                                <div key={k} className="fd3-tech-item">
                                  <span className="fd3-tech-label">{k}</span>
                                  <span className={`fd3-tech-val ${typeof v === "string" ? "fd3-tech-str" : ""}`}>
                                    {typeof v === "number" ? v.toFixed(3) : String(v)}
                                  </span>
                                </div>
                              ))}
                            </div>
                            {rec.data_source && (
                              <p className="fd3-tech-src">
                                <i className="fa-solid fa-satellite" /> Fuente: {rec.data_source}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
              </div>

              <div className="fd3-right">
                {rec ? (
                  <>
                    <div className="fd3-ai">
                      <div className="fd3-ai-head">
                        <i className="fa-solid fa-wand-magic-sparkles" />
                        <h3>Asistente IA</h3>
                        {aiLoading && <i className="fa-solid fa-circle-notch fa-spin fd3-ai-spin" />}
                      </div>

                      {aiAdvisory ? (
                        <>
                          {editing ? (
                            <textarea
                              className="fd3-ai-input"
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              rows={6}
                            />
                          ) : (
                            <p className="fd3-ai-text">{aiAdvisory.advisory}</p>
                          )}

                          <div className="fd3-ai-actions">
                            <button
                              type="button"
                              className={`fd3-ai-btn ${editing ? "fd3-ai-btn--save" : "fd3-ai-btn--edit"}`}
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
                              {editing ? "Guardar" : "Editar"}
                            </button>

                            {farmer.contact_phone && (
                              <a
                                href={`https://wa.me/${farmer.contact_phone.replace(/[^0-9]/g, "")}?text=${encodeURIComponent(editText)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="fd3-ai-btn fd3-ai-btn--wa"
                              >
                                <i className="fa-brands fa-whatsapp" />
                                WhatsApp
                              </a>
                            )}
                          </div>
                        </>
                      ) : aiLoading ? (
                        <div className="fd3-ai-wait">
                          <span className="fd3-ai-dots"><span /><span /><span /></span>
                          <span>Generando...</span>
                        </div>
                      ) : (
                        <div className="fd3-ai-empty">
                          <i className="fa-solid fa-cloud-exclamation" />
                          <div>
                            <strong>No disponible</strong>
                            <p>{aiError ? "Error al generar análisis con IA." : "Completa el análisis satelital primero."}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="fd3-info">
                      <div className="fd3-info-head">
                        <i className="fa-solid fa-circle-info" />
                        <h3>Datos de la finca</h3>
                      </div>
                      <dl className="fd3-info-list">
                        <div><dt>Productor</dt><dd>{farmer.full_name}</dd></div>
                        <div><dt>Ubicación</dt><dd>{farmer.municipality}, {farmer.department}</dd></div>
                        <div><dt>Zona</dt><dd><span className="fd3-mini-badge" style={{ backgroundColor: zoneColor }}>{zoneLabel}</span></dd></div>
                        {farmer.contact_phone && (
                          <div><dt>Teléfono</dt><dd><a href={`tel:${farmer.contact_phone}`} className="fd3-phone">{farmer.contact_phone}</a></dd></div>
                        )}
                      </dl>
                    </div>

                    <div className="fd3-card">
                      <div className="fd3-card-head">
                        <i className="fa-solid fa-file-lines" />
                        <h3>Análisis de la parcela</h3>
                      </div>
                      <p className="fd3-card-text">{rec.advisory_text}</p>
                    </div>

                    {c3sValue && typeof c3sValue === "string" && C3S_META[c3sValue] ? (
                      <div className="fd3-c3s">
                        <div className="fd3-c3s-head">
                          <i className={`fa-solid ${C3S_META[c3sValue].icon}`} style={{ color: C3S_META[c3sValue].color }} />
                          <h3>Pronóstico de precipitación</h3>
                        </div>
                        <div className="fd3-c3s-body">
                          <span className="fd3-c3s-badge" style={{ backgroundColor: C3S_META[c3sValue].color }}>
                            {C3S_META[c3sValue].label}
                          </span>
                          <p className="fd3-c3s-src"><i className="fa-solid fa-cloud" /> C3S / ECMWF</p>
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="dash-empty">
                    <i className="fa-solid fa-cloud" />
                    <p>No se pudo generar la recomendación.</p>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
