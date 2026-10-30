FROM python:3.12-slim

RUN pip install --no-cache-dir \
    dbt-duckdb==1.9.1 \
    duckdb==1.1.3 \
    requests==2.32.3

WORKDIR /opt/dbt
ENV DBT_PROFILES_DIR=/opt/dbt

ENTRYPOINT ["dbt"]
CMD ["build"]
