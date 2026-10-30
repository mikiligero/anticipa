"""Catálogos de estaciones por núcleo (data.renfe.com, Open Data oficial).

Descarga los 13 CSVs (uno por núcleo de Cercanías/Rodalies) y construye la
dimensión estación → núcleo en /data/nucleos/estaciones_nucleo.parquet.
Permite a la app de viajero filtrar la red por núcleo (Madrid por defecto).

Los stop_id se normalizan a 5 dígitos (zfill): los CSVs pierden los ceros a
la izquierda al venir los códigos como número.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import sys
from pathlib import Path

import duckdb
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s nucleos %(message)s")
log = logging.getLogger("nucleos")

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))

NUCLEOS = {
    "Madrid": "https://data.renfe.com/dataset/0b763a1a-860d-4346-8818-765d2559248f/resource/daa68d9b-77cf-4024-890f-285d31184c5a/download/listado-estaciones-cercanias-madrid.csv",
    "Barcelona": "https://data.renfe.com/dataset/8bdd06a5-f7f6-4f21-9cb6-b76f39842726/resource/e3969f12-aff2-468e-9b82-a65a6dd1a0d3/download/listado-estaciones-rodalies-barcelona.csv",
    "Valencia": "https://data.renfe.com/dataset/b5a039a1-4f02-4f9c-b617-a94d55779647/resource/0b1caf38-e6a9-4965-a94d-9a24c5a4ae84/download/listado-estaciones-cercanias-valencia.csv",
    "Sevilla": "https://data.renfe.com/dataset/d13549fe-f132-4633-aa50-5ed70b2f71dd/resource/ac3b4229-1c69-412f-a6de-29df913ece92/download/listado-estaciones-cercanias-sevilla.csv",
    "Bilbao": "https://data.renfe.com/dataset/0356d125-ddd2-4db2-9f10-3083c91f3e2a/resource/3254a1ed-a2b7-4fd1-9e9e-23eefe35f162/download/listado-estaciones-cercanias-bilbao.csv",
    "Murcia/Alicante": "https://data.renfe.com/dataset/9b7b24d0-57d0-489c-bcd6-cb78e96135e1/resource/1d17b744-4c68-4578-bdc3-b51457892967/download/listado-estaciones-cercanias-murcia-alicante.csv",
    "Zaragoza": "https://data.renfe.com/dataset/479fa2dd-76e0-4a97-ac88-b848943f9133/resource/9651ce18-9437-4274-ad04-143f1cc9e6db/download/listado-estaciones-cercanias-zaragoza_2.csv",
    "Málaga": "https://data.renfe.com/dataset/9cd08424-f617-4adb-a230-68abdb2c8abf/resource/4b651d25-3fed-4f6a-be4d-18352d7e2aea/download/listado-estaciones-cercanias-malaga-v4.csv",
    "Asturias": "https://data.renfe.com/dataset/a94a67b4-c353-417c-b471-284998bc257d/resource/6b73014a-e5bd-4b0e-b17b-1f8abe47a90f/download/listado-estaciones-cercanias-asturias.csv",
    "Cádiz": "https://data.renfe.com/dataset/d2197774-6671-45a7-ad3b-eadac1b66475/resource/2c3afbbd-30f6-41b1-815a-6ef452457f92/download/cercanias-cadiz-.csv",
    "Santander": "https://data.renfe.com/dataset/aa5cf888-f8b9-4824-b60a-7ae3ba6ec32b/resource/18dd8342-b68e-4846-9e52-1a96faf85e80/download/listado-estaciones-cercanias-santander.csv",
    "San Sebastián": "https://data.renfe.com/dataset/f3dc3712-cc1e-4b23-ada0-50562e9cf38b/resource/e8e8d882-865e-4032-8d39-d60cd0cfcdff/download/listado-estaciones-cercanias-san-sebastian.csv",
}


def _num(v: str) -> float | None:
    try:
        return float(v.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def parse_csv(nucleo: str, texto: str) -> list[tuple]:
    rows = []
    reader = csv.DictReader(io.StringIO(texto), delimiter=";")
    # cabeceras con BOM/espacios/acentos variables entre núcleos
    campos = {k.strip().upper().replace("﻿", ""): k for k in (reader.fieldnames or [])}
    col_cod = next((campos[c] for c in campos if "CÓDIGO" in c or "CODIGO" in c), None)
    col_nom = next((campos[c] for c in campos if "DESCRIPCION" in c or "DESCRIPCIÓN" in c or "ESTACION" in c), None)
    col_lat = next((campos[c] for c in campos if "LATITUD" in c), None)
    col_lon = next((campos[c] for c in campos if "LONGITUD" in c), None)
    if not col_cod:
        log.warning("%s: no se encontró columna de código (%s)", nucleo, reader.fieldnames)
        return rows
    for r in reader:
        cod = (r.get(col_cod) or "").strip()
        if not cod or not cod.isdigit():
            continue
        rows.append(
            (
                nucleo,
                cod.zfill(5),
                (r.get(col_nom) or "").strip().title() or None,
                _num(r.get(col_lat)) if col_lat else None,
                _num(r.get(col_lon)) if col_lon else None,
            )
        )
    return rows


def main() -> int:
    todas: list[tuple] = []
    for nucleo, url in NUCLEOS.items():
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            filas = parse_csv(nucleo, resp.content.decode("utf-8-sig", errors="replace"))
            todas.extend(filas)
            log.info("%s: %d estaciones", nucleo, len(filas))
        except Exception:  # noqa: BLE001
            log.exception("%s: error descargando (se continúa con el resto)", nucleo)

    if not todas:
        log.error("No se descargó ningún catálogo")
        return 1

    out_dir = DATA_ROOT / "nucleos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "estaciones_nucleo.parquet"
    con = duckdb.connect()
    con.execute("create table est (nucleo varchar, stop_id varchar, nombre varchar, lat double, lon double)")
    con.executemany("insert into est values (?, ?, ?, ?, ?)", todas)
    con.execute(f"copy (select distinct * from est) to '{out}' (format parquet, compression snappy)")
    log.info("Dimensión estación→núcleo: %d filas en %s", len(todas), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
