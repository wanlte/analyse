from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion(
                "SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1
            )
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对口径。", 1, 1)


def test_custom_window_keeps_only_october_gmv():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "time-user")
    orders = (
        "order_id,user_id,pay_time,status,pay_amount\n"
        "1,7,2026-09-01,paid,100\n"
        "2,7,2026-10-02,paid,80\n"
    )
    items = "order_id,product_id,quantity,unit_price\n1,3,1,100\n2,3,1,80\n"
    files = pack_files(orders)
    files["order_items"] = ("items.csv", items, "text/csv")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "分月", "resource_pack": "EC_V1.0"},
        files=files,
    )
    assert created.status_code == 200
    body = client.post(
        "/analyses",
        headers=headers,
        json={
            "dataset_id": created.json()["id"],
            "direction": "看大盘",
            "time_range": "自定义",
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
        },
    ).json()
    calculate = next(step["detail"] for step in body["steps"] if step["name"] == "计算")
    assert "本期 GMV 为 80" in calculate
    assert "100" not in calculate
    app.dependency_overrides.clear()
