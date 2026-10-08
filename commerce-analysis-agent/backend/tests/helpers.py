from fastapi.testclient import TestClient


def auth_header(client: TestClient, username: str) -> dict:
    client.post(
        "/auth/register",
        json={"username": username, "password": "secret", "nickname": username},
    )
    token = client.post(
        "/auth/login", json={"username": username, "password": "secret"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def pack_files(orders: str | None = None) -> dict:
    order_csv = orders or (
        "order_id,user_id,pay_time,status,pay_amount\n"
        "1,7,2026-10-01,paid,12\n"
        "2,7,2026-10-02,paid,8\n"
    )
    return {
        "orders": ("orders.csv", order_csv, "text/csv"),
        "order_items": (
            "items.csv",
            "order_id,product_id,quantity,unit_price\n1,3,1,12\n",
            "text/csv",
        ),
        "users": ("users.csv", "user_id\n7\n", "text/csv"),
        "products": ("products.csv", "product_id\n3\n", "text/csv"),
        "behaviors": (
            "behaviors.csv",
            "user_id,behavior_type\n7,pv\n",
            "text/csv",
        ),
    }
