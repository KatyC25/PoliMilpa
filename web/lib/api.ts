export type DemoCase = {
	id: number;
	case_code: string;
	title: string;
	municipality: string;
	department: string;
	agro_zone: string;
	recommendation_text: string;
	whatsapp_text: string;
	map_reference: string;
};

export type Farmer = {
	id: number;
	farmer_code: string;
	full_name: string;
	contact_phone: string;
	farm_name: string;
	municipality: string;
	department: string;
	agro_zone: string;
	lat: number | null;
	lon: number | null;
	geometry?: string | null;
	technician_username: string;
	is_active: boolean;
	area_m2?: number | null;
	area_manzanas?: number | null;
};

export type MapTile = {
	url: string;
	center: [number, number];
	zoom: number;
};

export type Recommendation = {
	parcel_id: string;
	traffic_light: "verde" | "amarillo" | "rojo";
	recommended_window: string;
	recommendations: Array<{
		rent_crop: string;
		food_crop: string;
		confidence: number;
		reason: string;
	}>;
	advisory_text: string;
	debug_scores?: Record<string, number | string>;
	data_source?: string;
	tile_url?: string | null;
	ai_advisory?: string | null;
	whatsapp_preview?: string | null;
};

export type AIAdvisoryInput = {
	parcel_id: string;
	traffic_light: string;
	global_score: number;
	rent_crop: string;
	food_crop: string;
	window: string;
	msavi2: number;
	slope_percent: number;
	soil_moisture: number;
	seasonal_forecast: string;
	zone: string;
	department: string;
	municipality: string;
};

export type AIAdvisoryResponse = {
	advisory: string;
	whatsapp_preview: string;
};

export type LoginResponse = {
	access_token: string;
	token_type: string;
};

const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(
	url: string,
	opts: RequestInit,
	retries = 2,
	delayMs = 1500,
): Promise<Response> {
	let lastError: Error | null = null;
	for (let attempt = 0; attempt <= retries; attempt++) {
		try {
			const res = await fetch(url, opts);
			return res;
		} catch (err) {
			lastError = err instanceof Error ? err : new Error(String(err));
			if (attempt < retries) {
				await sleep(delayMs);
			}
		}
	}
	throw lastError;
}

export async function login(
	username: string,
	password: string,
): Promise<LoginResponse> {
	const res = await fetchWithRetry(`${API_BASE_URL}/v1/auth/login`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ username, password }),
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: "Error de conexión" }));
		throw new Error(err.detail ?? "Credenciales inválidas");
	}
	return res.json() as Promise<LoginResponse>;
}

export async function fetchWithAuth(
	url: string,
	opts: RequestInit = {},
	tokenOverride?: string,
): Promise<Response> {
	const stored = tokenOverride ?? localStorage.getItem("polimilpa_token");
	const headers: Record<string, string> = {
		...(opts.headers as Record<string, string>),
	};
	if (stored) {
		headers["Authorization"] = `Bearer ${stored}`;
	}
	return fetch(`${API_BASE_URL}${url}`, { ...opts, headers });
}

export async function getFarmers(): Promise<Farmer[]> {
	const res = await fetchWithAuth("/v1/farmers");
	if (!res.ok) return [];
	return res.json() as Promise<Farmer[]>;
}

export async function getFarmer(id: number): Promise<Farmer | null> {
	const res = await fetchWithAuth(`/v1/farmers/${id}`);
	if (!res.ok) return null;
	return res.json() as Promise<Farmer>;
}

export async function getAutoRecommendation(
	parcelId: string,
	municipality: string,
	department: string,
	agroZone: string,
	lat: number,
	lon: number,
	geometry: string | null = null,
): Promise<Recommendation | null> {
	const res = await fetchWithAuth("/v1/recommendations/auto", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			parcel_id: parcelId,
			municipality,
			department,
			agro_zone: agroZone,
			lat,
			lon,
			geometry: geometry || undefined,
		}),
	});
	if (!res.ok) return null;
	return res.json() as Promise<Recommendation>;
}

export async function getAIAdvisory(
	data: AIAdvisoryInput,
): Promise<AIAdvisoryResponse | null> {
	const res = await fetchWithAuth("/v1/recommendations/ai-advisory", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(data),
	});
	if (!res.ok) return null;
	return res.json() as Promise<AIAdvisoryResponse>;
}

export async function fetchMapTiles(
	lat: number,
	lon: number,
	geometry?: string | null,
	agro_zone?: string | null,
): Promise<MapTile | null> {
	const res = await fetchWithAuth("/v1/recommendations/auto/map", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			parcel_id: "map",
			lat,
			lon,
			agro_zone: agro_zone || "transition",
			geometry: geometry || undefined,
		}),
	});
	if (!res.ok) return null;
	return res.json() as Promise<MapTile>;
}

export async function fetchDemoCases(): Promise<DemoCase[]> {
	try {
		const response = await fetch(`${API_BASE_URL}/v1/demo/cases`, {
			cache: "no-store",
		});

		if (!response.ok) {
			return [];
		}

		return (await response.json()) as DemoCase[];
	} catch {
		return [];
	}
}

export async function prefetchRecommendations(
	farmers: Array<{ lat: number; lon: number; agro_zone: string }>,
): Promise<void> {
	const valid = farmers.filter((f) => f.lat != null && f.lon != null);
	if (valid.length === 0) return;
	try {
		await fetchWithAuth("/v1/recommendations/prefetch", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ farmers: valid }),
		});
	} catch {
		// Prefetch es best-effort; ignorar errores
	}
}
