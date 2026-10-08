from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)

ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount,channel\n"
    "1,7,2026-09-15,paid,100,自营\n"
    "2,7,2026-10-01,paid,200,自营\n"
    "3,7,2026-10-02,paid,100,直播\n"
    "4,7,2025-10-03,paid,100,自营\n"
)
GROUPED = (
    "SELECT channel, SUM(pay_amount) AS gmv FROM ods_orders "
    "WHERE status = 'paid' GROUP BY channel"
)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql" and ("看结构" in prompt or "对比" in prompt):
            return Completion(GROUPED, 1, 1)
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'",
                1,
                1,
            )
        return Completion(f"结论：{prompt}", 1, 1)


def _run(username: str, orders: str, payload: dict) -> dict:
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, username)
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": username, "resource_pack": "EC_V1.0"},
        files=pack_files(orders),
    ).json()
    body = client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": created["id"], **payload},
    ).json()
    app.dependency_overrides.clear()
    return body


def _step(body: dict, name: str) -> str:
    return next(step["detail"] for step in body["steps"] if step["name"] == name)


def test_lookup_answer_uses_the_query_result():
    body = _run("case-lookup", None, {"direction": "看大盘", "question": "查数：GMV 是多少"})
    assert body["status"] == "成功"
    assert "本期 GMV 为 20" in _step(body, "计算")
    assert "本期 GMV 为 20" in body["answer"]


def test_attribution_answer_uses_the_query_result():
    body = _run("case-attribute", ORDERS, {"direction": "看大盘", "question": "归因：环比和渠道贡献"})
    detail = _step(body, "计算")
    assert "环比：2026-10 相对 2026-09 200%" in detail
    assert "维度贡献：自营 占 80%（400/500）" in detail
    assert "环比：2026-10 相对 2026-09 200%" in body["answer"]
    assert "维度贡献：自营 占 80%（400/500）" in body["answer"]


def test_comparison_answer_uses_the_query_result():
    body = _run("case-compare", ORDERS, {"direction": "看结构", "question": "对比：各渠道占比"})
    assert "结构：" in _step(body, "计算")
    assert "自营 80%" in body["answer"]
    assert "直播 20%" in body["answer"]
