"""Ingesta horaria de AEMET OpenData (enriquecimiento H14).

Guarda la respuesta JSON íntegra (principio Bronze: dato bruto primero) en
  data/aemet/date=YYYY-MM-DD/prediccion_{municipio}_{HH}.json

Si AEMET_API_KEY está vacío, sale sin error (fuente opcional del piloto).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s aemet %(message)s")
log = logging.getLogger("aemet")

API_KEY = os.environ.get("AEMET_API_KEY", "")
MUNICIPIO = os.environ.get("AEMET_MUNICIPIO", "28079")
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
BASE = "https://opendata.aemet.es/opendata/api"


def main() -> int:
    if not API_KEY:
        log.info("AEMET_API_KEY vacío: ingesta de meteorología omitida")
        return 0

    now = datetime.now(ZoneInfo("Europe/Madrid"))
    url = f"{BASE}/prediccion/especifica/municipio/horaria/{MUNICIPIO}"
    meta = requests.get(url, params={"api_key": API_KEY}, timeout=60)
    meta.raise_for_status()
    datos_url = meta.json().get("datos")
    if not datos_url:
        log.error("Respuesta AEMET sin campo 'datos': %s", meta.text[:200])
        return 1
    datos = requests.get(datos_url, timeout=60)
    datos.raise_for_status()

    out_dir = DATA_ROOT / "aemet" / f"date={now:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"prediccion_{MUNICIPIO}_{now:%H}.json"
    out.write_text(json.dumps(datos.json(), ensure_ascii=False))
    log.info("Guardado %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
