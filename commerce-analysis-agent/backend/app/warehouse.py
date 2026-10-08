from pathlib import Path

import duckdb

from app.db import ROOT
from app.packs import SLOTS

MODELS = ROOT / "warehouse" / "ecommerce"
LAYER_SQL = [
    MODELS / "dwd" / "dwd_order_detail.sql",
    MODELS / "dws" / "dws_user_daily.sql",
    MODELS / "dws" / "dws_product_daily.sql",
    MODELS / "ads" / "ads_trade_daily.sql",
]


def warehouse_file(dataset_dir: Path) -> Path:
    return dataset_dir / "warehouse.duckdb"


def load_csvs(dataset_dir: Path, slots: list[str]) -> None:
    target = warehouse_file(dataset_dir)
    if target.exists():
        target.unlink()
    connection = duckdb.connect(str(target))
    try:
        for slot in slots:
            source = dataset_dir / f"{slot}.csv"
            table = f"ods_{slot}"
            connection.execute(
                f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=true)",
                [str(source)],
            )
    finally:
        connection.close()
    rebuild(target)


def rebuild(database: Path) -> dict:
    connection = duckdb.connect(str(database))
    try:
        _staging(connection)
        for path in LAYER_SQL:
            connection.execute(path.read_text(encoding="utf-8"))
        violations = connection.execute(
            (MODELS / "tests" / "paid_amount_present.sql").read_text(encoding="utf-8")
        ).fetchone()[0]
        if violations:
            connection.execute("DROP TABLE IF EXISTS ads_trade_daily_next")
            return {"published": False, "violations": int(violations)}
        connection.execute("DROP TABLE IF EXISTS ads_trade_daily")
        connection.execute("ALTER TABLE ads_trade_daily_next RENAME TO ads_trade_daily")
        return {"published": True, "violations": 0}
    finally:
        connection.close()


def _staging(connection) -> None:
    connection.execute(
        f"""
        CREATE OR REPLACE VIEW stg_order_line AS
        SELECT
            o.order_id,
            o.user_id,
            i.product_id,
            CAST(o.pay_time AS VARCHAR) AS pay_time,
            substr(CAST(o.pay_time AS VARCHAR), 1, 10) AS pay_date,
            o.status,
            o.pay_amount,
            i.quantity,
            i.unit_price,
            {_expr(connection, "ods_orders", "channel", "'未知'")} AS channel,
            {_expr(connection, "ods_products", "category", "'未知'", "p")} AS category,
            {_expr(connection, "ods_orders", "city", _expr(connection, "ods_users", "city", "'未知'", "u"))} AS city,
            {_expr(connection, "ods_orders", "is_test", "0")} AS is_test
        FROM ods_orders o
        JOIN ods_order_items i ON o.order_id = i.order_id
        LEFT JOIN ods_products p ON i.product_id = p.product_id
        LEFT JOIN ods_users u ON o.user_id = u.user_id
        """
    )


def _expr(connection, table: str, column: str, fallback: str, alias: str = "o") -> str:
    names = [row[0] for row in connection.execute(f"DESCRIBE {table}").fetchall()]
    if column not in names:
        return fallback
    return f"COALESCE(CAST({alias}.{column} AS VARCHAR), {fallback})" if fallback != "0" else f"COALESCE({alias}.{column}, 0)"


def allowed_tables() -> set[str]:
    return {f"ods_{slot}" for slot in SLOTS} | {"uploaded"}


def table_columns(database: Path, table: str) -> list[str]:
    if not Path(database).exists():
        return []
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(f"DESCRIBE {table}").fetchall()
    except duckdb.Error:
        return []
    finally:
        connection.close()
    return [row[0] for row in rows]


def summarize_cards(database: Path, date_from: str = "", date_to: str = "") -> dict:
    names = ("GMV", "订单量", "转化率", "退款率")
    blank = {
        "data_date": "",
        "cards": [{"name": name, "value": None, "change": None} for name in names],
    }
    if not database.exists():
        return blank
    connection = duckdb.connect(str(database), read_only=True)
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        if "ads_trade_daily" not in tables:
            return blank
        clauses = []
        params = []
        if date_from:
            clauses.append("pay_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("pay_date <= ?")
            params.append(date_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        months = connection.execute(
            f"""
            SELECT substr(pay_date, 1, 7) AS month,
                   SUM(gmv) AS gmv,
                   SUM(orders) AS orders,
                   MAX(pay_date) AS data_date
            FROM ads_trade_daily
            {where}
            GROUP BY 1
            ORDER BY 1
            """,
            params,
        ).fetchall()
        if not months:
            return blank
        current = months[-1]
        previous = months[-2] if len(months) > 1 else None

        def change(now, before):
            if before is None or float(before) == 0:
                return None
            return float(now - before) / float(before)

        values = {
            "GMV": (float(current[1] or 0), change(current[1] or 0, None if previous is None else previous[1])),
            "订单量": (float(current[2] or 0), change(current[2] or 0, None if previous is None else previous[2])),
            "转化率": _rate(connection, tables, current[0], "conversion"),
            "退款率": _rate(connection, tables, current[0], "refund"),
        }
        return {
            "data_date": current[3] or "",
            "cards": [
                {"name": name, "value": values[name][0], "change": values[name][1]}
                for name in names
            ],
        }
    finally:
        connection.close()


def _rate(connection, tables: set[str], month: str, kind: str):
    if kind == "refund":
        if "ods_orders" not in tables or "refund_amount" not in _open_columns(connection, "ods_orders"):
            return None, None
        refund, paid = connection.execute(
            """
            SELECT COALESCE(SUM(refund_amount), 0), COALESCE(SUM(pay_amount), 0)
            FROM ods_orders
            WHERE status = 'paid' AND substr(CAST(pay_time AS VARCHAR), 1, 7) = ?
            """,
            [month],
        ).fetchone()
        if not paid:
            return 0.0, None
        return float(refund) / float(paid), None
    if "ods_orders" not in tables or "ods_behaviors" not in tables:
        return None, None
    buyers = connection.execute(
        """
        SELECT COUNT(DISTINCT user_id) FROM ods_orders
        WHERE status = 'paid' AND substr(CAST(pay_time AS VARCHAR), 1, 7) = ?
        """,
        [month],
    ).fetchone()[0]
    visitors = connection.execute(
        "SELECT COUNT(DISTINCT user_id) FROM ods_behaviors"
    ).fetchone()[0]
    if not visitors:
        return None, None
    return float(buyers) / float(visitors), None


def _open_columns(connection, table: str) -> set[str]:
    try:
        return {row[0] for row in connection.execute(f"DESCRIBE {table}").fetchall()}
    except duckdb.Error:
        return set()


def profile_database(database: Path) -> list[dict]:
    if not database.exists():
        return []
    connection = duckdb.connect(str(database), read_only=True)
    try:
        tables = [row[0] for row in connection.execute("SHOW TABLES").fetchall()]
        report = []
        for table in tables:
            columns = [row[0] for row in connection.execute(f"DESCRIBE {table}").fetchall()]
            row_count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            nulls = {}
            for column in columns:
                nulls[column] = connection.execute(
                    f'SELECT COUNT(*) FROM {table} WHERE "{column}" IS NULL'
                ).fetchone()[0]
            report.append(
                {
                    "table": table,
                    "row_count": int(row_count),
                    "columns": columns,
                    "nulls": nulls,
                }
            )
        return report
    finally:
        connection.close()
