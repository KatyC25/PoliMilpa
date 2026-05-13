import { fetchDemoCases } from "../lib/api";

const landingUrl = "file:///Users/katy/Proyectos/agroni/landing/index.html";

const zoneGroups = [
	{
		title: "Norte",
		climate: "Húmedo de altura",
		zones: ["Jinotega", "Matagalpa", "Nueva Segovia", "Madriz"],
		color: "green",
	},
	{
		title: "Centro",
		climate: "Transición",
		zones: ["Boaco", "Carazo", "Chontales", "Estelí"],
		color: "amber",
	},
	{
		title: "Occidente",
		climate: "Corredor seco",
		zones: ["Chinandega", "León", "Granada", "Managua"],
		color: "red",
	},
	{
		title: "Sur",
		climate: "Subhúmedo",
		zones: ["Rivas", "Río San Juan", "Masaya", "Atlántico Sur"],
		color: "lime",
	},
];

const legendItems = [
	{ label: "Húmedo de altura", color: "#16a34a" },
	{ label: "Subhúmedo", color: "#facc15" },
	{ label: "Transición", color: "#fb923c" },
	{ label: "Corredor seco", color: "#ef4444" },
];

export default async function Home() {
	const demoCases = await fetchDemoCases();

	return (
		<main className="page-shell">
			<header className="topbar">
				<a className="brand brand-link" href={landingUrl}>
					<div className="brand-mark" aria-hidden="true">
						<span />
						<span />
						<span />
					</div>
					<div>
						<div className="brand-name">PoliMilpa</div>
						<div className="brand-subtitle">
							Datos climáticos y satelitales para decidir mejor
						</div>
					</div>
				</a>

				<nav className="nav-links" aria-label="Principal">
					<a className="active" href="#inicio">
						Inicio
					</a>
					<a href="#productores">Productores</a>
					<a href={landingUrl}>Landing</a>
				</nav>

				<a className="login-link" href={landingUrl}>
					Volver a la landing
				</a>
			</header>

			<section className="hero" id="inicio">
				<div className="hero-copy">
					<p className="eyebrow">Selecciona tu zona</p>
					<h1>Elige la región donde te encuentras en el mapa o en la lista</h1>
					<p className="hero-text">
						Estas zonas se basan en datos climáticos y satelitales de
						Copernicus.
					</p>

					<div className="group-list" aria-label="Zonas agroclimáticas">
						{zoneGroups.map((group) => (
							<article
								className={`group-card ${group.color}`}
								key={group.title}
							>
								<div className="group-header">
									<h2>{group.title}</h2>
									<span>{group.climate}</span>
								</div>
								<ul>
									{group.zones.map((zone) => (
										<li key={zone}>{zone}</li>
									))}
								</ul>
							</article>
						))}
					</div>
				</div>

				<aside className="map-panel" aria-label="Mapa de zonas agroclimáticas">
					<div className="legend">
						{legendItems.map((item) => (
							<div className="legend-item" key={item.label}>
								<span style={{ backgroundColor: item.color }} />
								<small>{item.label}</small>
							</div>
						))}
					</div>

					<div className="map-card">
						<div className="map-placeholder">
							<div className="map-island north" />
							<div className="map-island center" />
							<div className="map-island west" />
							<div className="map-island south" />
							<p>Mapa interactivo de Nicaragua</p>
						</div>
					</div>

					<p className="mobile-hint">Presiona sobre el mapa tu zona</p>
				</aside>
			</section>

			<section className="demo-strip" id="productores">
				<div className="demo-strip-header">
					<p className="eyebrow">Demo público</p>
					<h2>Casos listos para revisar</h2>
				</div>

				<div className="demo-grid">
					{demoCases.length > 0 ? (
						demoCases.slice(0, 3).map((item) => (
							<article className="demo-card" key={item.case_code}>
								<strong>{item.title}</strong>
								<p>
									{item.department} · {item.municipality}
								</p>
								<small>{item.agro_zone}</small>
							</article>
						))
					) : (
						<article className="demo-card muted">
							<strong>No hay casos demo disponibles aún</strong>
							<p>La interfaz ya está conectada al backend FastAPI.</p>
						</article>
					)}
				</div>
			</section>
		</main>
	);
}
