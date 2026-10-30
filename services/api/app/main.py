"""API de servicios de la Plataforma de Monitorización de Cercanías.

Endpoints de la demo: salud, estado en vivo, posiciones, indicadores,
viajero, mapa y tendencias. Las predicciones son ejemplos de la interfaz.

Autenticación por token (cabecera X-API-Key), RBAC simplificado del piloto.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
GOLD = DATA_ROOT / "gold"
REALTIME = GOLD / "realtime"
API_TOKEN = os.environ["API_TOKEN"]

KPI_TABLES = {
    "ingesta": "kpi_ingesta.parquet",
    "cobertura": "kpi_cobertura.parquet",
    "retraso_franja": "kpi_retraso_franja.parquet",
    "puntualidad_linea": "kpi_puntualidad_linea.parquet",
}

app = FastAPI(
    title="Plataforma Monitorización Cercanías",
    description="TFM Máster Ingeniería de Datos — Grupo 1",
    version="1.0.0",
)

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_token(key: str = Security(api_key_header)) -> None:
    if key != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido (cabecera X-API-Key)")


def query_df(sql: str) -> pd.DataFrame:
    """Consulta DuckDB con conexión propia por llamada.

    FastAPI atiende peticiones concurrentes en un threadpool y la conexión
    global de duckdb.sql() no es segura entre hilos (500 intermitentes al
    abrir el Centro de Control, que lanza varias peticiones a la vez).
    """
    with duckdb.connect() as con:
        return con.sql(sql).df()


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Aún no hay datos en {path.name}")
    return query_df(f"select * from read_parquet('{path}')")


def _clean_records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _snapshot_epoch(path: Path) -> int:
    """Epoch del snapshot desde el nombre del fichero Bronze.

    Soporta ambas convenciones ('part-<epoch>' local y 'part-YYYYMMDDTHHMMSSZ'
    del servidor); si no es parseable (p. ej. particiones compactadas), usa el
    mtime del fichero.
    """
    token = path.stem.split("-", 1)[1] if "-" in path.stem else ""
    if token.isdigit():
        return int(token)
    try:
        return int(datetime.strptime(token, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return int(path.stat().st_mtime)


@app.get("/salud")
def salud() -> dict:
    """Salud de la plataforma: frescura de ingesta (K1/K2) y componentes."""
    now = time.time()
    feeds = {}
    for feed in ("trip_updates", "vehicle_positions", "alerts"):
        base = DATA_ROOT / "bronze" / feed
        latest = None
        if base.exists():
            dates = sorted(d for d in base.iterdir() if d.name.startswith("date="))
            if dates:
                parts = list(dates[-1].glob("part-*.parquet"))
                if parts:
                    latest = max(_snapshot_epoch(p) for p in parts)
        feeds[feed] = {
            "ultimo_snapshot": latest,
            "antiguedad_s": int(now - latest) if latest else None,
            "ok": latest is not None and now - latest < 300,
        }
    estado = REALTIME / "estado_red.parquet"
    return {
        "hora": datetime.now(timezone.utc).isoformat(),
        "ingesta": feeds,
        "ruta_caliente_ok": estado.exists() and now - estado.stat().st_mtime < 120,
    }


@app.get("/estado", dependencies=[Depends(require_token)])
def estado(linea: str | None = Query(default=None)) -> dict:
    """Estado de la red en tiempo real: último retraso conocido por viaje."""
    df = _read_parquet(REALTIME / "estado_red.parquet")
    if linea:
        df = df[df["linea"] == linea]
    resumen = {
        "viajes_activos": len(df),
        "retraso_medio_min": round(float(df["arrival_delay_min"].mean()), 2) if len(df) else None,
        "semaforo": df["semaforo"].value_counts().to_dict() if len(df) else {},
    }
    return {"resumen": resumen, "viajes": _clean_records(df)}


@app.get("/posiciones", dependencies=[Depends(require_token)])
def posiciones() -> list[dict]:
    """Última posición GPS de cada tren en circulación."""
    return _clean_records(_read_parquet(REALTIME / "posiciones.parquet"))


@app.get("/kpis/{tabla}", dependencies=[Depends(require_token)])
def kpis(tabla: str, fecha: str | None = Query(default=None)) -> list[dict]:
    """KPIs Gold: ingesta (K1/K2), cobertura (K3), retraso_franja (K10/K12), puntualidad_linea."""
    if tabla not in KPI_TABLES:
        raise HTTPException(status_code=404, detail=f"KPI desconocido; disponibles: {list(KPI_TABLES)}")
    df = _read_parquet(GOLD / KPI_TABLES[tabla])
    if fecha and "fecha" in df.columns:
        df = df[df["fecha"].astype(str) == fecha]
    return _clean_records(df)


# ── Endpoints públicos de viajero (webapp) ───────────────────────────────
from viajero import router as viajero_router  # noqa: E402

app.include_router(viajero_router)

# Capas independientes: la geometría se carga una vez; los trenes se refrescan.
from mapa import red as mapa_red, trenes as mapa_trenes

@app.get('/mapa/red', dependencies=[Depends(require_token)], tags=['mapa'])
def mapa_red_endpoint(nucleo: str = Query(min_length=1)) -> dict:
    return mapa_red(nucleo)

@app.get('/mapa/trenes', dependencies=[Depends(require_token)], tags=['mapa'])
def mapa_trenes_endpoint(nucleo: str = Query(min_length=1)) -> dict:
    return mapa_trenes(nucleo)

from tendencias import tendencias as tendencias_red

@app.get('/tendencias', dependencies=[Depends(require_token)], tags=['tendencias'])
def tendencias_endpoint(nucleo: str = Query(min_length=1)) -> dict:
    return tendencias_red(nucleo)
