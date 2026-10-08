from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, PlatformModel, get_model, model_for_user
from app.db import connect
from tests.helpers import auth_header, pack_files

client = TestClient(app)
SECRET = "user-secret-key"


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders", 1, 1)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对。", 1, 1)


def test_key_stays_on_the_server_and_group_enters_the_metric_step():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "config-user")
    bound = client.put("/me/key", headers=headers, json={"api_key": SECRET})
    assert bound.status_code == 200
    assert bound.json()["key_status"] == "已绑定"
    me = client.get("/me", headers=headers).text
    config = client.get("/me/config", headers=headers).text
    assert SECRET not in me
    assert SECRET not in config
    with connect() as connection:
        cipher = connection.execute(
            """
            SELECT key_cipher FROM user_config
            WHERE user_id = (SELECT id FROM users WHERE username = ?)
            """,
            ("config-user",),
        ).fetchone()[0]
    model = model_for_user(cipher, PlatformModel("platform-key", "http://example", "gpt"))
    assert model.api_key == SECRET
    blocked = client.put("/me/config", headers=headers, json={"resource_pack": "FN"})
    assert blocked.status_code == 400
    created_group = client.post(
        "/me/groups",
        headers=headers,
        json={"name": "健康度", "metrics": ["转化率", "复购率"]},
    )
    assert created_group.status_code == 200
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "配置", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "question": "健康度怎么样"},
    ).json()
    detail = next(step["detail"] for step in body["steps"] if step["name"] == "口径")
    assert "转化率" in detail
    assert "复购率" in detail
    assert body["steps"][0]["name"] == "数据来源"
    app.dependency_overrides.clear()
