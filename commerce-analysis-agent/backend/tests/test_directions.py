from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)

GROUPED = (
    "SELECT channel, SUM(pay_amount) AS gmv FROM ods_orders "
    "WHERE status = 'paid' GROUP BY channel"
)
CHANNEL_ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount,channel\n"
    "1,7,2026-10-01,paid,100,自营\n"
    "2,7,2026-10-02,paid,10,直播\n"
    "3,7,2026-10-03,paid,10,第三方\n"
)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql" and ("看结构" in prompt or "找异常" in prompt):
            return Completion(GROUPED, 1, 1)
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'",
                1,
                1,
            )
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def _prepare(username: str, orders: str | None = None):
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, username)
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": username, "resource_pack": "EC_V1.0"},
        files=pack_files(orders),
    ).json()
    return headers, created["id"]


def test_four_directions_succeed_or_name_the_missing_column():
    headers, dataset_id = _prepare("directions")
    for direction in ("看大盘", "看趋势"):
        body = client.post(
            "/analyses",
            headers=headers,
            json={"dataset_id": dataset_id, "direction": direction},
        )
        assert body.status_code == 200
        assert body.json()["status"] == "成功"
    for direction in ("看结构", "找异常"):
        body = client.post(
            "/analyses",
            headers=headers,
            json={"dataset_id": dataset_id, "direction": direction},
        )
        assert body.status_code == 200
        payload = body.json()
        assert payload["status"] == "失败"
        assert payload["error"] == "缺少列 channel"
        assert "未开放" not in str(payload)
    headers, dataset_id = _prepare("directions-channel", CHANNEL_ORDERS)
    structure = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": dataset_id, "direction": "看结构"},
    ).json()
    anomaly = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": dataset_id, "direction": "找异常"},
    ).json()
    assert structure["status"] == "成功"
    assert "结构：" in _step(structure, "计算")
    assert anomaly["status"] == "成功"
    assert "异常：自营" in _step(anomaly, "计算")
    app.dependency_overrides.clear()


def _step(body: dict, name: str) -> str:
    return next(step["detail"] for step in body["steps"] if step["name"] == name)
