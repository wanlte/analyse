import json
import os
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "semantic" / "queries.json"


def load_queries() -> dict:
    path = Path(os.environ.get("QUERIES_PATH", DEFAULT))
    return json.loads(path.read_text(encoding="utf-8"))
