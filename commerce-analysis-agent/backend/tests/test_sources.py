import sqlite3

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header

client = TestClient(app)


def _sqlite_bytes(path) -> bytes:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE orders (order_id INTEGER, user_id INTEGER, pay_time TEXT, status TEXT, pay_amount INTEGER)"
    )
    connection.execute(
        "INSERT INTO orders VALUES (1, 7, '2026-10-01', 'paid', 12), (2, 7, '2026-10-02', 'paid', 8)"
    )
    connection.execute(
        "CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price INTEGER)"
    )
    connection.execute("INSERT INTO order_items VALUES (1, 3, 1, 12)")
    connection.execute("CREATE TABLE users (user_id INTEGER)")
    connection.execute("INSERT INTO users VALUES (7)")
    connection.execute("CREATE TABLE products (product_id INTEGER)")
    connection.execute("INSERT INTO products VALUES (3)")
    connection.execute("CREATE TABLE behaviors (user_id INTEGER, behavior_type TEXT)")
    connection.execute("INSERT INTO behaviors VALUES (7, 'pv')")
    connection.commit()
    connection.close()
    return path.read_bytes()


def test_sqlite_loads_and_mysql_is_closed(tmp_path):
    headers = auth_header(client, "source-user")
    before = client.get("/datasets", headers=headers).json()
    rejected = client.post(
        "/datasets",
        headers=headers,
        data={"name": "mysql", "resource_pack": "EC_V1.0", "source_type": "mysql"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "本版未接入"
    assert client.get("/datasets", headers=headers).json() == before
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "sqlite订单", "resource_pack": "EC_V1.0", "source_type": "sqlite"},
        files={"file": ("shop.sqlite", _sqlite_bytes(tmp_path / "shop.sqlite"), "application/octet-stream")},
    )
    assert created.status_code == 200
    profile = client.get(f"/datasets/{created.json()['id']}/profile", headers=headers).json()
    orders = next(table for table in profile["tables"] if table["table"] == "ods_orders")
    assert orders["row_count"] == 2
