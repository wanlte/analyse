from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_category_and_custom_metric():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "metric-user")
    rejected = client.post(
        "/me/metrics",
        headers=headers,
        json={"name": "坏指标", "field_name": "pay_amount)+1", "agg": "sum"},
    )
    assert rejected.status_code == 400
    created_metric = client.post(
        "/me/metrics",
        headers=headers,
        json={"name": "实付合计", "field_name": "pay_amount", "agg": "sum"},
    )
    assert created_metric.status_code == 200
    chosen = client.put("/me/config", headers=headers, json={"category": "交易"})
    assert chosen.status_code == 200
    orders = "order_id,user_id,pay_time,status,pay_amount\n1,7,2026-10-01,paid,30\n2,7,2026-10-02,paid,50\n"
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "指标", "resource_pack": "EC_V1.0"},
        files=pack_files(orders),
    )
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created.json()["id"], "direction": "看大盘", "question": "实付合计是多少"},
    ).json()
    metric_step = next(step["detail"] for step in body["steps"] if step["name"] == "口径")
    calculate = next(step["detail"] for step in body["steps"] if step["name"] == "计算")
    assert "GMV" in metric_step
    assert "实付合计 为 80" in calculate
    missing = client.post(
        "/me/metrics",
        headers=headers,
        json={"name": "缺列指标", "field_name": "not_there", "agg": "sum"},
    )
    assert missing.status_code == 200
    failed = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created.json()["id"], "question": "缺列指标"},
    ).json()
    assert failed["failure_step"] == "读数"
    assert "缺少列 not_there" in failed["error"]
    app.dependency_overrides.clear()
