from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：当时的回答。数据支撑：见读数。建议：留档。", 1, 1)


def test_saved_analysis_can_be_opened_again():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "session-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "会话", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    )
    before = client.get("/analyses", headers=headers).json()
    saved = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created.json()["id"], "direction": "看大盘", "question": "本月 GMV 是多少"},
    ).json()
    listed = client.get("/analyses", headers=headers).json()
    assert len(listed) == len(before) + 1
    opened = client.get(f"/analyses/{saved['log_id']}", headers=headers).json()
    assert opened["answer"] == saved["answer"]
    assert opened["answer"] == "结论：当时的回答。数据支撑：见读数。建议：留档。"
    assert opened["steps"][0]["name"] == "数据来源"
    app.dependency_overrides.clear()
