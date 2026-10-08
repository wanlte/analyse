import json

from app.db import ROOT

SLOTS = {
    "orders": ["order_id", "user_id", "pay_time", "status", "pay_amount"],
    "order_items": ["order_id", "product_id", "quantity", "unit_price"],
    "users": ["user_id"],
    "products": ["product_id"],
    "behaviors": ["user_id", "behavior_type"],
}
SLOT_LABELS = {
    "orders": "订单",
    "order_items": "订单明细",
    "users": "用户",
    "products": "商品",
    "behaviors": "行为",
}


def list_packs() -> list[dict]:
    path = ROOT / "semantic" / "packs.json"
    return json.loads(path.read_text(encoding="utf-8"))
