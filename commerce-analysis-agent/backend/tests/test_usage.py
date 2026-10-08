from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders", 10, 4)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对。", 2, 2)


def test_usage_adds_up_and_names_the_failed_step(monkeypatch):
    monkeypatch.setenv("MODEL_INPUT_PRICE", "2")
    monkeypatch.setenv("MODEL_OUTPUT_PRICE", "3")
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "cost-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "费用", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    first = client.post(
        "/analyses", headers=headers, json={"dataset_id": created["id"], "direction": "看大盘"}
    ).json()
    second = client.post(
        "/analyses", headers=headers, json={"dataset_id": created["id"], "direction": "看趋势"}
    ).json()
    failed = client.post(
        "/analyses", headers=headers, json={"dataset_id": created["id"], "direction": "看结构"}
    ).json()
    summary = client.get("/me/usage", headers=headers).json()
    opened = client.get(f"/me/usage/{first['log_id']}", headers=headers).json()
    one_cost = 12 * 2 + 6 * 3
    assert first["cost"] == one_cost
    assert second["cost"] == one_cost
    assert summary["cost"] == one_cost * 2
    assert summary["input_tokens"] == 24
    assert summary["request_count"] == 4
    assert failed["failure_step"] == "读数"
    assert opened["input_price"] == 2
    assert opened["output_price"] == 3
    assert opened["steps"][0]["name"] == "数据来源"
    app.dependency_overrides.clear()
