import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

import duckdb

from app.warehouse import table_columns

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma|replace)\b",
    re.IGNORECASE,
)


class SandboxError(Exception):
    pass


def _guard(sql: str) -> str:
    text = sql.strip().rstrip(";")
    if not text or ";" in text:
        raise SandboxError("只允许一条查询")
    if FORBIDDEN.search(text):
        raise SandboxError("只允许读取数据")
    if not text.lower().startswith("select") and not text.lower().startswith("with"):
        raise SandboxError("只允许读取数据")
    return text


def _with_scope(
    database: Path,
    statement: str,
    scope: str = "",
    date_from: str = "",
    date_to: str = "",
    channel: str = "",
    category: str = "",
    city: str = "",
) -> str:
    columns = table_columns(database, "ods_orders")
    predicates = []
    if scope and "department" in columns:
        predicates.append(f"department = '{scope.replace(chr(39), chr(39) * 2)}'")
    if (date_from or date_to) and "pay_time" in columns:
        if date_from and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_from):
            raise SandboxError("日期格式不正确")
        if date_to and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_to):
            raise SandboxError("日期格式不正确")
        if date_from:
            predicates.append(f"substr(CAST(pay_time AS VARCHAR), 1, 10) >= '{date_from}'")
        if date_to:
            predicates.append(f"substr(CAST(pay_time AS VARCHAR), 1, 10) <= '{date_to}'")
    for name, value in (("channel", channel), ("category", category), ("city", city)):
        if not value or value == "全部" or name not in columns:
            continue
        if not re.fullmatch(r"[0-9A-Za-z_\-\u4e00-\u9fff]+", value):
            raise SandboxError("维度取值无法识别")
        predicates.append(f"{name} = '{value}'")
    if not predicates:
        return statement
    scoped = (
        "FROM (SELECT * FROM ods_orders WHERE "
        + " AND ".join(predicates)
        + ") AS ods_orders"
    )
    return re.sub(r"\bfrom\s+ods_orders\b", scoped, statement, flags=re.IGNORECASE)


def execute_readonly(
    database: Path,
    sql: str,
    limit: int = 100,
    timeout: float = 5,
    scope: str = "",
    date_from: str = "",
    date_to: str = "",
    channel: str = "",
    category: str = "",
    city: str = "",
) -> dict:
    statement = _with_scope(
        database, _guard(sql), scope, date_from, date_to, channel, category, city
    )
    bounded = f"SELECT * FROM ({statement}) AS query_result LIMIT {int(limit)}"

    def run():
        connection = duckdb.connect(str(database), read_only=True)
        try:
            cursor = connection.execute(bounded)
            columns = [item[0] for item in cursor.description]
            rows = cursor.fetchall()
            return columns, rows
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run)
        try:
            columns, rows = future.result(timeout=timeout)
        except FuturesTimeout as error:
            raise SandboxError("查询超时") from error
        except duckdb.Error as error:
            raise SandboxError(str(error)) from error
    return {
        "columns": columns,
        "rows": [list(row) for row in rows],
        "truncated": len(rows) >= limit,
        "sql": statement,
    }
