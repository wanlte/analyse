from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header, pack_files

client = TestClient(app)


def test_missing_column_is_rejected_and_two_saves_stay_separate():
    headers = auth_header(client, "data-user")
    broken = pack_files("order_id,user_id,pay_time,status\n1,7,2026-10-01,paid\n")
    rejected = client.post(
        "/datasets",
        headers=headers,
        data={"name": "坏数据", "resource_pack": "EC_V1.0"},
        files=broken,
    )
    assert rejected.status_code == 400
    assert "pay_amount" in rejected.json()["detail"]["missing"]["orders"]

    first = client.post(
        "/datasets",
        headers=headers,
        data={"name": "第一次", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    )
    second = client.post(
        "/datasets",
        headers=headers,
        data={"name": "第二次", "resource_pack": "EC_V1.0"},
        files=pack_files(),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    listed = client.get("/datasets", headers=headers).json()
    assert [item["name"] for item in listed] == ["第二次", "第一次"]
    detail = client.get(f"/datasets/{first.json()['id']}", headers=headers)
    assert detail.json()["files"]["orders"]["preview"][0]["order_id"] == "1"
