import duckdb
from fastapi.testclient import TestClient

from app.db import connect, data_root
from app.main import app
from app.model import Completion, get_model
from app.sandbox import execute_readonly
from app.warehouse import warehouse_file
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'",
                1,
                1,
            )
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_program_appends_department_before_execute(tmp_path):
    database = tmp_path / "warehouse.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute(
        "CREATE TABLE ods_orders (department VARCHAR, pay_amount INTEGER, status VARCHAR)"
    )
    connection.execute(
        "INSERT INTO ods_orders VALUES ('east', 10, 'paid'), ('west', 99, 'paid')"
    )
    connection.close()
    result = execute_readonly(
        database,
        "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'",
        scope="east",
    )
    assert "department" not in "SELECT SUM(pay_amount) AS gmv FROM ods_orders"
    assert "department = 'east'" in result["sql"]
    assert result["rows"] == [[10]]


def test_analysis_cannot_widen_scope():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "scope-user")
    with connect() as connection:
        connection.execute(
            "UPDATE users SET data_scope = ? WHERE username = ?",
            ("east", "scope-user"),
        )
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "范围", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    me = client.get("/me", headers=headers).json()
    database = warehouse_file(data_root() / f"tenant_{me['id']}" / str(created["id"]))
    connection = duckdb.connect(str(database))
    connection.execute(
        """
        CREATE OR REPLACE TABLE ods_orders AS
        SELECT order_id, user_id, pay_time, status, pay_amount, 'east' AS department
        FROM ods_orders WHERE order_id = 1
        UNION ALL
        SELECT order_id, user_id, pay_time, status, pay_amount, 'west' AS department
        FROM ods_orders WHERE order_id = 2
        """
    )
    connection.close()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘"},
    ).json()
    assert "department" not in body["sql"]
    assert "department = 'east'" in body["executed_sql"]
    assert body["table"]["rows"] == [[12]]
    app.dependency_overrides.clear()
