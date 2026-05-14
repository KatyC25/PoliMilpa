"use client";

import Image from "next/image";
import { useState } from "react";

const brandLogo = "/assets/logo-polimilpa.png";
const nicaraguaMap = "/assets/nicaragua.svg";

const zoneGroups = [
	{
		id: "norte",
		title: "Zona Norte (Húmeda)",
		description: "Alta humedad y lluvias abundantes.",
		icon: "fa-cloud-rain",
		color: "green",
	},
	{
		id: "centro",
		title: "Zona Centro (Subhúmeda)",
		description: "Humedad moderada y lluvias estacionales.",
		icon: "fa-cloud-sun",
		color: "amber",
	},
	{
		id: "occidente",
		title: "Zona Occidente (Seca)",
		description: "Menor humedad y lluvias escasas.",
		icon: "fa-sun",
		color: "orange",
	},
	{
		id: "sur",
		title: "Zona Sur (Muy seca)",
		description: "Condiciones secas y altas temperaturas.",
		icon: "fa-solid fa-temperature-high",
		color: "red",
	},
];

// Recomendaciones adaptadas a los nuevos IDs de las zonas
const zoneRecommendations: Record<string, any> = {
	norte: {
		title: "Zona Norte (Húmeda)",
		subtitle: "Condiciones actuales para siembra",
		main_crop: {
			name: "Frijol de sombra",
			status: "Recomendado",
			description:
				"Buen nivel de humedad y condiciones favorables de suelo para el desarrollo del cultivo.",
			benefits: ["Buen rendimiento esperado", "Baja incidencia de plagas"],
			image: "/assets/frijol.png",
		},
		alt_crop: {
			name: "Maíz",
			status: "Alternativa",
			description:
				"Opción complementaria según disponibilidad de suelo y preparación.",
			benefits: [],
			image: "/assets/maiz.png",
		},
		actions: [
			{
				icon: "fa-tree",
				title: "Sembrar en zonas con sombra",
				description: "Aprovecha la humedad y protege el cultivo.",
			},
			{
				icon: "fa-leaf",
				title: "Evitar suelos expuestos",
				description: "Reduce la erosión y mejora la retención de humedad.",
			},
			{
				icon: "fa-droplet",
				title: "Preparar drenaje ligero",
				description: "Asegura un buen flujo de agua y evita encharcamientos.",
			},
		],
		weather: {
			title: "Lluvias en los próximos 5 días",
			forecast: "Condiciones favorables para la siembra.",
			days: [
				{ day: "Hoy", icon: "fa-cloud-rain", temp: "24°/18°" },
				{ day: "Mar", icon: "fa-cloud-rain", temp: "25°/18°" },
				{ day: "Mié", icon: "fa-cloud-rain", temp: "24°/18°" },
				{ day: "Jue", icon: "fa-cloud", temp: "25°/18°" },
				{ day: "Vie", icon: "fa-sun", temp: "26°/19°" },
			],
			note: "Año Niño moderado. Se esperan lluvias por encima del promedio.",
		},
	},
	centro: {
		title: "Zona Centro (Subhúmeda)",
		subtitle: "Condiciones actuales para siembra",
		main_crop: {
			name: "Cacao",
			status: "Recomendado",
			description:
				"Humedad constante y temperaturas ideales para este cultivo tropical.",
			benefits: ["Excelente adaptación", "Suelo óptimo para crecimiento"],
			image: "/assets/cacao.png",
		},
		alt_crop: {
			name: "Yuca",
			status: "Alternativa",
			description:
				"Opción resistente y complementaria para diversificar producción.",
			benefits: [],
			image: "/assets/yuca.png",
		},
		actions: [
			{
				icon: "fa-leaf",
				title: "Mantener humedad constante",
				description: "Monitorea regularmente el nivel de humedad del suelo.",
			},
			{
				icon: "fa-droplet",
				title: "Mejorar drenaje",
				description: "Evita el exceso de agua en épocas lluviosas.",
			},
			{
				icon: "fa-tree",
				title: "Establecer sombra parcial",
				description: "Propicia condiciones favorables para el desarrollo.",
			},
		],
		weather: {
			title: "Lluvia frecuente esperada",
			forecast: "Condiciones muy favorables para siembra.",
			days: [
				{ day: "Hoy", icon: "fa-cloud-rain", temp: "26°/21°" },
				{ day: "Mar", icon: "fa-cloud-rain", temp: "26°/21°" },
				{ day: "Mié", icon: "fa-cloud-rain", temp: "25°/20°" },
				{ day: "Jue", icon: "fa-cloud-rain", temp: "26°/21°" },
				{ day: "Vie", icon: "fa-cloud-sun", temp: "27°/22°" },
			],
			note: "Precipitaciones regulares durante esta temporada.",
		},
	},
	occidente: {
		title: "Zona Occidente (Seca)",
		subtitle: "Condiciones actuales para siembra",
		main_crop: {
			name: "Café",
			status: "Recomendado",
			description: "Condiciones mixtas con humedad moderada a baja.",
			benefits: ["Equilibrio humedad-temperatura", "Buen suelo fértil"],
			image: "/assets/cafe.png",
		},
		alt_crop: {
			name: "Frijol",
			status: "Alternativa",
			description: "Opción versátil que se adapta a condiciones variables.",
			benefits: [],
			image: "/assets/frijol.png",
		},
		actions: [
			{
				icon: "fa-leaf",
				title: "Monitorear humedad",
				description: "Mantén equilibrio entre riego y drenaje.",
			},
			{
				icon: "fa-tree",
				title: "Usar agroforestería",
				description: "Integra árboles de sombra con cultivos.",
			},
			{
				icon: "fa-droplet",
				title: "Preparar para variabilidad",
				description: "Ten sistemas de riego y drenaje flexibles.",
			},
		],
		weather: {
			title: "Condiciones variables",
			forecast: "Equilibrio entre lluvia escasa y sequía.",
			days: [
				{ day: "Hoy", icon: "fa-cloud-sun", temp: "26°/19°" },
				{ day: "Mar", icon: "fa-cloud-rain", temp: "25°/18°" },
				{ day: "Mié", icon: "fa-cloud-sun", temp: "26°/19°" },
				{ day: "Jue", icon: "fa-sun", temp: "27°/20°" },
				{ day: "Vie", icon: "fa-cloud-sun", temp: "27°/19°" },
			],
			note: "Condiciones transicionales con menos precipitaciones.",
		},
	},
	sur: {
		title: "Zona Sur (Muy seca)",
		subtitle: "Condiciones actuales para siembra",
		main_crop: {
			name: "Sorgo",
			status: "Recomendado",
			description:
				"Cultivo resiliente ideal para climas secos con buena adaptación.",
			benefits: ["Alta resistencia a sequía", "Bajo requerimiento de agua"],
			image: "/assets/sorgo.png",
		},
		alt_crop: {
			name: "Frijol caupí",
			status: "Alternativa",
			description: "Leguminosa resistente a condiciones de estrés hídrico.",
			benefits: [],
			image: "/assets/frijol-caupi.png",
		},
		actions: [
			{
				icon: "fa-droplet",
				title: "Riego complementario",
				description: "Aplica riego en momentos críticos del cultivo.",
			},
			{
				icon: "fa-leaf",
				title: "Conservar humedad del suelo",
				description: "Usa mulch para retener agua y reducir evaporación.",
			},
			{
				icon: "fa-sun",
				title: "Aprovechar sistemas de cosecha",
				description: "Recoge agua de lluvia para futuros riegos.",
			},
		],
		weather: {
			title: "Sequía esperada en próximos días",
			forecast: "Planifica riego complementario.",
			days: [
				{ day: "Hoy", icon: "fa-sun", temp: "28°/19°" },
				{ day: "Mar", icon: "fa-sun", temp: "29°/20°" },
				{ day: "Mié", icon: "fa-sun", temp: "29°/20°" },
				{ day: "Jue", icon: "fa-cloud-sun", temp: "28°/19°" },
				{ day: "Vie", icon: "fa-sun", temp: "30°/21°" },
			],
			note: "Zona seca con baja precipitación y altas temperaturas.",
		},
	},
};

