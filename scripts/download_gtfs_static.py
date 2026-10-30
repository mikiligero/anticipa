"""Descarga GTFS versionado: conserva el ZIP original y genera Parquet normalizados.
stop_times se incluye siempre; --full añade shapes cuando Renfe lo publica.
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from pathlib import Path

import duckdb
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s gtfs %(message)s")
log = logging.getLogger("gtfs")

GTFS_URL = "https://ssl.renfe.com/ftransit/Fichero_CER_FOMENTO/fomento_transit.zip"
# stop_times es pesado (~250 MB CSV) pero imprescindible: es la única fuente
# del destino final de cada viaje (trip_headsign viene vacío en Renfe)
BASE_FILES = ["trips", "routes", "stops", "calendar", "stop_times"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=os.environ.get("DATA_ROOT", "/data"))
    parser.add_argument("--gtfs-zip", type=Path, help="Usar un ZIP local en lugar de descargar")
    parser.add_argument("--full", action="store_true", help="incluir también shapes (geometría)")
    parser.add_argument("--force", action="store_true", help="re-descargar aunque exista la versión de hoy")
    args = parser.parse_args()

    version = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    out_dir = Path(args.data_root) / "gtfs_static" / f"version={version}"
    if (out_dir / "feed.zip").exists() and not args.force and (not args.full or (out_dir / "shapes.parquet").exists()):
        log.info("La versión %s ya existe: nada que hacer (usa --force para repetir)", version)
        return

    if args.gtfs_zip:
        payload = args.gtfs_zip.read_bytes()
    else:
        log.info("Descargando %s ...", GTFS_URL)
        resp = requests.get(GTFS_URL, timeout=300)
        resp.raise_for_status()
        payload = resp.content
    log.info("GTFS: %.1f MB", len(payload) / 1e6)

    files = BASE_FILES + (["shapes"] if args.full else [])
    # Sin '=' en el nombre temporal: DuckDB auto-detecta particiones Hive en
    # la ruta y contaminaría los parquet con una columna espuria.
    tmp_dir = out_dir.parent / f".tmp_{version}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    (tmp_dir / "feed.zip").write_bytes(payload)
    con = duckdb.connect()
    con.sql("set memory_limit='1GB'")
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for name in files:
            txt = f"{name}.txt"
            if txt not in zf.namelist():
                log.warning("%s no está en el ZIP: se omite", txt)
                continue
            csv_path = tmp_dir / txt
            csv_path.write_bytes(zf.read(txt))
            parquet_path = tmp_dir / f"{name}.parquet"
            relation = con.read_csv(str(csv_path), all_varchar=True, hive_partitioning=False)
            quoted = lambda name: '"' + name.replace('"', '""') + '"'
            relation.project(', '.join(f'{quoted(c)} as {quoted(c.strip())}' for c in relation.columns)).write_parquet(str(parquet_path),compression='snappy')
            csv_path.unlink()
            log.info("%s → %s", txt, parquet_path.name)

    if out_dir.exists():
        import shutil

        shutil.rmtree(out_dir)
    tmp_dir.rename(out_dir)
    log.info("GTFS estático versionado en %s", out_dir)


if __name__ == "__main__":
    sys.exit(main())
