#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest discover -s services/api/tests -v
python3 -m unittest discover -s tests -v
(cd services/webapp && npm ci --no-audit --no-fund && npm run build)
