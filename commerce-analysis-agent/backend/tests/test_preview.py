from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header, pack_files

client = TestClient(app)


def test_preview_missing_column_does_not_save():
    headers = auth_header(client, "preview-user")
    before = client.get("/datasets", headers=headers).json()
    orders = "order_id,user_id,pay_time,status\n1,7,2026-10-01,paid\n"
    preview = client.post(
        "/datasets/preview",
        headers=headers,
        data={"resource_pack": "EC_V1.0"},
        files=pack_files(orders),
    )
    assert preview.status_code == 200
    assert "pay_amount" in preview.json()["missing"]["orders"]
    assert preview.json()["files"]["orders"]["row_count"] == 1
    assert len(preview.json()["files"]["orders"]["preview"]) == 1
    assert client.get("/datasets", headers=headers).json() == before
