"""Cuadro de mando — Tiempo real (ruta caliente, latencia objetivo < 60 s)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import DATA_ROOT, fmt_min

st.set_page_config(page_title="Cercanías — Tiempo real", page_icon="🚆", layout="wide")

st.title("🚆 Estado de la red en tiempo real")
st.caption("Plataforma de Monitorización de la Red de Cercanías — TFM Ingeniería de Datos")

realtime = DATA_ROOT / "gold" / "realtime"
estado_path = realtime / "estado_red.parquet"
pos_path = realtime / "posiciones.parquet"

if st.button("🔄 Actualizar"):
    st.rerun()

if not estado_path.exists():
    st.info(
        "Aún no hay estado en tiempo real. Comprueba que `ingestor`, `kafka` y "
        "`stream` están arrancados (`docker compose ps`)."
    )
    st.stop()

df = pd.read_parquet(estado_path)

# ── Tiles de cabecera ────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Viajes activos", len(df))
c2.metric("Retraso medio", fmt_min(df["arrival_delay_min"].mean()))
c3.metric("Retraso máximo", fmt_min(df["arrival_delay_min"].max()))
en_hora = (df["arrival_delay_min"] < 5).mean() * 100 if len(df) else 0
c4.metric("En hora (< 5 min)", f"{en_hora:.0f}%")

# ── Semáforo (estado = paleta de estado, con recuento textual) ──────────
st.subheader("Semáforo de la red")
counts = df["semaforo"].value_counts()
cols = st.columns(4)
labels = {"verde": "🟢 En hora", "ambar": "🟡 5–10 min", "rojo": "🔴 > 10 min", "gris": "⚪ Sin dato"}
for col, key in zip(cols, ["verde", "ambar", "rojo", "gris"]):
    col.metric(labels[key], int(counts.get(key, 0)))

col_mapa, col_tabla = st.columns([1, 1])

with col_mapa:
    st.subheader("Posición de los trenes")
    if pos_path.exists():
        pos = pd.read_parquet(pos_path)
        pos = pos.dropna(subset=["latitude", "longitude"])
        st.map(pos, latitude="latitude", longitude="longitude", size=30)
        st.caption(f"{len(pos)} trenes con posición · actualizado {pos['updated_at'].max()}")
    else:
        st.info("Sin posiciones todavía (feed vehicle_positions).")

with col_tabla:
    st.subheader("Mayores retrasos ahora")
    cols_show = [c for c in ["linea", "trip_id", "stop_name", "arrival_delay_min", "semaforo"] if c in df.columns]
    top = df.sort_values("arrival_delay_min", ascending=False).head(15)[cols_show]
    st.dataframe(
        top.rename(columns={"arrival_delay_min": "retraso (min)", "stop_name": "próxima parada"}),
        use_container_width=True, hide_index=True,
    )
