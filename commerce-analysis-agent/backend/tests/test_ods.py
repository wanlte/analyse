from fastapi.testclient import TestClient

from app.db import data_root
from app.main import app
from app.sandbox import execute_readonly
from app.warehouse import warehouse_file
from tests.helpers import auth_header, pack_files

client = TestClient(app)


def test_saved_csv_can_be_counted_in_duckdb():
    headers = auth_header(client, "ods-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "可查询", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    me = client.get("/me", headers=headers).json()
    database = warehouse_file(data_root() / f"tenant_{me['id']}" / str(created["id"]))
    result = execute_readonly(database, "SELECT COUNT(*) AS total FROM ods_orders")
    assert result["rows"] == [[2]]
    assert created["row_count"] == 2 + 1 + 1 + 1 + 1
