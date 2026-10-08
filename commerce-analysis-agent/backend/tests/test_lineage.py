from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header, pack_files

client = TestClient(app)


def test_profile_and_lineage_name_the_dataset():
    headers = auth_header(client, "lineage-user")
    created = client.post(
        "/datasets",
        headers=headers,
        data={"name": "十月订单", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    ).json()
    profile = client.get(f"/datasets/{created['id']}/profile", headers=headers).json()
    orders = next(table for table in profile["tables"] if table["table"] == "ods_orders")
    assert orders["row_count"] == 2
    assert "pay_amount" in orders["columns"]
    lineage = client.get(f"/datasets/{created['id']}/lineage", headers=headers).json()
    gmv = next(item for item in lineage["metrics"] if item["metric"] == "GMV")
    assert lineage["dataset"] == "十月订单"
    assert "ads_trade_daily" in gmv["tables"]
    assert "dwd_order_detail" in gmv["tables"]
    assert "ods_orders" in gmv["sources"]
