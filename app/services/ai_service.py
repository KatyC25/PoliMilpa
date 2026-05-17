import json
import os
from typing import Optional

from google import genai

from app.schemas import AIAdvisoryInput, AIAdvisoryResponse

_SYSTEM_PROMPT = """
Eres un asistente agroclimático experto en agricultura de Nicaragua.
Recibes datos de una parcela (GEE + C3S + reglas de negocio) y debes
generar un advisory natural y útil para el productor.

Devuelve SOLO un JSON con dos campos:
  - "advisory": texto narrativo de 3-5 oraciones explicando la situacion
    de la parcela, los cultivos recomendados, y la accion sugerida.
  - "whatsapp_preview": version corta (<280 caracteres) lista para
    enviar por WhatsApp, con emojis relevantes.

Sé concreto, usa lenguaje sencillo y datos del análisis.
"""


class AIService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.5-flash"

    def generate_advisory(self, data: AIAdvisoryInput) -> Optional[AIAdvisoryResponse]:
        if not self.enabled:
            return None

        prompt = f"""
Datos de la parcela:
- Parcela: {data.parcel_id}
- Semáforo: {data.traffic_light}
- Score global: {data.global_score:.3f}
- Cultivo de renta: {data.rent_crop}
- Cultivo alimentario: {data.food_crop}
- Ventana: {data.window}
- MSAVI2 (vigor vegetal): {data.msavi2}
- Pendiente: {data.slope_percent}%
- Humedad del suelo: {data.soil_moisture}
- Pronóstico estacional: {data.seasonal_forecast}
- Zona agroclimática: {data.zone}
- Departamento: {data.department}
- Municipio: {data.municipality}
"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                ),
            )
            text = response.text.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(text)
            return AIAdvisoryResponse(
                advisory=parsed.get("advisory", text),
                whatsapp_preview=parsed.get("whatsapp_preview", ""),
            )
        except Exception:
            return None


ai_service = AIService()
