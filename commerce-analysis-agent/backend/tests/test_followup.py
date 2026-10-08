from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)

CHANNEL_ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount,channel\n"
    "1,7,2026-10-01,paid,80,自营\n"
    "2,7,2026-10-02,paid,20,直播\n"
)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对。", 1, 1)


def test_channel_followup_and_missing_product():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "follow-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "渠道", "resource_pack": "EC_V1.0"},
        files=pack_files(CHANNEL_ORDERS),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "question": "哪个渠道贡献最大"},
    ).json()
    detail = next(step["detail"] for step in body["steps"] if step["name"] == "计算")
    assert "维度贡献" in detail
    plain = client.post(
        "/datasets",
        headers=headers,
        data={"name": "无单品", "resource_pack": ""},
        files={"file": ("data.csv", "user_id,amount\n1,2\n", "text/csv")},
    ).json()
    missing = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": plain["id"], "question": "下钻到单品"},
    ).json()
    assert missing["failure_step"] == "读数"
    assert missing["error"] == "缺少列 product_id"
    app.dependency_overrides.clear()
