import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header

client = TestClient(app)


def test_board_keeps_the_saved_metric_version(tmp_path, monkeypatch):
    headers = auth_header(client, "board-user")
    saved = client.post(
        "/boards",
        headers=headers,
        json={
            "name": "十月大盘",
            "answer": "结论：GMV 为 20。",
            "steps": [{"name": "口径", "detail": "GMV v1.0"}],
            "metric_version": "v1.0",
            "data_date": "2026-10-02",
        },
    )
    assert saved.status_code == 200
    board_id = saved.json()["id"]
    source = Path(__file__).resolve().parents[2] / "semantic" / "metrics.json"
    metrics = json.loads(source.read_text(encoding="utf-8"))
    for item in metrics:
        if item["name"] == "GMV":
            item["version"] = "v8.8"
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("METRICS_PATH", str(path))
    listed = client.get("/boards", headers=headers).json()
    opened = client.get(f"/boards/{board_id}", headers=headers).json()
    assert listed[0]["id"] == board_id
    assert opened["metric_version"] == "v1.0"
    assert opened["data_date"] == "2026-10-02"
    assert opened["steps"][0]["detail"] == "GMV v1.0"


def test_rename_changes_the_title_and_delete_removes_the_board():
    headers = auth_header(client, "board-edit")
    saved = client.post(
        "/boards",
        headers=headers,
        json={
            "name": "旧标题",
            "answer": "结论：当时的回答。",
            "steps": [],
            "metric_version": "v1.0",
            "data_date": "2026-10-02",
        },
    ).json()
    renamed = client.patch(
        f"/boards/{saved['id']}",
        headers=headers,
        json={"name": "新标题"},
    )
    assert renamed.status_code == 200
    listed = client.get("/boards", headers=headers).json()
    assert listed[0]["name"] == "新标题"
    removed = client.delete(f"/boards/{saved['id']}", headers=headers)
    assert removed.status_code == 200
    assert client.get("/boards", headers=headers).json() == []
