"""Ruta caliente (Spark Structured Streaming).

Consume los topics de Kafka publicados por el ingestor y mantiene dos
tablas de estado en Gold, refrescadas en micro-batches de 30 s
(latencia extremo a extremo objetivo < 60 s, KPI K5):

  - /data/gold/realtime/estado_red.parquet   → último retraso por viaje
  - /data/gold/realtime/posiciones.parquet   → última posición por vehículo

El estado se enriquece con dim_lineas / dim_estaciones (Gold de dbt) y
se escribe de forma atómica (tmp + rename) para que API y dashboard
siempre lean un fichero consistente.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s stream %(message)s")
log = logging.getLogger("stream")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092")
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
REALTIME_DIR = DATA_ROOT / "gold" / "realtime"
CHECKPOINT_DIR = DATA_ROOT / "checkpoints"
STATE_TTL_S = int(os.environ.get("STATE_TTL_S", "1800"))  # 30 min
TRIGGER = os.environ.get("TRIGGER", "30 seconds")

TU_SCHEMA = StructType(
    [
        StructField("snapshot_ts", LongType()),
        StructField("ingested_at", StringType()),
        StructField("entity_id", StringType()),
        StructField("trip_id", StringType()),
        StructField("vehicle_id", StringType()),
        StructField("stop_sequence", IntegerType()),
        StructField("stop_id", StringType()),
        StructField("arrival_delay", IntegerType()),
        StructField("arrival_time", LongType()),
        StructField("departure_delay", IntegerType()),
        StructField("departure_time", LongType()),
        StructField("schedule_relationship", IntegerType()),
    ]
)

VP_SCHEMA = StructType(
    [
        StructField("snapshot_ts", LongType()),
        StructField("ingested_at", StringType()),
        StructField("entity_id", StringType()),
        StructField("trip_id", StringType()),
        StructField("vehicle_id", StringType()),
        StructField("vehicle_label", StringType()),
        StructField("latitude", DoubleType()),
        StructField("longitude", DoubleType()),
        StructField("bearing", DoubleType()),
        StructField("speed_ms", DoubleType()),
        StructField("stop_id", StringType()),
        StructField("current_stop_sequence", IntegerType()),
        StructField("current_status", IntegerType()),
    ]
)


class Dimensions:
    """Dimensiones Gold (dbt) recargadas periódicamente."""

    def __init__(self, ttl_s: int = 600):
        self.ttl_s = ttl_s
        self._loaded_at = 0.0
        self.lineas: pd.DataFrame | None = None
        self.estaciones: pd.DataFrame | None = None

    def refresh(self) -> None:
        if time.time() - self._loaded_at < self.ttl_s:
            return
        try:
            p = DATA_ROOT / "gold" / "dim_lineas.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                cols = [c for c in ("trip_id", "linea", "route_id", "trip_headsign", "destino") if c in df.columns]
                self.lineas = df[cols]
            p = DATA_ROOT / "gold" / "dim_estaciones.parquet"
            if p.exists():
                self.estaciones = pd.read_parquet(p)[["stop_id", "stop_name"]]
            self._loaded_at = time.time()
        except Exception:  # noqa: BLE001
            log.exception("No se pudieron recargar las dimensiones (se sigue sin ellas)")


DIMS = Dimensions()
_STATE: dict[str, dict[str, pd.DataFrame]] = {"tu": {}, "vp": {}}
_FIRST_SEEN: dict[str, int] = {}  # trip_id → primer snapshot_ts observado


def _atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def _semaforo(delay_min: float) -> str:
    if delay_min is None or pd.isna(delay_min):
        return "gris"
    if delay_min < 5:
        return "verde"
    if delay_min <= 10:
        return "ambar"
    return "rojo"


def _update_state(kind: str, batch: pd.DataFrame, key: str) -> pd.DataFrame:
    """Fusiona el batch en el estado (último registro por clave) y poda por TTL."""
    state = _STATE[kind]
    if not batch.empty:
        batch = batch.sort_values("snapshot_ts").groupby(key, as_index=False).last()
        for _, row in batch.iterrows():
            state[row[key]] = row
    if state:
        df = pd.DataFrame(list(state.values()))
        cutoff = df["snapshot_ts"].max() - STATE_TTL_S
        df = df[df["snapshot_ts"] >= cutoff]
        _STATE[kind] = {r[key]: r for _, r in df.iterrows()}
        return df
    return pd.DataFrame()


def _enrich_linea(df: pd.DataFrame) -> pd.DataFrame:
    """Completa líneas ausentes con etiquetas del feed de posiciones reciente."""
    df = df.copy()
    if "linea" not in df:
        df["linea"] = None
    missing = df["linea"].fillna("").str.strip().eq("")
    path = REALTIME_DIR / "posiciones.parquet"
    if not missing.any() or not path.exists():
        return df
    try:
        vp = pd.read_parquet(path)
        vp = vp.dropna(subset=["trip_id", "linea_label", "snapshot_ts"])
        vp = vp[vp["snapshot_ts"] >= time.time() - STATE_TTL_S].copy()
        vp["trip_id"] = vp["trip_id"].str.strip()
        vp = vp.sort_values("snapshot_ts").drop_duplicates("trip_id", keep="last")
        mapping = vp.set_index("trip_id")["linea_label"]
        df.loc[missing, "linea"] = df.loc[missing, "trip_id"].str.strip().map(mapping)
    except Exception:
        log.exception("No se pudieron completar las líneas desde posiciones")
    return df


def process_tu(batch_df, batch_id: int) -> None:
    pdf = batch_df.toPandas()
    if not pdf.empty:
        # Mismo filtro de rango que la capa Silver (EDA: -5 a +120 min);
        # fuera de rango se trata como dato sin fiabilidad y se descarta.
        pdf = pdf[
            pdf["trip_id"].notna()
            & pdf["arrival_delay"].notna()
            & pdf["arrival_delay"].between(-300, 7200)
        ]
    df = _update_state("tu", pdf, "trip_id")
    if df.empty:
        return
    DIMS.refresh()
    df = df.copy()
    df["trip_id"] = df["trip_id"].str.strip()
    df["arrival_delay_min"] = (df["arrival_delay"] / 60.0).round(2)
    # primer avistamiento de cada viaje (feature min_desde_inicio del modelo)
    for tid, ts in zip(df["trip_id"], df["snapshot_ts"]):
        _FIRST_SEEN.setdefault(tid, int(ts))
    activos = set(df["trip_id"])
    for tid in list(_FIRST_SEEN):
        if tid not in activos:
            _FIRST_SEEN.pop(tid)
    df["min_desde_inicio"] = df.apply(
        lambda r: round((r["snapshot_ts"] - _FIRST_SEEN.get(r["trip_id"], r["snapshot_ts"])) / 60.0, 1),
        axis=1,
    )
    if DIMS.lineas is not None:
        df = df.merge(DIMS.lineas, on="trip_id", how="left")
    df = _enrich_linea(df)
    if DIMS.estaciones is not None:
        df = df.merge(DIMS.estaciones, on="stop_id", how="left")
    df["semaforo"] = df["arrival_delay_min"].map(_semaforo)
    df["updated_at"] = pd.Timestamp.utcnow().isoformat()
    _atomic_write(df, REALTIME_DIR / "estado_red.parquet")
    log.info("batch %s: estado_red con %d viajes activos", batch_id, len(df))


def process_vp(batch_df, batch_id: int) -> None:
    pdf = batch_df.toPandas()
    pdf = pdf[pdf["vehicle_id"].notna()] if not pdf.empty else pdf
    df = _update_state("vp", pdf, "vehicle_id")
    if df.empty:
        return
    df = df.copy()
    df["linea_label"] = df["vehicle_label"].str.extract(r"^([A-Z]+[0-9]+[a-z]?)", expand=False)
    df["updated_at"] = pd.Timestamp.utcnow().isoformat()
    _atomic_write(df, REALTIME_DIR / "posiciones.parquet")
    log.info("batch %s: posiciones con %d vehículos", batch_id, len(df))


def _read_topic(spark: SparkSession, topic: str, schema: StructType):
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
        .select(from_json(col("value").cast("string"), schema).alias("j"))
        .select("j.*")
    )


def main() -> None:
    spark = (
        SparkSession.builder.appName("cercanias-ruta-caliente")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    tu = _read_topic(spark, "cercanias.trip_updates", TU_SCHEMA)
    vp = _read_topic(spark, "cercanias.vehicle_positions", VP_SCHEMA)

    q1 = (
        tu.writeStream.foreachBatch(process_tu)
        .option("checkpointLocation", str(CHECKPOINT_DIR / "tu"))
        .trigger(processingTime=TRIGGER)
        .start()
    )
    q2 = (
        vp.writeStream.foreachBatch(process_vp)
        .option("checkpointLocation", str(CHECKPOINT_DIR / "vp"))
        .trigger(processingTime=TRIGGER)
        .start()
    )
    log.info("Streaming arrancado sobre %s (trigger %s)", KAFKA_BOOTSTRAP, TRIGGER)
    q1.awaitTermination()
    q2.awaitTermination()


if __name__ == "__main__":
    main()
