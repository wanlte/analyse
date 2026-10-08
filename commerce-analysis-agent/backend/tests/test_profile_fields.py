from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header

client = TestClient(app)


def test_email_and_phone_must_match_their_format():
    headers = auth_header(client, "profile-check")
    bad_email = client.patch("/me", headers=headers, json={"email": "not-an-email"})
    assert bad_email.status_code == 400
    assert bad_email.json()["detail"] == "邮箱格式不正确"
    bad_phone = client.patch("/me", headers=headers, json={"phone": "123"})
    assert bad_phone.status_code == 400
    saved = client.patch(
        "/me",
        headers=headers,
        json={"email": "a@b.cn", "phone": "13800000000"},
    )
    assert saved.status_code == 200
    assert saved.json()["email"] == "a@b.cn"
    assert saved.json()["phone"] == "13800000000"
