import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import ROOT, connect
from app.model import PlatformModel, model_for_user
from app.secrets import encrypt_secret
from app.security import current_user

router = APIRouter()


class ConfigBody(BaseModel):
    resource_pack: str | None = None
    output_preference: str | None = None
    default_range: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    category: str | None = None


class GroupBody(BaseModel):
    name: str = Field(min_length=1)
    metrics: list[str]


class KeyBody(BaseModel):
    api_key: str = Field(min_length=1)


class MetricBody(BaseModel):
    name: str = Field(min_length=1)
    field_name: str
    agg: str


FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
AGGREGATES = {"sum", "count", "avg", "rate"}


def load_config(user_id: int) -> dict:
    with connect() as connection:
        _ensure_config(connection, user_id)
        row = connection.execute(
            "SELECT * FROM user_config WHERE user_id = ?", (user_id,)
        ).fetchone()
    return _public_config(dict(row))


def load_groups(user_id: int) -> list[dict]:
    with connect() as connection:
        groups = connection.execute(
            "SELECT * FROM metric_group WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
        result = []
        for group in groups:
            items = connection.execute(
                """
                SELECT metric_name FROM metric_group_item
                WHERE group_id = ? ORDER BY position, metric_name
                """,
                (group["id"],),
            ).fetchall()
            result.append(
                {"id": group["id"], "name": group["name"], "metrics": [item[0] for item in items]}
            )
    return result


def _ensure_config(connection, user_id: int) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO user_config (user_id, resource_pack, output_preference, default_range, key_status, key_cipher)
        VALUES (?, 'EC_V1.0', '汇总结论', '本月', '平台密钥', '')
        """,
        (user_id,),
    )


def _public_config(row: dict) -> dict:
    return {
        "resource_pack": row["resource_pack"],
        "output_preference": row["output_preference"],
        "default_range": row["default_range"],
        "date_from": row.get("date_from") or "",
        "date_to": row.get("date_to") or "",
        "category": row.get("category") or "",
        "key_status": row["key_status"],
    }


def _enterable(code: str) -> bool:
    packs = json.loads((ROOT / "semantic" / "packs.json").read_text(encoding="utf-8"))
    return any(item["code"] == code and item["enterable"] for item in packs)


@router.get("/me/config")
def get_config(user: dict = Depends(current_user)):
    return load_config(user["id"])


@router.put("/me/config")
def put_config(body: ConfigBody, user: dict = Depends(current_user)):
    if body.resource_pack is not None and not _enterable(body.resource_pack):
        raise HTTPException(status_code=400, detail="该资源包未启用")
    if body.output_preference is not None and body.output_preference not in {
        "汇总结论",
        "结论加图表",
        "完整报告",
    }:
        raise HTTPException(status_code=400, detail="输出偏好无法识别")
    with connect() as connection:
        _ensure_config(connection, user["id"])
        current = dict(
            connection.execute(
                "SELECT * FROM user_config WHERE user_id = ?", (user["id"],)
            ).fetchone()
        )
        resource_pack = body.resource_pack or current["resource_pack"]
        preference = body.output_preference or current["output_preference"]
        default_range = body.default_range or current["default_range"]
        date_from = current["date_from"] if body.date_from is None else body.date_from
        date_to = current["date_to"] if body.date_to is None else body.date_to
        category = current.get("category") or "" if body.category is None else body.category
        connection.execute(
            """
            UPDATE user_config
            SET resource_pack = ?, output_preference = ?, default_range = ?,
                date_from = ?, date_to = ?, category = ?
            WHERE user_id = ?
            """,
            (resource_pack, preference, default_range, date_from, date_to, category, user["id"]),
        )
    return load_config(user["id"])


@router.get("/me/groups")
def get_groups(user: dict = Depends(current_user)):
    return load_groups(user["id"])


@router.post("/me/groups")
def create_group(body: GroupBody, user: dict = Depends(current_user)):
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO metric_group (user_id, name) VALUES (?, ?)",
            (user["id"], body.name),
        )
        group_id = cursor.lastrowid
        for position, name in enumerate(body.metrics):
            connection.execute(
                """
                INSERT INTO metric_group_item (group_id, metric_name, position)
                VALUES (?, ?, ?)
                """,
                (group_id, name, position),
            )
    return next(item for item in load_groups(user["id"]) if item["id"] == group_id)


@router.put("/me/key")
def put_key(body: KeyBody, user: dict = Depends(current_user)):
    cipher = encrypt_secret(body.api_key)
    with connect() as connection:
        _ensure_config(connection, user["id"])
        connection.execute(
            """
            UPDATE user_config SET key_status = '已绑定', key_cipher = ? WHERE user_id = ?
            """,
            (cipher, user["id"]),
        )
    return load_config(user["id"])


def load_user_metrics(user_id: int) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, name, field_name, agg FROM user_metric WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/me/categories")
def list_categories(_user: dict = Depends(current_user)):
    return json.loads((ROOT / "semantic" / "categories.json").read_text(encoding="utf-8"))


@router.get("/me/metrics")
def list_metrics(user: dict = Depends(current_user)):
    return load_user_metrics(user["id"])


@router.post("/me/metrics")
def create_metric(body: MetricBody, user: dict = Depends(current_user)):
    if body.agg not in AGGREGATES or not FIELD_NAME.fullmatch(body.field_name):
        raise HTTPException(status_code=400, detail="只允许字段名和 sum、count、avg、rate")
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO user_metric (user_id, name, field_name, agg)
            VALUES (?, ?, ?, ?)
            """,
            (user["id"], body.name, body.field_name, body.agg),
        )
    return load_user_metrics(user["id"])[-1]


def configured_model(user: dict, fallback):
    with connect() as connection:
        row = connection.execute(
            "SELECT key_cipher FROM user_config WHERE user_id = ?", (user["id"],)
        ).fetchone()
    if row is None or not row["key_cipher"] or not isinstance(fallback, PlatformModel):
        return fallback
    return model_for_user(row["key_cipher"], fallback)
