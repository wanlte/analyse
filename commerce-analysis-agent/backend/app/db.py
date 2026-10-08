import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def db_path() -> Path:
    configured = os.environ.get("APP_DB")
    if configured:
        return Path(configured)
    return ROOT / "data" / "app.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def data_root() -> Path:
    configured = os.environ.get("DATA_ROOT")
    if configured:
        return Path(configured)
    return ROOT / "data"


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nickname TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                avatar_url TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT '普通用户',
                status TEXT NOT NULL DEFAULT '启用',
                data_scope TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                resource_pack TEXT,
                row_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS qa_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dataset_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                sql TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                error TEXT NOT NULL DEFAULT '',
                request_count INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        _add_column(connection, "users", "data_scope", "TEXT NOT NULL DEFAULT ''")
        _add_column(connection, "qa_log", "elapsed_ms", "INTEGER NOT NULL DEFAULT 0")
        _add_column(connection, "qa_log", "input_price", "REAL NOT NULL DEFAULT 0")
        _add_column(connection, "qa_log", "output_price", "REAL NOT NULL DEFAULT 0")
        _add_column(connection, "qa_log", "cost", "REAL NOT NULL DEFAULT 0")
        _add_column(connection, "qa_log", "failure_step", "TEXT NOT NULL DEFAULT ''")
        _add_column(connection, "qa_log", "steps_json", "TEXT NOT NULL DEFAULT '[]'")
        _add_column(connection, "qa_log", "answer", "TEXT NOT NULL DEFAULT ''")
        _add_column(connection, "qa_log", "table_json", "TEXT NOT NULL DEFAULT ''")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                log_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                vote TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                answer TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                metric_version TEXT NOT NULL,
                data_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_config (
                user_id INTEGER PRIMARY KEY,
                resource_pack TEXT NOT NULL DEFAULT 'EC_V1.0',
                output_preference TEXT NOT NULL DEFAULT '汇总结论',
                default_range TEXT NOT NULL DEFAULT '本月',
                key_status TEXT NOT NULL DEFAULT '平台密钥',
                key_cipher TEXT NOT NULL DEFAULT ''
            )
            """
        )
        _add_column(connection, "user_config", "date_from", "TEXT NOT NULL DEFAULT ''")
        _add_column(connection, "user_config", "date_to", "TEXT NOT NULL DEFAULT ''")
        _add_column(connection, "user_config", "category", "TEXT NOT NULL DEFAULT ''")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_metric (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                field_name TEXT NOT NULL,
                agg TEXT NOT NULL,
                UNIQUE (user_id, name)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_group (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_group_item (
                group_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (group_id, metric_name)
            )
            """
        )


def _add_column(connection, table: str, column: str, definition: str) -> None:
    names = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
    if column not in names:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
