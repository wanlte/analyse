import duckdb

from app.sandbox import execute_readonly
from app.warehouse import rebuild


def _database(path, extra_order: str = ""):
    connection = duckdb.connect(str(path))
    connection.execute(
        """
        CREATE TABLE ods_orders (
            order_id INTEGER, user_id INTEGER, pay_time VARCHAR, status VARCHAR,
            pay_amount INTEGER, channel VARCHAR, city VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO ods_orders VALUES
            (1, 7, '2026-10-01', 'paid', 12, '自营', '杭州'),
            (2, 7, '2026-10-01', 'paid', 8, '自营', '杭州'),
            (3, 8, '2026-10-02', 'paid', 5, '直播', '上海')
        """
    )
    connection.execute(
        """
        CREATE TABLE ods_order_items (
            order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price INTEGER
        )
        """
    )
    connection.execute(
        """
        INSERT INTO ods_order_items VALUES
            (1, 3, 1, 12),
            (2, 3, 1, 8),
            (3, 4, 2, 5)
        """
    )
    connection.execute("CREATE TABLE ods_users (user_id INTEGER, city VARCHAR)")
    connection.execute("INSERT INTO ods_users VALUES (7, '杭州'), (8, '上海')")
    connection.execute("CREATE TABLE ods_products (product_id INTEGER, category VARCHAR)")
    connection.execute("INSERT INTO ods_products VALUES (3, '服装'), (4, '食品')")
    if extra_order:
        connection.execute(extra_order)
    connection.close()


def test_ads_grain_matches_two_rebuilds(tmp_path):
    database = tmp_path / "warehouse.duckdb"
    _database(database)
    assert rebuild(database)["published"] is True
    assert rebuild(database)["published"] is True
    detail = execute_readonly(
        database,
        """
        SELECT DISTINCT pay_date, channel, category, city
        FROM dwd_order_detail
        WHERE status = 'paid'
        """,
    )
    ads = execute_readonly(
        database,
        "SELECT pay_date, channel, category, city FROM ads_trade_daily",
    )
    assert {tuple(row) for row in ads["rows"]} == {tuple(row) for row in detail["rows"]}
    assert len(ads["rows"]) == 2


def test_failed_quality_keeps_published_ads(tmp_path):
    database = tmp_path / "warehouse.duckdb"
    _database(database)
    rebuild(database)
    before = execute_readonly(database, "SELECT COUNT(*) FROM ads_trade_daily")
    connection = duckdb.connect(str(database))
    connection.execute(
        "INSERT INTO ods_orders VALUES (9, 7, '2026-10-03', 'paid', NULL, '自营', '杭州')"
    )
    connection.execute("INSERT INTO ods_order_items VALUES (9, 3, 1, 1)")
    connection.close()
    outcome = rebuild(database)
    after = execute_readonly(database, "SELECT COUNT(*) FROM ads_trade_daily")
    assert outcome["published"] is False
    assert outcome["violations"] == 1
    assert after["rows"] == before["rows"]
