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

const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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
