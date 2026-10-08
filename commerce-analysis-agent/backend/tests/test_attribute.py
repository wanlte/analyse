from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)

ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount,channel\n"
    "1,7,2026-09-15,paid,100,自营\n"
    "2,7,2026-10-01,paid,200,自营\n"
    "3,7,2026-10-02,paid,100,直播\n"
    "4,7,2025-10-03,paid,100,自营\n"
)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'",
                1,
                1,
            )
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_period_and_channel_match_hand_calculation():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "attribute")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "归因", "resource_pack": "EC_V1.0"},
        files=pack_files(ORDERS),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘"},
    ).json()
    detail = next(step["detail"] for step in body["steps"] if step["name"] == "计算")
    assert body["request_count"] == 2
    assert "环比：2026-10 相对 2026-09 200%" in detail
    assert "同比" not in detail
    assert "维度贡献：自营 占 80%（400/500）" in detail
    yoy = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘", "compare": "同比"},
    ).json()
    yoy_detail = next(step["detail"] for step in yoy["steps"] if step["name"] == "计算")
    assert "同比：相对 2025-10 200%" in yoy_detail
    app.dependency_overrides.clear()
