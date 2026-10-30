"""KPIs técnicos de la plataforma (K1-K4): la regla de las 3 As en vivo."""
from __future__ import annotations

import altair as alt
import streamlit as st

from lib import color_scale, read_gold, periodo_datos

st.set_page_config(page_title="Cercanías — Calidad del dato", page_icon="🛠️", layout="wide")
st.title("🛠️ Calidad del dato e ingesta")

ingesta = read_gold("kpi_ingesta")
cobertura = read_gold("kpi_cobertura")

if ingesta.empty:
    st.info("Sin métricas de ingesta todavía: ejecuta `dbt build`.")
    st.stop()

st.info(periodo_datos(ingesta) + " Indicadores históricos; no representan el estado en vivo.")

ingesta["fecha"] = ingesta["fecha"].astype(str)

# ── K1: snapshots por día y feed ─────────────────────────────────────────
st.subheader("K1 · Snapshots capturados por día y feed")
dominio, colores = color_scale(ingesta["feed"].unique().tolist())
chart = (
    alt.Chart(ingesta)
    .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=60))
    .encode(
        x=alt.X("fecha:N", title="Fecha"),
        y=alt.Y("n_snapshots:Q", title="Snapshots/día"),
        color=alt.Color("feed:N", scale=alt.Scale(domain=dominio, range=colores), title="Feed"),
        tooltip=["fecha:N", "feed:N", "n_snapshots:Q",
                 alt.Tooltip("cadencia_media_s:Q", title="Cadencia media (s)"),
                 alt.Tooltip("n_huecos_2min:Q", title="Huecos > 2 min")],
    )
    .properties(height=320)
)
st.altair_chart(chart, use_container_width=True)

c1, c2, c3 = st.columns(3)
ult = ingesta.sort_values("fecha").groupby("feed").last().reset_index()
c1.metric("Cadencia media (últ. día)", f"{ult['cadencia_media_s'].mean():.0f} s", help="Objetivo K2: ≤ 35 s")
c2.metric("Huecos > 2 min (últ. día)", int(ult["n_huecos_2min"].sum()), help="Objetivo K2: < 5/día")
c3.metric("Disponibilidad media", f"{ult['disponibilidad_pct'].mean():.0f}%", help="Objetivo K1: ≥ 99%")

# ── K3: cobertura reconciliada ──────────────────────────────────────────
if not cobertura.empty:
    st.subheader("K3 · Cobertura reconciliada RT ↔ GTFS estático")
    st.caption(periodo_datos(cobertura) + " Umbral H12': ≥ 95% de los viajes observados con línea identificada.")
    cobertura["fecha"] = cobertura["fecha"].astype(str)
    base = alt.Chart(cobertura).encode(x=alt.X("fecha:N", title="Fecha"))
    linea_cob = base.mark_line(strokeWidth=2, color="#2a78d6", point=alt.OverlayMarkDef(size=60)).encode(
        y=alt.Y("cobertura_pct:Q", title="Cobertura (%)", scale=alt.Scale(domain=[0, 100])),
        tooltip=["fecha:N",
                 alt.Tooltip("cobertura_pct:Q", format=".1f", title="Cobertura (%)"),
                 alt.Tooltip("viajes_observados:Q", title="Viajes observados")],
    )
    umbral = alt.Chart(cobertura).mark_rule(strokeDash=[6, 4], color="#52514e").encode(y=alt.datum(95))
    st.altair_chart((linea_cob + umbral).properties(height=300), use_container_width=True)

with st.expander("Ver tablas de datos"):
    st.dataframe(ingesta, use_container_width=True, hide_index=True)
    if not cobertura.empty:
        st.dataframe(cobertura, use_container_width=True, hide_index=True)
