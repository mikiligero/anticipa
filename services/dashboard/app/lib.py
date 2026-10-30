"""Utilidades compartidas del cuadro de mando."""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
GOLD = DATA_ROOT / "gold"
API_URL = os.environ.get("API_URL", "http://api:8000")
API_TOKEN = os.environ["API_TOKEN"]

# Paleta categórica validada (orden fijo — la asignación sigue a la entidad)
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300",
               "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
SEQ_BLUE = "#2a78d6"


@st.cache_data(ttl=30)
def read_gold(name: str) -> pd.DataFrame:
    """Lee una tabla Gold (Parquet). Devuelve DataFrame vacío si no existe."""
    path = GOLD / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return duckdb.sql(f"select * from read_parquet('{path}')").df()


def color_scale(categorias: list[str]) -> tuple[list[str], list[str]]:
    """Escala categórica con orden fijo; a partir de la 8ª, gris 'Otras'."""
    cats = sorted(categorias)[:8]
    return cats, CATEGORICAL[: len(cats)]


def fmt_min(v: float | None) -> str:
    return "—" if v is None or pd.isna(v) else f"{v:.1f} min"


def periodo_datos(df: pd.DataFrame) -> str:
    """Periodo real del archivo, sin atribuirle una actualidad que no conocemos."""
    if "fecha" not in df:
        return "Periodo de los datos no disponible."
    fechas = pd.to_datetime(df["fecha"], errors="coerce", utc=True).dropna()
    if fechas.empty:
        return "Periodo de los datos no disponible."
    inicio, fin = fechas.min().strftime("%d/%m/%Y"), fechas.max().strftime("%d/%m/%Y")
    return f"Datos del {inicio}." if inicio == fin else f"Datos del {inicio} al {fin}."
