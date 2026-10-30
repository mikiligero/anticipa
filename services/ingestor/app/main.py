"""Capturador continuo de los feeds GTFS-Realtime de Renfe.

Bucle cada POLL_SECONDS:
  1. Descarga cada feed (.pb).
  2. Dedup por header.timestamp (si el snapshot no cambió, se omite).
  3. Persiste raw (.pb) y Bronze (Parquet particionado Hive por fecha).
  4. Publica en Kafka (best-effort) para la ruta caliente.
  5. Late el healthcheck (H16': vigilancia + rearranque automático).
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path

import requests

from parsers import parse_feed
from sinks import BronzeSink, Health, KafkaSink, RawSink

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("ingestor")

FEEDS = {
    "vehicle_positions": "https://gtfsrt.renfe.com/vehicle_positions.pb",
    "trip_updates": "https://gtfsrt.renfe.com/trip_updates.pb",
    "alerts": "https://gtfsrt.renfe.com/alerts.pb",
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "30"))
HEALTH_FILE = Path(os.environ.get("HEALTH_FILE", "/tmp/ingestor_health"))
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "")

_running = True


def _stop(signum, _frame):
    global _running
    log.info("Señal %s recibida: parada ordenada", signum)
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    raw = RawSink(DATA_ROOT / "raw")
    bronze = BronzeSink(DATA_ROOT / "bronze")
    kafka = KafkaSink(KAFKA_BOOTSTRAP)
    health = Health(HEALTH_FILE)

    session = requests.Session()
    session.headers["User-Agent"] = "tfm-cercanias-ingestor/1.0"
    last_ts: dict[str, int] = {}

    log.info("Ingestor arrancado: cadencia %ss, datos en %s", POLL_SECONDS, DATA_ROOT)

    while _running:
        cycle_start = time.monotonic()
        ok_any = False
        for feed, url in FEEDS.items():
            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
                ts, rows = parse_feed(feed, resp.content)
                if ts and ts == last_ts.get(feed):
                    ok_any = True  # el feed responde, aunque no haya snapshot nuevo
                    continue
                raw.write(feed, ts, resp.content)
                bronze.write(feed, ts, rows)
                kafka.publish(feed, rows)
                last_ts[feed] = ts
                ok_any = True
                log.info("%s: snapshot %s con %d filas", feed, ts, len(rows))
            except Exception:  # noqa: BLE001
                log.exception("Error capturando %s (se reintenta en el próximo ciclo)", feed)
        if ok_any:
            health.beat()
        elapsed = time.monotonic() - cycle_start
        time.sleep(max(0.0, POLL_SECONDS - elapsed))

    kafka.flush()
    log.info("Ingestor detenido")


if __name__ == "__main__":
    main()
