FROM apache/airflow:2.10.3-python3.12

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*
USER airflow

# Dependencias de los DAGs: dbt (ruta fría), ML (reentreno) y scripts de datos
RUN pip install --no-cache-dir \
    dbt-duckdb==1.9.1 \
    duckdb==1.1.3 \
    pandas==2.2.3 \
    pyarrow==17.0.0 \
    lightgbm==4.5.0 \
    scikit-learn==1.5.2 \
    joblib==1.4.2 \
    requests==2.32.3
