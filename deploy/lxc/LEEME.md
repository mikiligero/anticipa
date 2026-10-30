# Despliegue del TFM en un LXC compartido

La aplicación usa `docker-compose.yml` y `deploy/lxc/compose.yml`. Este último solo añade límites de recursos. Las rutas son relativas y no incluye credenciales ni direcciones privadas.

## Instalación nueva

```sh
python3 scripts/init_project.py
make COMPOSE="docker compose -f docker-compose.yml -f deploy/lxc/compose.yml" config
make COMPOSE="docker compose -f docker-compose.yml -f deploy/lxc/compose.yml" bootstrap
make COMPOSE="docker compose -f docker-compose.yml -f deploy/lxc/compose.yml" up
```

Ajusta las direcciones de escucha y los puertos en `.env` según la red. Por defecto: web 3000, dashboard 18501, API solo en localhost:18000. El otro proyecto puede conservar su puerto 8501.

Las credenciales del operador están en `.secrets/access.txt`; nginx lee el hash de `.secrets/operator.htpasswd`. No se deben versionar. El inicializador conserva archivos existentes. Para migrar una instalación, conserva el token API y copia el hash actual a la nueva ruta privada antes de arrancar.

## Migración desde la demo anterior

1. Conservar `.env`, el directorio `data/`, el volumen Kafka existente y las credenciales privadas.
2. Copiar `operator.htpasswd` a `.secrets/operator.htpasswd`, sin cambiar su contenido.
3. Validar el Compose común con `config --quiet`.
4. Reconstruir API, web y dashboard con el código actualizado.
5. Usar el complemento LXC para conservar los límites de memoria. No usar el antiguo `compose.server.json`; sus copias locales quedan excluidas de Git.
6. Verificar autenticación, viajero, operador, mapa, tendencias y Streamlit antes de retirar archivos obsoletos.

No copiar ni modificar el proyecto alojado fuera de la carpeta del TFM. No borrar volúmenes ni checkpoints durante una limpieza de código.

## Actualizar las pantallas

```sh
docker compose -f docker-compose.yml -f deploy/lxc/compose.yml build api webapp dashboard
docker compose -f docker-compose.yml -f deploy/lxc/compose.yml up -d --no-deps api webapp dashboard
```

Las actualizaciones forman parte de las imágenes. No requieren montajes de código distintos a los del repositorio. Para verificar o parar los servicios, usar siempre los mismos archivos de Compose.

## Alcance

Captura, streaming, mapa y tendencias usan datos reales. Las predicciones de ejemplo llevan su aviso de simulación. Los archivos históricos de una instalación previa pueden conservarse como evidencia; una instalación nueva los genera al ejecutar dbt sobre su propio Bronze. Airflow y entrenamiento permanecen opcionales y no se activan con `make up`.
