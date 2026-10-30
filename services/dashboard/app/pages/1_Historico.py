"""Histórico de puntualidad (capa Gold, ruta fría)."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from lib import SEQ_BLUE, color_scale, read_gold, periodo_datos

st.set_page_config(page_title="Cercanías — Histórico", page_icon="📈", layout="wide")
st.title("📈 Histórico de puntualidad")

franja = read_gold("kpi_retraso_franja")
punt = read_gold("kpi_puntualidad_linea")

if franja.empty:
    st.info("Aún no hay Gold histórico: ejecuta el DAG diario o `dbt build`.")
    st.stop()

st.info(periodo_datos(franja) + " Indicadores históricos; no representan el estado en vivo.")

franja["fecha"] = franja["fecha"].astype(str)
lineas = sorted(x for x in franja["linea"].unique() if x and x != "SIN_LINEA")

# ── Filtros (una fila, encima de las gráficas) ──────────────────────────
c1, c2 = st.columns([2, 2])
fechas = sorted(franja["fecha"].unique())
rango = c1.select_slider("Rango de fechas", options=fechas, value=(fechas[0], fechas[-1]))
sel_lineas = c2.multiselect("Líneas", lineas, default=lineas[:4] or lineas)

mask = (franja["fecha"] >= rango[0]) & (franja["fecha"] <= rango[1])
f = franja[mask]

# ── Retraso medio por franja horaria (réplica continua de la Fig. 4) ────
st.subheader("Retraso medio por franja horaria")
agg = (
    f.groupby("franja", as_index=False)
    .apply(lambda g: pd.Series({"retraso_medio_min": (g["retraso_medio_min"] * g["n_observaciones"]).sum() / g["n_observaciones"].sum()}), include_groups=False)
)
chart = (
    alt.Chart(agg)
    .mark_bar(color=SEQ_BLUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("franja:N", sort=None, title="Franja horaria (hora local Madrid)"),
        y=alt.Y("retraso_medio_min:Q", title="Retraso medio (min)"),
        tooltip=[alt.Tooltip("franja:N", title="Franja"),
                 alt.Tooltip("retraso_medio_min:Q", format=".2f", title="Retraso medio (min)")],
    )
    .properties(height=320)
)
st.altair_chart(chart, use_container_width=True)

# ── Evolución diaria por línea ───────────────────────────────────────────
st.subheader("Evolución diaria del retraso medio por línea")
fl = f[f["linea"].isin(sel_lineas)]
if fl.empty:
    st.info("Selecciona al menos una línea con datos en el rango.")
else:
    evo = (
        fl.groupby(["fecha", "linea"], as_index=False)
        .apply(lambda g: pd.Series({"retraso_medio_min": (g["retraso_medio_min"] * g["n_observaciones"]).sum() / g["n_observaciones"].sum()}), include_groups=False)
    )
    dominio, colores = color_scale(sel_lineas)
    line = (
        alt.Chart(evo[evo["linea"].isin(dominio)])
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=60))
        .encode(
            x=alt.X("fecha:N", title="Fecha"),
            y=alt.Y("retraso_medio_min:Q", title="Retraso medio (min)"),
            color=alt.Color("linea:N", scale=alt.Scale(domain=dominio, range=colores), title="Línea"),
            tooltip=["fecha:N", "linea:N",
                     alt.Tooltip("retraso_medio_min:Q", format=".2f", title="Retraso (min)")],
        )
        .properties(height=340)
    )
    st.altair_chart(line, use_container_width=True)

# ── Puntualidad consumada por línea ─────────────────────────────────────
if not punt.empty:
    st.subheader("Puntualidad consumada por línea (% viajes ≤ 5 min al final)")
    punt["fecha"] = punt["fecha"].astype(str)
    p = punt[(punt["fecha"] >= rango[0]) & (punt["fecha"] <= rango[1])]
    p = p[p["linea"].isin(sel_lineas)] if sel_lineas else p
    st.caption(periodo_datos(p))
    agg_p = (
        p.groupby("linea", as_index=False)
        .apply(lambda g: pd.Series({
            "puntualidad_pct": (g["puntualidad_pct"] * g["viajes"]).sum() / g["viajes"].sum(),
            "viajes": g["viajes"].sum(),
        }), include_groups=False)
    )
    bar = (
        alt.Chart(agg_p)
        .mark_bar(color=SEQ_BLUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("linea:N", title="Línea", sort=None),
            y=alt.Y("puntualidad_pct:Q", title="Puntualidad (%)", scale=alt.Scale(domain=[0, 100])),
            tooltip=["linea:N",
                     alt.Tooltip("puntualidad_pct:Q", format=".1f", title="Puntualidad (%)"),
                     alt.Tooltip("viajes:Q", title="Viajes")],
        )
        .properties(height=300)
    )
    st.altair_chart(bar, use_container_width=True)
    with st.expander("Ver tabla de datos"):
        st.dataframe(p, use_container_width=True, hide_index=True)
