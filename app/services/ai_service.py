import datetime as dt
import json
import os
import time
from typing import Optional

from google import genai

from app.schemas import AIAdvisoryInput, AIAdvisoryResponse
from app.services.cache import TTLCache

_SYSTEM_PROMPT = """
Eres un asistente agroclimatico experto en agricultura de Nicaragua.
Recibes datos de una parcela (GEE + C3S + reglas de negocio) y debes
generar un advisory natural y util para el productor.

Devuelve SOLO un JSON con dos campos:
  - "advisory": texto narrativo de 3-5 oraciones explicando la situacion
    de la parcela, los cultivos recomendados, y la accion sugerida.
  - "whatsapp_preview": version corta (<280 caracteres) lista para
    enviar por WhatsApp, con emojis relevantes.

Se concreto, usa lenguaje sencillo y datos del analisis.
"""

_ai_cache = TTLCache(default_ttl=86400)


def _cache_key(parcel_id: str) -> str:
    return f"{parcel_id}:{dt.date.today().isoformat()}"


def _parse_response(text: str) -> Optional[dict]:
    try:
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _call_gemini(
    client: genai.Client, model: str, prompt: str
) -> Optional[AIAdvisoryResponse]:
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
            ),
        )
        text = response.text.strip()
        parsed = _parse_response(text)
        if parsed is None:
            print("[AI] Gemini response was not valid JSON")
            return None
        return AIAdvisoryResponse(
            advisory=parsed.get("advisory", text),
            whatsapp_preview=parsed.get("whatsapp_preview", ""),
        )
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str:
            retry_secs = _extract_retry_delay(err_str)
            if retry_secs is not None and retry_secs < 10:
                print(f"[AI] 429 — esperando {retry_secs}s y reintentando...")
                time.sleep(retry_secs)
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(
                            system_instruction=_SYSTEM_PROMPT,
                        ),
                    )
                    text = response.text.strip()
                    parsed = _parse_response(text)
                    if parsed is None:
                        return None
                    return AIAdvisoryResponse(
                        advisory=parsed.get("advisory", text),
                        whatsapp_preview=parsed.get("whatsapp_preview", ""),
                    )
                except Exception as retry_exc:
                    print(f"[AI] Retry tambien fallo: {retry_exc}")
                    return None
            else:
                print(f"[AI] 429 — quota diaria excedida ({retry_secs}s), omitiendo")
        elif "503" in err_str:
            print(f"[AI] 503 — Gemini no disponible temporalmente")
        else:
            print(f"[AI] Error generando advisory: {exc}")
        return None


def _extract_retry_delay(error_str: str) -> Optional[float]:
    try:
        if "retryDelay" in error_str:
            start = error_str.index("retryDelay") + len("retryDelay")
            segment = error_str[start:]
            digits = ""
            for ch in segment:
                if ch.isdigit() or ch == ".":
                    digits += ch
                elif digits:
                    break
            if digits:
                return float(digits) + 1.0
    except (ValueError, IndexError):
        pass

    try:
        if "retry in" in error_str:
            start = error_str.index("retry in") + len("retry in")
            segment = error_str[start:]
            digits = ""
            for ch in segment:
                if ch.isdigit() or ch == ".":
                    digits += ch
                elif digits:
                    break
            if digits:
                return float(digits) + 1.0
    except (ValueError, IndexError):
        pass

    return None


class AIService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.5-flash"

    def generate_advisory(self, data: AIAdvisoryInput) -> Optional[AIAdvisoryResponse]:
        if not self.enabled:
            print("[AI] Servicio deshabilitado: GEMINI_API_KEY no configurada")
            return None

        key = _cache_key(data.parcel_id)
        cached = _ai_cache.get(key)
        if cached is not None:
            print(f"[AI] Cache hit para parcela={data.parcel_id}")
            return cached

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
- Zona agroclimatica: {data.zone}
- Departamento: {data.department}
- Municipio: {data.municipality}
"""
        result = _call_gemini(self.client, self.model, prompt)
        if result is not None:
            _ai_cache.set(key, result)
        return result


ai_service = AIService()
