"""DAG semanal: nueva versión del GTFS estático + reentrenamiento del modelo.

1. Descarga y versiona el GTFS estático (requisito H12': se conservan
   todas las versiones para la reconciliación).
2. Reconstruye Silver/Gold con la nueva versión.
3. Reentrena el modelo con backtesting (K6); train.py solo promociona a
   prod si el MAE no empeora el del modelo vigente.
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

ENV = {
    "DATA_ROOT": "/data",
    "DUCKDB_PATH": "/data/warehouse/cercanias.duckdb",
    "GOLD_ROOT": "/data/gold",
    "DBT_PROFILES_DIR": "/opt/dbt",
}

with DAG(
    dag_id="semanal_gtfs_y_modelo",
    description="GTFS estático versionado + reentreno con promoción condicionada",
    schedule="0 4 * * 1",
    start_date=pendulum.datetime(2026, 7, 1, tz="Europe/Madrid"),
    catchup=False,
    tags=["ruta-fria", "gtfs", "ml"],
) as dag:
    descargar_gtfs = BashOperator(
        task_id="descargar_gtfs_estatico",
        bash_command="python /opt/scripts/download_gtfs_static.py --data-root /data",
        env=ENV,
        append_env=True,
    )

    descargar_nucleos = BashOperator(
        task_id="descargar_catalogos_nucleos",
        bash_command="python /opt/scripts/download_nucleos.py",
        env=ENV,
        append_env=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/dbt && dbt build --no-use-colors",
        env=ENV,
        append_env=True,
    )

    entrenar = BashOperator(
        task_id="entrenar_modelo",
        bash_command="python /opt/ml/train.py",
        env=ENV,
        append_env=True,
    )

    descargar_gtfs >> dbt_build >> entrenar
    descargar_nucleos >> dbt_build
