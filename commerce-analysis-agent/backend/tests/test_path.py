from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：GMV 来自查询。数据支撑：见读数。建议：核对口径。", 1, 1)


def test_register_login_save_and_read_dashboard():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    registered = client.post(
        "/auth/register", json={"username": "path-user", "password": "secret"}
    )
    assert registered.status_code == 200
    logged_in = client.post(
        "/auth/login", json={"username": "path-user", "password": "secret"}
    )
    headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "走通", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘", "question": "本月 GMV 是多少"},
    ).json()
    names = [step["name"] for step in body["steps"]]
    assert "数据来源" in names
    assert "口径" in names
    assert "结论" in names
    assert "结论" in body["answer"]
    app.dependency_overrides.clear()
