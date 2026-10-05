"""Central configuration, read from environment (.env) with sensible defaults."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

WAREHOUSE_PATH = Path(os.getenv("WAREHOUSE_PATH", ROOT / "warehouse" / "retail.duckdb"))
if not WAREHOUSE_PATH.is_absolute():
    WAREHOUSE_PATH = ROOT / WAREHOUSE_PATH
SCHEMA = os.getenv("WAREHOUSE_SCHEMA", "dev")
HORIZON = int(os.getenv("HORIZON", 28))
N_FOLDS = int(os.getenv("N_FOLDS", 13))
SAMPLE_DIR = ROOT / "data" / "sample"
RAW_DIR = ROOT / "data" / "raw"
EXPORT_DIR = ROOT / "reports" / "exports"
IMAGE_DIR = ROOT / "images"


def connect(read_only: bool = False):
    import duckdb

    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=read_only)
