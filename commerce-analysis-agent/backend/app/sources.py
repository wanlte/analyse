import csv
import sqlite3
from pathlib import Path

from app.packs import SLOTS

CLOSED_SOURCES = {"mysql", "hive", "postgresql"}


class SourceError(Exception):
    pass


def assert_supported(source_type: str) -> str:
    kind = source_type or "csv"
    if kind in CLOSED_SOURCES or kind not in {"csv", "sqlite"}:
        raise SourceError("本版未接入")
    return kind


def export_sqlite(sqlite_path: Path, folder: Path) -> None:
    connection = sqlite3.connect(sqlite_path)
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for slot in SLOTS:
            if slot not in names:
                raise SourceError(f"缺少表 {slot}")
            cursor = connection.execute(f"SELECT * FROM {slot}")
            headers = [item[0] for item in cursor.description]
            with (folder / f"{slot}.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(cursor.fetchall())
    finally:
        connection.close()
