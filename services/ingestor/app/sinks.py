"""Destinos de la ingesta: raw (.pb), Bronze (Parquet) y Kafka.

Principio de diseño (Sprint 2, capa Bronze): el dato bruto se persiste
SIEMPRE antes de cualquier otra cosa. Kafka es best-effort: si el broker
no está disponible, la captura continúa conservando los datos en Bronze.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger("ingestor")

TZ_MADRID = ZoneInfo("Europe/Madrid")


def service_date(snapshot_ts: int) -> str:
    """Fecha local de Madrid del snapshot — clave de partición Hive."""
    return datetime.fromtimestamp(snapshot_ts, tz=TZ_MADRID).strftime("%Y-%m-%d")


class RawSink:
    def __init__(self, root: Path):
        self.root = root

    def write(self, feed: str, snapshot_ts: int, payload: bytes) -> Path:
        d = self.root / feed / service_date(snapshot_ts)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{snapshot_ts}.pb"
        tmp = path.with_suffix(".pb.tmp")
        tmp.write_bytes(payload)
        tmp.rename(path)  # escritura atómica
        return path


class BronzeSink:
    def __init__(self, root: Path):
        self.root = root

    def write(self, feed: str, snapshot_ts: int, rows: list[dict]) -> Path | None:
        if not rows:
            return None
        d = self.root / feed / f"date={service_date(snapshot_ts)}"
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"part-{snapshot_ts}.parquet"
        if path.exists():  # dedup extra por si acaso
            return path
        table = pa.Table.from_pylist(rows)
        tmp = d / f".part-{snapshot_ts}.parquet.tmp"
        pq.write_table(table, tmp, compression="snappy")
        tmp.rename(path)
        return path


class KafkaSink:
    """Productor best-effort. Nunca bloquea la captura."""

    TOPICS = {
        "vehicle_positions": "cercanias.vehicle_positions",
        "trip_updates": "cercanias.trip_updates",
        "alerts": "cercanias.alerts",
    }

    def __init__(self, bootstrap: str | None):
        self._producer = None
        self._bootstrap = bootstrap
        if not bootstrap:
            log.warning("KAFKA_BOOTSTRAP vacío: publicación en Kafka desactivada")
            return
        try:
            from confluent_kafka import Producer

            self._producer = Producer(
                {
                    "bootstrap.servers": bootstrap,
                    "linger.ms": 100,
                    "queue.buffering.max.messages": 200_000,
                    "message.timeout.ms": 30_000,
                }
            )
        except Exception:  # noqa: BLE001
            log.exception("No se pudo crear el productor Kafka; se continúa sin él")

    def publish(self, feed: str, rows: list[dict]) -> None:
        if self._producer is None or not rows:
            return
        topic = self.TOPICS[feed]
        try:
            for row in rows:
                self._producer.produce(topic, json.dumps(row, default=_json_default).encode())
            self._producer.poll(0)
        except BufferError:
            log.warning("Buffer de Kafka lleno: se descartan mensajes de %s", feed)
            self._producer.poll(0)
        except Exception:  # noqa: BLE001
            log.exception("Error publicando en Kafka (se ignora)")

    def flush(self, timeout: float = 5.0) -> None:
        if self._producer is not None:
            self._producer.flush(timeout)


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    raise TypeError(f"No serializable: {type(obj)}")


class Health:
    """Fichero de salud que consulta el healthcheck de Docker."""

    def __init__(self, path: Path):
        self.path = path

    def beat(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(int(datetime.now(timezone.utc).timestamp())))
