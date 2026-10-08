from fastapi.testclient import TestClient

from app.main import app
from app.model import Completion, get_model
from tests.helpers import auth_header, pack_files

client = TestClient(app)

GROSS_ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount\n"
    "1,7,2026-10-01,paid,100\n"
)
GROSS_ITEMS = (
    "order_id,product_id,quantity,unit_price,refund_amount\n"
    "1,3,1,100,10\n"
)
GRAIN_ORDERS = (
    "order_id,user_id,pay_time,status,pay_amount\n"
    "1,7,2026-01-15,paid,100\n"
    "2,7,2026-02-15,paid,50\n"
    "3,7,2026-04-15,paid,80\n"
)


class FakeModel:
    def complete(self, purpose: str, prompt: str) -> Completion:
        if purpose == "sql":
            return Completion("SELECT SUM(pay_amount) AS gmv FROM ods_orders WHERE status = 'paid'", 1, 1)
        return Completion("结论：来自查询。数据支撑：见结果。建议：核对。", 1, 1)


def _files(orders: str, items: str | None = None):
    files = pack_files(orders)
    if items:
        files["order_items"] = ("items.csv", items, "text/csv")
    return files


def _run(headers, dataset_id, **payload):
    return client.post(
        "/analyses",
        headers=headers,
        json={"dataset_id": dataset_id, "direction": "看大盘", **payload},
    ).json()


def test_net_gmv_subtracts_refund_and_quarter_changes_period():
    app.dependency_overrides[get_model] = lambda: FakeModel()
    headers = auth_header(client, "switch-user")
    refunded = client.post(
        "/datasets",
        headers=headers,
        data={"name": "退款", "resource_pack": "EC_V1.0"},
        files=_files(GROSS_ORDERS, GROSS_ITEMS),
    ).json()
    gross = _run(headers, refunded["id"], gmv_mode="含退款")
    net = _run(headers, refunded["id"], gmv_mode="净GMV")
    gross_detail = _step(gross, "计算")
    net_detail = _step(net, "计算")
    assert "本期 GMV 为 100" in gross_detail
    assert "净 GMV 为 90" in net_detail
    assert 100 - 90 == 10

    dated = client.post(
        "/datasets",
        headers=headers,
        data={"name": "粒度", "resource_pack": "EC_V1.0"},
        files=pack_files(GRAIN_ORDERS),
    ).json()
    month = _run(headers, dated["id"], grain="月")
    quarter = _run(headers, dated["id"], grain="季")
    assert "2026-04" in _step(month, "计算")
    assert "2026-Q2" in _step(quarter, "计算")
    assert _step(month, "计算") != _step(quarter, "计算")
    app.dependency_overrides.clear()


def _step(body: dict, name: str) -> str:
    return next(step["detail"] for step in body["steps"] if step["name"] == name)