// Conservamos la leyenda del primer código
const legendItems = [
	{ label: "Zona Norte (Húmeda)", color: "#56b34f" },
	{ label: "Zona Centro (Subhúmeda)", color: "#f2c94c" },
	{ label: "Zona Occidente (Seca)", color: "#f2994a" },
	{ label: "Zona Sur (Muy seca)", color: "#eb5757" },
];

export default function Home() {
	const [selectedZone, setSelectedZone] = useState<string | null>(null);
	const rec = selectedZone ? zoneRecommendations[selectedZone] : null;

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
							<article
								className={`zone-card ${selectedZone === group.id ? "active" : ""}`}
								key={group.id}
								onClick={() => setSelectedZone(group.id)}
								role="button"
								tabIndex={0}
								onKeyDown={(e) => {
									if (e.key === "Enter" || e.key === " ") {
										setSelectedZone(group.id);
									}
								}}
							>
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

			{/* Panel de recomendaciones interactivo del segundo código */}
			{selectedZone && rec && (
				<section className="recommendation-panel">
					<div className="rec-header">
						<div>
							<h1>{rec.title}</h1>
							<div className="rec-badge">
								<i className="fa-solid fa-circle-check" />
								Zona seleccionada
							</div>
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

								{/* Cultivo principal */}
								<div className="crop-card recommended">
									<div className="crop-image">
										<div className="crop-placeholder">
											<i className="fa-solid fa-leaf" />
										</div>
									</div>
									<div className="crop-info">
										<h3>{rec.main_crop.name}</h3>
										<span className={`crop-badge recommended`}>
											{rec.main_crop.status}
										</span>
										<p>{rec.main_crop.description}</p>
										{rec.main_crop.benefits.length > 0 && (
											<div className="crop-benefits">
												{rec.main_crop.benefits.map(
													(benefit: string, idx: number) => (
														<span key={idx}>
															<i className="fa-solid fa-check" /> {benefit}
														</span>
													),
												)}
											</div>
										)}
									</div>
								</div>

								{/* Cultivo alternativo */}
								<div className="crop-card alternative">
									<div className="crop-image">
										<div className="crop-placeholder">
											<i className="fa-solid fa-leaf" />
										</div>
									</div>
									<div className="crop-info">
										<h3>{rec.alt_crop.name}</h3>
										<span className="crop-badge alternative">
											{rec.alt_crop.status}
										</span>
										<p>{rec.alt_crop.description}</p>
									</div>
								</div>

								<div className="rec-note">
									<i className="fa-solid fa-circle-info" />
									<span>
										Recomendaciones generadas con datos satelitales (Copernicus)
										y climáticos actualizados.
									</span>
								</div>
							</div>

							<div className="rec-section">
								<h2>¿Qué puedes hacer esta semana?</h2>
								<div className="actions-grid">
									{rec.actions.map((action: any, idx: number) => (
										<div key={idx} className="action-card">
											<div className="action-icon">
												<i className={`fa-solid ${action.icon}`} />
											</div>
											<h3>{action.title}</h3>
											<p>{action.description}</p>
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
								<h3 className="weather-title">{rec.weather.title}</h3>
								<p className="weather-forecast">{rec.weather.forecast}</p>

								<div className="forecast-days">
									{rec.weather.days.map((d: any, idx: number) => (
										<div key={idx} className="forecast-day">
											<span className="day-name">{d.day}</span>
											<i className={`fa-solid ${d.icon}`} />
											<span className="day-temp">{d.temp}</span>
										</div>
									))}
								</div>

								<div className="weather-note">
									<i className="fa-solid fa-wave" />
									<span>{rec.weather.note}</span>
								</div>
							</div>

							<div className="rec-section tech-section">
								<div className="tech-icon">
									<i className="fa-solid fa-user-tie" />
								</div>
								<h2>¿Quieres recomendaciones más precisas para tu finca?</h2>
								<p>
									Un técnico puede analizar tu parcela y darte recomendaciones
									personalizadas.
								</p>
								<button type="button" className="tech-cta">
									<i className="fa-solid fa-lock" />
									Sin compromiso. Tú decides.
								</button>
							</div>
						</div>
					</div>
				</section>
			)}
		</main>
	);
}
