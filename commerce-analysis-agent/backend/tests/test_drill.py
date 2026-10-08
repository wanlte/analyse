from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion(
                "SELECT channel, SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid' GROUP BY 1",
                1,
                1,
            )
        return Completion("结论：下钻后的回答。数据支撑：见结果。建议：看自营。", 1, 1)


def test_drill_request_for_self_operated_keeps_only_that_channel():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "drill-user")
    orders = (
        "order_id,user_id,pay_time,status,pay_amount,channel\n"
        "1,7,2026-10-01,paid,100,自营\n"
        "2,8,2026-10-02,paid,50,直播\n"
    )
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "下钻", "resource_pack": "EC_V1.0"},
        files=pack_files(orders),
    )
    body = client.post(
        "/analyses",
        headers=headers,
        json={
            "dataset_id": created.json()["id"],
            "direction": "看结构",
            "question": "下钻 自营",
            "channel": "自营",
        },
    ).json()
    calculate = next(step["detail"] for step in body["steps"] if step["name"] == "计算")
    assert "自营" in calculate
    assert "直播" not in calculate
    app.dependency_overrides.clear()
