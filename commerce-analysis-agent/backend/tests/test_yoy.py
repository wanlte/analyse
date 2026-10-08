import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.attribute import keep_compare, period_change
from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_year_alignment_for_week_and_quarter():
    weekly = period_change([("2025-W01", 10), ("2026-W01", 20)])
    quarterly = period_change([("2025-Q2", 10), ("2026-Q2", 30)])
    assert "同比：相对 2025-W01" in weekly
    assert "同比：相对 2025-Q2" in quarterly
    assert "同比" not in keep_compare(weekly, "环比")


def test_compare_switch_keeps_one_sentence():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "yoy-user")
    orders = (
        "order_id,user_id,pay_time,status,pay_amount\n"
        "1,7,2025-10-02,paid,50\n"
        "2,7,2026-10-02,paid,80\n"
    )
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "同比", "resource_pack": "EC_V1.0"},
        files=pack_files(orders),
    )
    dataset_id = created.json()["id"]

    def calculate(compare):
        body = client.post(
            "/analyses",
            headers=headers,
            json={"dataset_id": dataset_id, "direction": "看大盘", "compare": compare},
        ).json()
        return next(step["detail"] for step in body["steps"] if step["name"] == "计算")

    year = calculate("同比")
    ring = calculate("环比")
    assert "相对 2025-10" in year
    assert "同比" not in ring
    app.dependency_overrides.clear()
