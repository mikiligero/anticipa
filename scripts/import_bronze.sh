#!/usr/bin/env bash
# Importa el histórico Bronze (y opcionalmente raw) desde el servidor de
# captura al volumen local ./data. El layout es idéntico, así que dbt y el
# resto de la plataforma funcionan sobre él sin transformación alguna.
#
# Uso:
#   ./scripts/import_bronze.sh root@cercanias [ruta_remota] [--with-raw]
#
set -euo pipefail

HOST="${1:?Uso: import_bronze.sh usuario@host [ruta_remota] [--with-raw]}"
REMOTE_ROOT="${2:?Indica la ruta remota de datos del proyecto de origen}"
LOCAL_ROOT="$(cd "$(dirname "$0")/.." && pwd)/data"

echo "→ Importando Bronze desde ${HOST}:${REMOTE_ROOT}/bronze/ a ${LOCAL_ROOT}/bronze/"
rsync -avz --progress --partial \
  "${HOST}:${REMOTE_ROOT}/bronze/" "${LOCAL_ROOT}/bronze/"

if [[ "${3:-}" == "--with-raw" ]]; then
  echo "→ Importando raw (.pb) — puede tardar"
  rsync -avz --progress --partial \
    "${HOST}:${REMOTE_ROOT}/raw/" "${LOCAL_ROOT}/raw/"
fi

echo "✓ Importación completada. Siguiente paso: docker compose run --rm dbt build"
