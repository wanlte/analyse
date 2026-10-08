import csv
from pathlib import Path


def read_table(path: Path, limit: int = 5) -> tuple[list[str], int, list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        rows = []
        count = 0
        for record in reader:
            count += 1
            if len(rows) < limit:
                rows.append(record)
    return list(columns), count, rows


def missing_columns(columns: list[str], required: list[str]) -> list[str]:
    present = set(columns)
    return [name for name in required if name not in present]
