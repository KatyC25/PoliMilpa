import Image from "next/image";

const brandLogo = "/assets/logo-polimilpa.png";

export default function LoginPage() {
	return (
		<main className="login-shell">
			<section className="login-layout" aria-label="Acceso PoliMilpa">
				<div className="login-hero">
					<div className="login-branding">
						<div className="login-brand-mark">
							<Image
								src={brandLogo}
								alt="PoliMilpa"
								width={100}
								height={100}
								style={{ width: "auto", height: "2.5rem" }}
								priority
							/>
						</div>

						<span className="login-brand-name">PoliMilpa</span>
					</div>

					<div className="login-hero-copy">
						<h1>
							Bienvenido
							<span>de vuelta</span>
						</h1>

						<p>
							Accede a los análisis satelitales y fichas de productores de tu
							región.
						</p>
					</div>

					<ul className="login-benefits" aria-label="Beneficios de acceso">
						<li>
							<span className="login-benefit-icon">
								<i className="fa-solid fa-satellite" aria-hidden="true" />
							</span>

							<span>Datos Copernicus en tiempo real</span>
						</li>

						<li>
							<span className="login-benefit-icon">
								<i
									className="fa-solid fa-map-location-dot"
									aria-hidden="true"
								/>
							</span>

							<span>Análisis NDVI por parcela</span>
						</li>

						<li>
							<span className="login-benefit-icon">
								<i
									className="fa-solid fa-location-crosshairs"
									aria-hidden="true"
								/>
							</span>

							<span>Geolocalización de fincas</span>
						</li>
					</ul>

					<div className="login-trust">
						<div className="login-trust-icon">
							<i className="fa-solid fa-shield-halved" aria-hidden="true" />
						</div>

						<div>
							<strong>Plataforma segura y confiable</strong>
							<span>Tus datos están protegidos</span>
						</div>
					</div>
				</div>

				<form className="login-panel">
					<div className="login-panel-head">
						<h2>Iniciar sesión</h2>
						<p>Acceso para técnicos y equipo PoliMilpa</p>
					</div>

					<label className="login-field">
						<span>Correo</span>

						<div className="login-input-wrap">
							<i className="fa-regular fa-envelope" aria-hidden="true" />

							<input
								type="email"
								name="email"
								placeholder="correo@ejemplo.com"
							/>
						</div>
					</label>

					<label className="login-field">
						<span>Contraseña</span>

						<div className="login-input-wrap login-password-wrap">
							<i className="fa-solid fa-lock" aria-hidden="true" />

							<input type="password" name="password" placeholder="••••••••••" />

							<button
								type="button"
								className="login-eye"
								aria-label="Mostrar contraseña"
							>
								<i className="fa-regular fa-eye" aria-hidden="true" />
							</button>
						</div>
					</label>

					<button type="button" className="login-submit">
						<span>Iniciar sesión</span>

						<i className="fa-solid fa-arrow-right" aria-hidden="true" />
					</button>

					<div className="login-footer-note">
						<i className="fa-solid fa-lock" aria-hidden="true" />

						<p>
							Acceso restringido a personal autorizado de PoliMilpa. Todos los
							accesos quedan registrados.
						</p>
					</div>
				</form>
			</section>
		</main>
	);
}
