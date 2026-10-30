COMPOSE ?= docker compose
.PHONY: init up down logs ps config gtfs nucleos mapa bootstrap dbt dbt-test
init:
	python3 scripts/init_project.py
config:
	$(COMPOSE) config --quiet
up:
	$(COMPOSE) up -d --build
bootstrap:
	$(COMPOSE) run --rm tools python /opt/scripts/bootstrap.py --data-root /data

gtfs:
	$(COMPOSE) run --rm tools python /opt/scripts/download_gtfs_static.py --data-root /data --full
nucleos:
	$(COMPOSE) run --rm tools python /opt/scripts/download_nucleos.py
mapa:
	$(COMPOSE) run --rm tools python /opt/scripts/prepare_map.py --data-root /data
dbt:
	$(COMPOSE) run --rm dbt build
dbt-test:
	$(COMPOSE) run --rm dbt test
ps:
	$(COMPOSE) ps
logs:
	$(COMPOSE) logs -f --tail=100
down:
	$(COMPOSE) down
