import json
from pathlib import Path

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


def test_metric_version_comes_from_the_file(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / "semantic" / "metrics.json"
    metrics = json.loads(source.read_text(encoding="utf-8"))
    for item in metrics:
        if item["name"] == "GMV":
            item["version"] = "v9.9"
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("METRICS_PATH", str(path))
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "metric-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "口径", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘"},
    ).json()
    detail = next(step["detail"] for step in body["steps"] if step["name"] == "口径")
    assert "v9.9" in detail
    app.dependency_overrides.clear()
