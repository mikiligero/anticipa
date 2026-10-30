"""DAG horario: ingesta de AEMET OpenData (enriquecimiento H14).

Si no hay AEMET_API_KEY configurada, el script sale limpio (fuente opcional).
"""
from __future__ import annotations

import os

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="horario_aemet",
    description="Predicción meteorológica horaria (variable explicativa del modelo)",
    schedule="@hourly",
    start_date=pendulum.datetime(2026, 7, 1, tz="Europe/Madrid"),
    catchup=False,
    tags=["enriquecimiento"],
) as dag:
    ingesta = BashOperator(
        task_id="ingesta_aemet",
        bash_command="python /opt/scripts/ingest_aemet.py",
        env={
            "DATA_ROOT": "/data",
            "AEMET_API_KEY": os.environ.get("AEMET_API_KEY", ""),
            "AEMET_MUNICIPIO": os.environ.get("AEMET_MUNICIPIO", "28079"),
        },
        append_env=True,
    )
