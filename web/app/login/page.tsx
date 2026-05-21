"use client";

import Image from "next/image";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";

const brandLogo = "/assets/logo-polimilpa.png";

export default function LoginPage() {
	const router = useRouter();
	const { login, user, loading } = useAuth();
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const [submitting, setSubmitting] = useState(false);

	if (loading) {
		return (
			<main className="login-shell" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
				<p>Cargando...</p>
			</main>
		);
	}

	if (user) {
		router.replace("/dashboard");
		return null;
	}

	const handleSubmit = async (e: FormEvent) => {
		e.preventDefault();
		setError("");
		setSubmitting(true);
		try {
			await login(username, password);
			router.push("/dashboard");
		} catch (err) {
			setError(err instanceof Error ? err.message : "Error al iniciar sesión");
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<main className="login-shell">
			<section className="login-layout" aria-label="Acceso PoliMilpa">
				<div className="login-hero">
					<a className="login-branding" href="https://poli-milpa.vercel.app">
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
					</a>

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

				<form className="login-panel" onSubmit={handleSubmit}>
					<div className="login-panel-head">
						<h2>Iniciar sesión</h2>
						<p>Acceso para técnicos y equipo PoliMilpa</p>
					</div>

					{error && (
						<div className="login-error">
							<i className="fa-solid fa-circle-exclamation" />
							<span>{error}</span>
						</div>
					)}

					<label className="login-field">
						<span>Usuario</span>

						<div className="login-input-wrap">
							<i className="fa-regular fa-user" aria-hidden="true" />

							<input
								type="text"
								name="username"
								placeholder="usuario"
								value={username}
								onChange={(e) => setUsername(e.target.value)}
								required
								autoFocus
							/>
						</div>
					</label>

					<label className="login-field">
						<span>Contraseña</span>

						<div className="login-input-wrap login-password-wrap">
							<i className="fa-solid fa-lock" aria-hidden="true" />

							<input
								type="password"
								name="password"
								placeholder="••••••••••"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								required
							/>

							<button
								type="button"
								className="login-eye"
								aria-label="Mostrar contraseña"
								onClick={(e) => {
									const input = (e.currentTarget.parentElement!.querySelector("input")!);
									input.type = input.type === "password" ? "text" : "password";
								}}
							>
								<i className="fa-regular fa-eye" aria-hidden="true" />
							</button>
						</div>
					</label>

					<button type="submit" className="login-submit" disabled={submitting}>
						<span>
							{submitting ? (
								<><i className="fa-solid fa-circle-notch fa-spin" /> Conectando con el servidor...</>
							) : "Iniciar sesión"}</span>

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
