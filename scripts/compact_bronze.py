"""Compactación del Bronze: un parquet por (feed, día) para los días cerrados.

Motivo: la ingesta escribe un parquet por snapshot (~2.880/día y feed). Con
semanas de histórico son cientos de miles de ficheros diminutos y el escaneo
de metadatos ahoga a DuckDB/dbt. Compactar el día cerrado en un único fichero
reduce ~2.880 ficheros → 1 sin tocar el contenido (el raw .pb sigue siendo el
origen inmutable para auditoría).

Además aplica `select distinct *`: elimina duplicados exactos cuando el mismo
día existe capturado por dos procesos (p. ej. servidor + local).

El día de HOY (hora Madrid) nunca se compacta: sigue en append por el ingestor.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s compact %(message)s")
log = logging.getLogger("compact")

FEEDS = ("trip_updates", "vehicle_positions", "alerts")
COMPACT_NAME = "part-00000-compact.parquet"


def compact_dir(con: duckdb.DuckDBPyConnection, d: Path) -> None:
    files = sorted(d.glob("*.parquet"))
    if len(files) <= 1:
        return
    tmp = d / (COMPACT_NAME + ".tmp")
    try:
        antes = con.sql(
            f"select count(distinct snapshot_ts) from read_parquet('{d}/*.parquet', union_by_name=true)"
        ).fetchone()[0]
        con.sql(
            f"copy (select distinct * from read_parquet('{d}/*.parquet', union_by_name=true)) "
            f"to '{tmp}' (format parquet, compression snappy)"
        )
        despues = con.sql(f"select count(distinct snapshot_ts) from read_parquet('{tmp}')").fetchone()[0]
        if despues != antes:
            raise RuntimeError(f"verificación fallida: {antes} snapshots antes vs {despues} después")
        for f in files:
            f.unlink()
        tmp.rename(d / COMPACT_NAME)
        log.info("%s: %d ficheros → 1 (%d snapshots)", d, len(files), despues)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="/data")
    args = parser.parse_args()

    hoy = f"date={datetime.now(ZoneInfo('Europe/Madrid')):%Y-%m-%d}"
    con = duckdb.connect()
    con.sql("set memory_limit='1GB'")
    errores = 0
    for feed in FEEDS:
        base = Path(args.data_root) / "bronze" / feed
        if not base.exists():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir() and p.name.startswith("date=")):
            if d.name == hoy:
                continue  # el día abierto sigue en append
            try:
                compact_dir(con, d)
            except Exception:  # noqa: BLE001
                errores += 1
                log.exception("Error compactando %s (se continúa)", d)
    if errores:
        log.error("%d particiones con error", errores)
        return 1
    log.info("Compactación completada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
