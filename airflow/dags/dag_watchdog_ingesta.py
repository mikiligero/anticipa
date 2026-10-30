"""DAG de vigilancia de la ingesta (H16': la lección del incidente 03/06).

Cada 5 minutos comprueba que el Bronze tiene snapshots recientes de los
tres feeds. Si alguno lleva > 5 min sin datos, el DAG falla y queda
alertado en Airflow (además del healthcheck de Docker + autoheal, que
reinician el contenedor del ingestor automáticamente).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

DATA_ROOT = Path("/data")
FEEDS = ("trip_updates", "vehicle_positions", "alerts")
MAX_AGE_S = 300


def _snapshot_epoch(path: Path) -> int:
    """Soporta 'part-<epoch>' (local), 'part-YYYYMMDDTHHMMSSZ' (servidor) y
    particiones compactadas (mtime como último recurso)."""
    token = path.stem.split("-", 1)[1] if "-" in path.stem else ""
    if token.isdigit():
        return int(token)
    try:
        return int(datetime.strptime(token, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return int(path.stat().st_mtime)


def comprobar_frescura() -> None:
    ahora = time.time()
    problemas = []
    for feed in FEEDS:
        base = DATA_ROOT / "bronze" / feed
        ultimo = None
        if base.exists():
            fechas = sorted(d for d in base.iterdir() if d.name.startswith("date="))
            if fechas:
                partes = list(fechas[-1].glob("part-*.parquet"))
                if partes:
                    ultimo = max(_snapshot_epoch(p) for p in partes)
        if ultimo is None:
            problemas.append(f"{feed}: sin datos en Bronze")
        elif ahora - ultimo > MAX_AGE_S:
            problemas.append(f"{feed}: último snapshot hace {int(ahora - ultimo)}s")
    if problemas:
        raise RuntimeError("Ingesta degradada → " + " · ".join(problemas))
    print("Ingesta OK: los tres feeds tienen snapshots recientes")


with DAG(
    dag_id="watchdog_ingesta",
    description="Vigilancia de frescura del Bronze (K1/K2)",
    schedule="*/5 * * * *",
    start_date=pendulum.datetime(2026, 7, 1, tz="Europe/Madrid"),
    catchup=False,
    max_active_runs=1,
    tags=["observabilidad"],
) as dag:
    PythonOperator(task_id="comprobar_frescura", python_callable=comprobar_frescura)
