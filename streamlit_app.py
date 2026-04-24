import os
import urllib.parse

import httpx
import pandas as pd
import streamlit as st


API_BASE_URL = os.getenv("POLIMILPA_API_URL", "http://127.0.0.1:8000")


def infer_semaforo(text: str) -> tuple[str, str]:
    normalized = text.lower()
    if "rojo" in normalized:
        return "ROJO", "#d73027"
    if "amarillo" in normalized:
        return "AMARILLO", "#fdae61"
    if "verde" in normalized:
        return "VERDE", "#1a9850"
    return "SIN CLASIFICAR", "#455a64"


@st.cache_data(ttl=30)
def fetch_demo_cases() -> list[dict]:
    url = f"{API_BASE_URL}/v1/demo/cases"
    with httpx.Client(timeout=15) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


st.set_page_config(page_title="PoliMilpa Demo", page_icon="🌱", layout="wide")

st.markdown(
    """
    <style>
    .status-card {
        border-radius: 12px;
        padding: 14px 16px;
        color: #fff;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .hint {
        font-size: 0.9rem;
        opacity: 0.88;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("PoliMilpa Demo Publico")
st.caption(
    "Recomendaciones de policultivo con soporte satelital para casos demostrativos"
)

left_col, right_col = st.columns([1, 2])

try:
    cases = fetch_demo_cases()
except Exception as exc:
    st.error("No fue posible cargar casos demo desde la API")
    st.info("Verifica que FastAPI este arriba y que POLIMILPA_API_URL sea correcto")
    st.exception(exc)
    st.stop()

if not cases:
    st.warning("No hay casos demo activos. Carga al menos uno en public_demo_cases.")
    st.stop()

options = {f"{item['title']} ({item['case_code']})": item for item in cases}
selected_label = left_col.selectbox("Selecciona una finca demo", list(options.keys()))
selected_case = options[selected_label]

left_col.subheader("Resumen")
left_col.write(f"Municipio: {selected_case['municipality']}")
left_col.write(f"Departamento: {selected_case['department']}")
left_col.write(f"Zona agro: {selected_case['agro_zone']}")
left_col.write(f"Lat/Lon: {selected_case['lat']}, {selected_case['lon']}")

if selected_case.get("map_reference"):
    left_col.caption(f"Referencia de mapa: {selected_case['map_reference']}")

right_col.subheader("Mapa de ubicacion")
map_df = pd.DataFrame(
    [
        {
            "lat": selected_case["lat"],
            "lon": selected_case["lon"],
        }
    ]
)
right_col.map(map_df, size=14, zoom=15)

right_col.subheader("Recomendacion")
status_label, status_color = infer_semaforo(selected_case["recommendation_text"])
right_col.markdown(
    f"<div class='status-card' style='background:{status_color}'>Semaforo: {status_label}</div>",
    unsafe_allow_html=True,
)
right_col.info(selected_case["recommendation_text"])

message_text = (
    selected_case.get("whatsapp_text") or selected_case["recommendation_text"]
)
encoded = urllib.parse.quote(message_text)
wa_link = f"https://wa.me/?text={encoded}"

right_col.markdown(f"### [Enviar recomendacion por WhatsApp]({wa_link})")
right_col.caption("Usa este boton para mostrar el cierre de valor en la demo.")

with st.expander("JSON del caso"):
    st.json(selected_case)
