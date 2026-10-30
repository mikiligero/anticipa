"""Healthcheck de Docker: falla si el último latido tiene más de MAX_AGE s."""
import os
import sys
import time
from pathlib import Path

HEALTH_FILE = Path(os.environ.get("HEALTH_FILE", "/tmp/ingestor_health"))
MAX_AGE = int(os.environ.get("HEALTH_MAX_AGE", "120"))

try:
    last = int(HEALTH_FILE.read_text().strip())
except Exception:  # noqa: BLE001
    sys.exit(1)

sys.exit(0 if time.time() - last <= MAX_AGE else 1)
