import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import ROOT
from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)

CHANNEL_ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount,channel\n"
    "1,7,2026-09-15,paid,100,自营\n"
    "2,7,2026-10-01,paid,200,自营\n"
    "3,7,2026-10-02,paid,100,直播\n"
)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql" and "看结构" in prompt:
            return Completion(
                "SELECT channel, SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid' GROUP BY channel",
                1,
                1,
            )
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_failed_log_becomes_a_passing_case(tmp_path, monkeypatch):
    source = ROOT / "eval" / "ecommerce" / "cases.json"
    target = tmp_path / "cases.json"
    shutil.copy(source, target)
    monkeypatch.setenv("EVAL_CASES", str(target))
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "promote-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "缺渠道", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    failed = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看结构"},
    ).json()
    assert failed["failure_step"] == "读数"
    promoted = client.post(f"/analyses/{failed['log_id']}/promote", headers=headers)
    assert promoted.status_code == 200
    cases = json.loads(target.read_text(encoding="utf-8"))
    assert cases[-1]["source_log_id"] == failed["log_id"]
    fixed = client.post(
        "/datasets",
        headers=headers,
        data={"name": "有渠道", "resource_pack": "EC_V1.0"},
        files=pack_files(CHANNEL_ORDERS),
    ).json()
    again = client.post(
        "/analyses",
        headers=headers,
        json={
            "dataset_id": fixed["id"],
            "direction": cases[-1]["direction"],
            "question": cases[-1]["question"],
        },
    ).json()
    assert again["status"] == "成功"
    import sys

    sys.path.insert(0, str(ROOT))
    import eval.run_eval as run_eval

    assert run_eval.main() == 0
    app.dependency_overrides.clear()


def test_walkthrough_shows_source_metric_and_answer():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "walk-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "走通", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], "direction": "看大盘"},
    ).json()
    names = [step["name"] for step in body["steps"]]
    assert names[0] == "数据来源"
    assert "口径" in names
    assert "结论" in names
    assert body["answer"]
    app.dependency_overrides.clear()
