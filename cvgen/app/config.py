"""Configuration — paths read from env vars, sensible defaults for local dev."""
import os
from pathlib import Path

VERSION = "0.1.0"

DATA_DIR = Path(os.environ.get("CVGEN_DATA_DIR", "/app/data"))
CONFIG_DIR = Path(os.environ.get("CVGEN_CONFIG_DIR", "/app/config"))
TEMPLATES_DIR = Path(os.environ.get("CVGEN_TEMPLATES_DIR", "/app/templates"))

DB_PATH = DATA_DIR / "personnel.db"
OUTPUT_DIR = DATA_DIR / "output"


def ensure_dirs():
    """Create required directories if missing."""
    for d in (DATA_DIR, CONFIG_DIR, TEMPLATES_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)
