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
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_channel_filter_keeps_only_the_selected_channel():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "dim-user")
    orders = (
        "order_id,user_id,pay_time,status,pay_amount,channel\n"
        "1,7,2026-10-01,paid,100,自营\n"
        "2,8,2026-10-02,paid,50,直播\n"
    )
    files = pack_files(orders)
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "渠道", "resource_pack": "EC_V1.0"},
        files=files,
    )
    assert created.status_code == 200
    dataset_id = created.json()["id"]
    listed = client.get(f"/datasets/{dataset_id}/dimensions", headers=headers).json()
    assert listed["channel"] == ["直播", "自营"]
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": dataset_id, "direction": "看大盘", "channel": "自营"},
    ).json()
    calculate = next(step["detail"] for step in body["steps"] if step["name"] == "计算")
    assert "自营" in calculate
    assert "直播" not in calculate
    app.dependency_overrides.clear()
