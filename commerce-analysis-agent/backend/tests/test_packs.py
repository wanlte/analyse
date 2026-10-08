from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_only_ecommerce_pack_is_enterable():
    response = client.get("/resource-packs")
    packs = {item["code"]: item for item in response.json()}
    assert packs["EC_V1.0"]["enterable"] is True
    assert packs["EC_V1.0"]["metrics"] == [
        "GMV",
        "订单量",
        "支付买家数",
        "转化率",
        "客单价",
        "退款金额",
        "退款率",
        "复购率",
    ]
    assert packs["FN"]["enterable"] is False
    assert packs["ED"]["enterable"] is False
    assert packs["GM"]["enterable"] is False
    assert len(packs["EC_V1.0"]["questions"]) == 20
