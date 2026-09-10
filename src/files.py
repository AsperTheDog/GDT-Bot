from functools import cache
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR / "data_files"
QUERIES_DIR = DATA_DIR / "queries"
OTHER_DIR = DATA_DIR / "other"
CONFIG_PATH = DATA_DIR / "config.json"
EXAMPLE_CONFIG_PATH = DATA_DIR / "config.json.example"
DATABASE_PATH = DATA_DIR / "database.sqlite"


@cache
def query(name: str) -> str:
    return (QUERIES_DIR / name).read_text(encoding="utf-8")
