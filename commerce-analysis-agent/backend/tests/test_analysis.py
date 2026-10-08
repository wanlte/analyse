from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from app.sandbox import execute_readonly
from app.db import data_root
from app.warehouse import warehouse_file
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if "删掉" in prompt:
            return Completion("DELETE FROM ods_orders", 2, 2)
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv, COUNT(*) AS orders FROM ods_orders WHERE status = 'paid'",
                10,
                8,
            )
        return Completion("结论：GMV 来自查询结果。数据支撑：见读数。建议：继续看趋势。", 4, 6)


def setup():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "analyst")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "电商订单_1008", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    return headers, created


def test_dashboard_records_tokens_and_source():
    headers, created = setup()
    response = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "成功"
    assert "SELECT" in body["sql"]
    assert body["request_count"] == 2
    assert body["input_tokens"] == 14
    assert body["output_tokens"] == 14
    assert body["steps"][0]["name"] == "数据来源"
    assert "电商订单_1008" in body["steps"][0]["detail"]
    assert "EC_V1.0" in body["steps"][0]["detail"]


def test_write_sql_does_not_change_rows():
    headers, created = setup()
    me = client.get("/me", headers=headers).json()
    database = warehouse_file(data_root() / f"tenant_{me['id']}" / str(created["id"]))
    before = execute_readonly(database, "SELECT COUNT(*) FROM ods_orders")
    rejected = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "question": "删掉订单"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "失败"
    after = execute_readonly(database, "SELECT COUNT(*) FROM ods_orders")
    assert before["rows"] == after["rows"]
    app.dependency_overrides.clear()
