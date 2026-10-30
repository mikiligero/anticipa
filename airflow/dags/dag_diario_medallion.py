"""DAG diario (ruta fría): consolidación Bronze → Silver → Gold con dbt.

Se ejecuta de madrugada, tras el cierre del servicio (Sprint 2, 4.2).
Los tests de dbt son bloqueantes: si la calidad falla (K4), el dato
defectuoso no se promociona y el DAG queda en fallo (alertado).
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_ENV = {
    "DATA_ROOT": "/data",
    "DUCKDB_PATH": "/data/warehouse/cercanias.duckdb",
    "GOLD_ROOT": "/data/gold",
    "DBT_PROFILES_DIR": "/opt/dbt",
}

with DAG(
    dag_id="diario_medallion",
    description="Compactación del Bronze + Bronze → Silver → Gold (dbt con tests bloqueantes)",
    schedule="30 3 * * *",
    start_date=pendulum.datetime(2026, 7, 1, tz="Europe/Madrid"),
    catchup=False,
    tags=["ruta-fria", "dbt"],
) as dag:
    # Un parquet por día cerrado: sin esto, los ~2.880 ficheros/día por feed
    # acaban ahogando el escaneo de metadatos de DuckDB
    compactar = BashOperator(
        task_id="compactar_bronze",
        bash_command="python /opt/scripts/compact_bronze.py --data-root /data",
        env=DBT_ENV,
        append_env=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/dbt && dbt build --no-use-colors",
        env=DBT_ENV,
        append_env=True,
    )

    compactar >> dbt_build
