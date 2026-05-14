import Image from "next/image";

const brandLogo = "/assets/logo-polimilpa.png";
const nicaraguaMap = "/assets/nicaragua.svg";

const zoneGroups = [
	{
		title: "Zona Norte (Húmeda)",
		description: "Alta humedad y lluvias abundantes.",
		icon: "fa-cloud-rain",
		color: "green",
	},
	{
		title: "Zona Centro (Subhúmeda)",
		description: "Humedad moderada y lluvias estacionales.",
		icon: "fa-cloud-sun",
		color: "amber",
	},
	{
		title: "Zona Occidente (Seca)",
		description: "Menor humedad y lluvias escasas.",
		icon: "fa-sun",
		color: "orange",
	},
	{
		title: "Zona Sur (Muy seca)",
		description: "Condiciones secas y altas temperaturas.",
		icon: "fa-solid fa-temperature-high",
		color: "red",
	},
];

const legendItems = [
	{ label: "Zona Norte (Húmeda)", color: "#56b34f" },
	{ label: "Zona Centro (Subhúmeda)", color: "#f2c94c" },
	{ label: "Zona Occidente (Seca)", color: "#f2994a" },
	{ label: "Zona Sur (Muy seca)", color: "#eb5757" },
];

export default function Home() {
	return (
		<main className="app-shell" id="inicio">
			<header className="topbar">
				<a className="brand" href="#inicio" aria-label="PoliMilpa">
					<Image
						className="brand-logo"
						src={brandLogo}
						alt="PoliMilpa"
						width={44}
						height={44}
						priority
					/>
					<span className="brand-name">PoliMilpa</span>
				</a>

				<nav className="topnav" aria-label="Principal">
					<a href="#inicio">Inicio</a>
					<a href="#zonas">Productores</a>
				</nav>

				<a className="primary-button" href="#zonas">
					Iniciar sesión
				</a>
			</header>

			<section className="platform-grid" id="zonas">
				<div className="zone-panel">
					<p className="section-kicker">Selecciona tu zona</p>
					<h2>Elige la región donde te encuentras</h2>
					<p className="section-copy">
						Elige la región en el mapa o en la lista.
					</p>

					<section className="zone-list" aria-label="Zonas agroclimáticas">
						{zoneGroups.map((group) => (
							<article className="zone-card" key={group.title}>
								<div className={`zone-icon ${group.color}`} aria-hidden="true">
									<i className={`fa-solid ${group.icon}`} />
								</div>
								<div className="zone-copy">
									<h2>{group.title}</h2>
									<p>{group.description}</p>
								</div>
								<i
									className="fa-solid fa-chevron-right zone-chevron"
									aria-hidden="true"
								/>
							</article>
						))}
					</section>
				</div>

				<section
					className="map-panel"
					aria-label="Mapa de zonas agroclimáticas"
				>
					<div className="map-frame">
						<div className="map-bg" aria-hidden="true" />
						<object
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
									<span
										style={{ backgroundColor: item.color }}
										aria-hidden="true"
									/>
									<small>{item.label}</small>
								</div>
							))}
						</div>
					</div>
				</section>
			</section>
		</main>
	);
}
