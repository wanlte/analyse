import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("APP_DB", str(ROOT / "data" / "eval.db"))
os.environ.setdefault("DATA_ROOT", str(ROOT / "data" / "eval"))

from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model


def load_cases() -> list:
    path = Path(os.environ.get("EVAL_CASES", Path(__file__).parent / "ecommerce" / "cases.json"))
    return json.loads(path.read_text(encoding="utf-8"))


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql" and ("看结构" in prompt or "找异常" in prompt):
            return Completion(
                "SELECT channel, SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid' GROUP BY channel",
                1,
                1,
            )
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv, COUNT(*) AS orders FROM ods_orders WHERE status = 'paid'",
                1,
                1,
            )
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def main() -> int:
    real_key = bool(os.environ.get("OPENAI_API_KEY"))
    if not real_key:
        app.dependency_overrides[get_model] = lambda: FakeModel()
        print("未做真实模型调用，使用假模型只验证评测脚本。")
    client = TestClient(app)
    client.post("/auth/register", json={"username": "eval", "password": "secret"})
    token = client.post("/auth/login", json={"username": "eval", "password": "secret"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    files = {
        "orders": (
            "orders.csv",
            "order_id,user_id,pay_time,status,pay_amount,channel\n"
            "1,1,2026-09-01,paid,100,自营\n"
            "2,1,2026-10-01,paid,200,自营\n"
            "3,1,2026-10-02,paid,100,直播\n"
            "4,1,2025-10-01,paid,100,自营\n",
            "text/csv",
        ),
        "order_items": ("items.csv", "order_id,product_id,quantity,unit_price\n1,1,1,3\n", "text/csv"),
        "users": ("users.csv", "user_id\n1\n", "text/csv"),
        "products": ("products.csv", "product_id\n1\n", "text/csv"),
        "behaviors": ("behaviors.csv", "user_id,behavior_type\n1,pv\n", "text/csv"),
    }
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "评测集", "resource_pack": "EC_V1.0"},
        files=files,
    )
    dataset_id = created.json()["id"]
    cases = load_cases()
    success = 0
    tokens = 0
    started = time.perf_counter()
    for case in cases:
        response = client.post(
            "/analyses",
            headers=headers,
            json={"dataset_id": dataset_id, "direction": case["direction"], "question": case["question"]},
        )
        if response.status_code == 200 and response.json()["status"] == "成功":
            success += 1
            body = response.json()
            tokens += body["input_tokens"] + body["output_tokens"]
    elapsed = time.perf_counter() - started
    rate = success / len(cases)
    print(
        f"SQL 执行成功 {success}/{len(cases)}，比例 {rate:.0%}，token {tokens}，耗时 {elapsed:.2f} 秒"
    )
    if real_key and rate < 0.8:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
