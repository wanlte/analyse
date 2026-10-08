import base64

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header

client = TestClient(app)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_avatar_opens_and_password_changes():
    headers = auth_header(client, "avatar-user")
    uploaded = client.post(
        "/me/avatar",
        headers=headers,
        files={"file": ("face.png", PNG, "image/png")},
    )
    assert uploaded.status_code == 200
    avatar_url = uploaded.json()["avatar_url"]
    assert avatar_url.endswith(".png")
    opened = client.get(avatar_url)
    assert opened.status_code == 200
    assert opened.content.startswith(b"\x89PNG")

    rejected = client.patch(
        "/me",
        headers=headers,
        json={"password": "next-secret", "current_password": "wrong"},
    )
    assert rejected.status_code == 400
    changed = client.patch(
        "/me",
        headers=headers,
        json={"password": "next-secret", "current_password": "secret"},
    )
    assert changed.status_code == 200
    logged_in = client.post(
        "/auth/login", json={"username": "avatar-user", "password": "next-secret"}
    )
    assert logged_in.status_code == 200
