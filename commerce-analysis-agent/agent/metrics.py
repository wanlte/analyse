import json
import os
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "semantic" / "metrics.json"


def load_metrics() -> list[dict]:
    path = Path(os.environ.get("METRICS_PATH", DEFAULT))
    return json.loads(path.read_text(encoding="utf-8"))


def gmv_metric() -> dict:
    for item in load_metrics():
        if item["name"] == "GMV":
            return item
    raise KeyError("GMV")


def metric_detail() -> str:
    item = gmv_metric()
    return f"GMV {item['version']} · {item['definition']}"


def lines_for(names: list[str]) -> str:
    wanted = set(names)
    parts = []
    for item in load_metrics():
        if item["name"] in wanted:
            parts.append(f"{item['name']} {item['version']} · {item['definition']}")
    return " ".join(parts)


def category_line(name: str) -> str:
    if not name:
        return ""
    tree = json.loads((DEFAULT.parent / "categories.json").read_text(encoding="utf-8"))
    for children in tree.values():
        if name in children:
            return lines_for(children[name])
    return ""
