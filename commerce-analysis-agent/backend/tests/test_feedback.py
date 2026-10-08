from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'",
                1,
                1,
            )
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_last_feedback_replaces_the_previous_vote():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "feedback-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "反馈", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    log_id = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘"},
    ).json()["log_id"]
    first = client.post(
        f"/analyses/{log_id}/feedback",
        headers=headers,
        json={"vote": "赞", "note": "清楚"},
    )
    second = client.post(
        f"/analyses/{log_id}/feedback",
        headers=headers,
        json={"vote": "踩", "note": "口径不对"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["vote"] == "踩"
    assert second.json()["count"] == 1
    app.dependency_overrides.clear()
