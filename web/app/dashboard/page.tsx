"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAuth } from "../../lib/auth-context";
import { getFarmers, type Farmer } from "../../lib/api";

const brandLogo = "/assets/logo-polimilpa.png";

const ZONE_LABELS: Record<string, string> = {
	highland_humid: "Z1 — Húmedo de Altura",
	dry_corridor: "Z2 — Corredor Seco",
	subhumid_caribbean: "Z3 — Caribe Subhúmedo",
	transition: "Z4 — Zona de Transición",
};

const ZONE_COLORS: Record<string, string> = {
	highland_humid: "#56b34f",
	dry_corridor: "#eb5757",
	subhumid_caribbean: "#f2c94c",
	transition: "#f2994a",
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
			.then(setFarmers)
			.finally(() => setFetching(false));
	}, [token, loading, router]);

	if (loading || fetching) {
		return (
			<main className="dash-shell">
				<div className="dash-loading">Cargando...</div>
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
						<i className="fa-solid fa-user" />
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
					<div className="farmer-grid">
						{farmers.map((farmer) => (
							<article
								key={farmer.id}
								className="farmer-card"
								onClick={() => router.push(`/dashboard/farmer/${farmer.id}`)}
								role="button"
								tabIndex={0}
								onKeyDown={(e) => {
									if (e.key === "Enter" || e.key === " ") {
										router.push(`/dashboard/farmer/${farmer.id}`);
									}
								}}
							>
								<div className="farmer-card-head">
									<div
										className="farmer-avatar"
										style={{ backgroundColor: ZONE_COLORS[farmer.agro_zone] ?? "#999" }}
									>
										{farmer.full_name.charAt(0)}
									</div>
									<div className="farmer-card-info">
										<h2>{farmer.farm_name}</h2>
										<p>{farmer.full_name}</p>
									</div>
									<span
										className="zone-badge"
										style={{ backgroundColor: ZONE_COLORS[farmer.agro_zone] ?? "#999" }}
									>
										{ZONE_LABELS[farmer.agro_zone] ?? farmer.agro_zone}
									</span>
								</div>

								<div className="farmer-card-body">
									<div className="farmer-detail">
										<i className="fa-solid fa-location-dot" />
										<span>{farmer.municipality}, {farmer.department}</span>
									</div>
									{farmer.contact_phone && (
										<div className="farmer-detail">
											<i className="fa-solid fa-phone" />
											<span>{farmer.contact_phone}</span>
										</div>
									)}
								</div>

								<div className="farmer-card-foot">
									<span className="farmer-cta">
										Ver recomendación
										<i className="fa-solid fa-arrow-right" />
									</span>
								</div>
							</article>
						))}
					</div>
				)}
			</section>
		</main>
	);
}
