from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.__enter__()


def test_login_and_update_nickname():
    registered = client.post(
        "/auth/register",
        json={"username": "ada", "password": "secret", "nickname": "Ada"},
    )
    assert registered.status_code == 200
    assert registered.json()["access_token"]

    logged_in = client.post(
        "/auth/login", json={"username": "ada", "password": "secret"}
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    renamed = client.patch("/me", json={"nickname": "分析员"}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.json()["nickname"] == "分析员"
    assert renamed.json()["role"] == "普通用户"

    again = client.get("/me", headers=headers)
    assert again.json()["nickname"] == "分析员"


def test_wrong_password_rejected():
    client.post("/auth/register", json={"username": "bea", "password": "secret"})
    rejected = client.post(
        "/auth/login", json={"username": "bea", "password": "wrong"}
    )
    assert rejected.status_code == 401
