"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Image from "next/image";
import dynamic from "next/dynamic";
import { useAuth } from "../../../../lib/auth-context";
import { getFarmer, getAutoRecommendation, type Farmer, type Recommendation, type FosWindow } from "../../../../lib/api";

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

const FOS_STATUS_META: Record<string, { label: string; cls: string }> = {
  activa: { label: "Activa", cls: "fd3-fos-tag--activa" },
  proxima: { label: "Próxima", cls: "fd3-fos-tag--proxima" },
  expirada: { label: "Cerrada", cls: "fd3-fos-tag--expirada" },
  no_aplica: { label: "No aplica", cls: "fd3-fos-tag--no_aplica" },
};

function NinoBanner({ alert }: { alert: { level: string; label: string; message: string } }) {
  if (!alert) return null;
  const levelCls = `fd3-nino--${alert.level}`;
  const icon = alert.level === "activo_nino"
    ? "fa-solid fa-triangle-exclamation"
    : alert.level === "la_nina"
    ? "fa-solid fa-cloud-rain"
    : "fa-solid fa-circle-check";
  return (
    <div className={`fd3-nino ${levelCls}`}>
      <div className="fd3-nino-icon"><i className={icon} /></div>
      <div className="fd3-nino-body">
        <strong>{alert.label}</strong>
        <p>{alert.message}</p>
      </div>
    </div>
  );
}

function FosWindows({ fos }: { fos: { activas: FosWindow[]; proximas: FosWindow[]; expiradas: FosWindow[]; no_aplica: FosWindow[] } | null | undefined }) {
  if (!fos) return null;
  const all = [...(fos.activas || []), ...(fos.proximas || []), ...(fos.expiradas || []), ...(fos.no_aplica || [])];
  if (all.length === 0) return null;
  return (
    <div className="fd3-fos">
      <div className="fd3-fos-head">
        <i className="fa-solid fa-calendar-check" />
        <h3>Ventana de siembra (FOS MAG 2026)</h3>
      </div>
      <div className="fd3-fos-grid">
        {all.map((w) => {
          const meta = FOS_STATUS_META[w.status] ?? FOS_STATUS_META["no_aplica"];
          const datesCls = w.status === "activa" ? "fd3-fos-dates--activa" : w.status === "proxima" ? "fd3-fos-dates--proxima" : "";
          const datesLabel = w.status === "activa"
            ? `${w.inicio} – ${w.fin}`
            : w.status === "proxima"
            ? `En ${w.dias_restantes} días`
            : w.status === "expirada"
            ? "Cerrada"
            : "—";
          return (
            <div key={w.fos_key} className="fd3-fos-item">
              <span className={`fd3-fos-status fd3-fos-status--${w.status}`} />
              <span className="fd3-fos-crop">{w.crop}</span>
              <span className={`fd3-fos-dates ${datesCls}`}>{datesLabel}</span>
              <span className={`fd3-fos-tag ${meta.cls}`}>{meta.label}</span>
            </div>
          );
        })}
      </div>
      <div className="fd3-fos-legend">
        <span className="fd3-fos-legend-item"><span className="fd3-fos-status fd3-fos-status--activa" /> Activa</span>
        <span className="fd3-fos-legend-item"><span className="fd3-fos-status fd3-fos-status--proxima" /> Próxima</span>
        <span className="fd3-fos-legend-item"><span className="fd3-fos-status fd3-fos-status--expirada" /> Cerrada (ventana paso)</span>
        <span className="fd3-fos-legend-item"><span className="fd3-fos-status fd3-fos-status--no_aplica" /> No aplica en zona</span>
      </div>
    </div>
  );
}

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
          const r = await getAutoRecommendation(
            f.farmer_code, f.municipality, f.department,
            f.agro_zone, f.lat, f.lon, f.geometry,
          );

          if (!cancelled) {
            setRec(r);
            if (r?.tile_url) setTileUrl(r.tile_url);
            if (r?.ai_advisory) {
              setAiAdvisory({
                advisory: r.ai_advisory,
                whatsapp_preview: r.whatsapp_preview ?? "",
              });
              setEditText(r.ai_advisory);
            } else {
              setAiError(true);
            }
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
          <button className="dash-back" onClick={handleBack} type="button">
            <i className="fa-solid fa-arrow-left" /> Volver
          </button>
          <Image src={brandLogo} alt="PoliMilpa" width={36} height={36} style={{ width: "auto", height: "1.8rem" }} />
          <span className="dash-brand-name">PoliMilpa</span>
        </div>
        <div className="dash-nav">
          {user && <span className="dash-user"><i className="fa-regular fa-user" /> {user.full_name}</span>}
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

            {rec?.nino_alert && <NinoBanner alert={rec.nino_alert} />}

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

                    {rec?.fos_windows && <FosWindows fos={rec.fos_windows} />}

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
