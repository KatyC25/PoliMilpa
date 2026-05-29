"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAuth } from "../../lib/auth-context";
import { getFarmers, prefetchRecommendations, type Farmer } from "../../lib/api";

const brandLogo = "/assets/logo-polimilpa.png";

const ZONE_LABELS: Record<string, string> = {
  highland_humid: "Z1 Húmedo Altura",
  dry_corridor: "Z2 Corredor Seco",
  subhumid_caribbean: "Z3 Caribe Subhúmedo",
  transition: "Z4 Transición",
};

const ZONE_COLORS: Record<string, string> = {
  highland_humid: "#56b34f",
  dry_corridor: "#eb5757",
  subhumid_caribbean: "#f2c94c",
  transition: "#f2994a",
};

const FARMER_PHOTOS: Record<string, string> = {
  "ESP-001": "/assets/farmerLechuga.jpg",
  "FLO-001": "/assets/farmerMaria.jpg",
};

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, loading, logout } = useAuth();
  const [farmers, setFarmers] = useState<Farmer[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    getFarmers()
      .then((list) => {
        setFarmers(list);
        prefetchRecommendations(
          list.map((f) => ({
            lat: f.lat!,
            lon: f.lon!,
            agro_zone: f.agro_zone,
          })),
        );
      })
      .finally(() => setFetching(false));
  }, [token, loading, router]);

  if (loading || fetching) {
    return (
      <main className="dash-shell">
        <div className="dash-loading">
          <i className="fa-solid fa-circle-notch fa-spin" />
          <span>Cargando productores...</span>
        </div>
      </main>
    );
  }

  return (
    <main className="dash-shell">
      <header className="dash-topbar">
        <div className="dash-brand">
          <Image
            src={brandLogo}
            alt="PoliMilpa"
            width={36}
            height={36}
            style={{ width: "auto", height: "1.8rem" }}
          />
          <span className="dash-brand-name">PoliMilpa</span>
        </div>

        <nav className="dash-nav">
          <span className="dash-user">
            <i className="fa-regular fa-user" />
            {user?.full_name ?? user?.username}
          </span>
          <button className="dash-logout" onClick={logout} type="button">
            <i className="fa-solid fa-right-from-bracket" />
            Salir
          </button>
        </nav>
      </header>

      <section className="dash-content">
        <div className="dash-header">
          <div>
            <h1>Productores</h1>
            <p className="dash-count">{farmers.length} finca(s) registrada(s)</p>
          </div>
        </div>

        {farmers.length === 0 ? (
          <div className="dash-empty">
            <i className="fa-solid fa-map" />
            <p>No hay fincas registradas para tu usuario.</p>
          </div>
        ) : (
          <div className="pl-grid">
            {farmers.map((farmer) => (
              <article
                key={farmer.id}
                className="pl-card"
                onClick={() => router.push(`/dashboard/farmer/${farmer.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    router.push(`/dashboard/farmer/${farmer.id}`);
                  }
                }}
              >
                <div className="pl-card-left">
                  <div className="pl-avatar">
                    {FARMER_PHOTOS[farmer.farmer_code] ? (
                      <Image
                        src={FARMER_PHOTOS[farmer.farmer_code]}
                        alt={farmer.full_name}
                        width={80}
                        height={80}
                        className="pl-avatar-img"
                      />
                    ) : (
                      <div
                        className="pl-avatar-letter"
                        style={{ backgroundColor: ZONE_COLORS[farmer.agro_zone] ?? "#999" }}
                      >
                        {farmer.full_name.charAt(0)}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pl-card-body">
                  <div className="pl-card-top">
                    <h2 className="pl-name">{farmer.full_name}</h2>
                    <span
                      className="pl-badge"
                      style={{ backgroundColor: ZONE_COLORS[farmer.agro_zone] ?? "#999" }}
                    >
                      {ZONE_LABELS[farmer.agro_zone] ?? farmer.agro_zone}
                    </span>
                  </div>

                  <div className="pl-meta">
                    <span>
                      <i className="fa-solid fa-location-dot" />
                      {farmer.municipality}, {farmer.department}
                    </span>
                    {farmer.area_manzanas != null && (
                      <span>
                        <i className="fa-solid fa-ruler-combined" />
                        {farmer.area_manzanas.toFixed(1)} mz
                      </span>
                    )}
                  </div>

                  <div className="pl-card-foot">
                    <span className="pl-cta">
                      Ver recomendación
                      <i className="fa-solid fa-arrow-right" />
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
