from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header, pack_files

client = TestClient(app)


def test_home_cards_use_the_latest_saved_dataset():
    headers = auth_header(client, "home-user")
    orders = (
        "order_id,user_id,pay_time,status,pay_amount,refund_amount\n"
        "1,7,2026-09-01,paid,100,0\n"
        "2,7,2026-10-02,paid,80,10\n"
    )
    items = "order_id,product_id,quantity,unit_price\n1,3,1,100\n2,3,1,80\n"
    behaviors = "user_id,behavior_type\n7,pv\n8,pv\n"
    files = pack_files(orders)
    files["order_items"] = ("items.csv", items, "text/csv")
    files["behaviors"] = ("behaviors.csv", behaviors, "text/csv")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "首页订单", "resource_pack": "EC_V1.0"},
        files=files,
    )
    assert created.status_code == 200
    saved = client.put(
        "/me/config",
        headers=headers,
        json={
            "default_range": "自定义",
            "date_from": "2026-09-01",
            "date_to": "2026-10-31",
        },
    )
    assert saved.status_code == 200
    body = client.get("/home/cards", headers=headers).json()
    assert body["source"] == "首页订单"
    assert body["data_date"] == "2026-10-02"
    cards = {item["name"]: item for item in body["cards"]}
    assert cards["GMV"]["value"] == 80
    assert cards["GMV"]["change"] == -0.2
    assert cards["订单量"]["value"] == 1
    assert cards["转化率"]["value"] == 0.5
    assert cards["退款率"]["value"] == 0.125
