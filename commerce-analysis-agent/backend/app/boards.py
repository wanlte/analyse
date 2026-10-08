import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import connect
from app.security import current_user

router = APIRouter()


class BoardBody(BaseModel):
    name: str = Field(min_length=1)
    answer: str = ""
    steps: list = []
    metric_version: str
    data_date: str


def _public(row) -> dict:
    item = dict(row)
    item["steps"] = json.loads(item.pop("steps_json"))
    return item


@router.post("/boards")
def create_board(body: BoardBody, user: dict = Depends(current_user)):
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO boards (
                user_id, name, answer, steps_json, metric_version, data_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                body.name,
                body.answer,
                json.dumps(body.steps, ensure_ascii=False),
                body.metric_version,
                body.data_date,
                created_at,
            ),
        )
        row = connection.execute(
            "SELECT * FROM boards WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return _public(row)


@router.get("/boards")
def list_boards(user: dict = Depends(current_user)):
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM boards WHERE user_id = ? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
    return [_public(row) for row in rows]


@router.get("/boards/{board_id}")
def get_board(board_id: int, user: dict = Depends(current_user)):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="看板不存在")
    return _public(row)


class RenameBody(BaseModel):
    name: str = Field(min_length=1)


@router.patch("/boards/{board_id}")
def rename_board(board_id: int, body: RenameBody, user: dict = Depends(current_user)):
    with connect() as connection:
        found = connection.execute(
            "SELECT id FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user["id"]),
        ).fetchone()
        if found is None:
            raise HTTPException(status_code=404, detail="看板不存在")
        connection.execute(
            "UPDATE boards SET name = ? WHERE id = ? AND user_id = ?",
            (body.name, board_id, user["id"]),
        )
        row = connection.execute(
            "SELECT * FROM boards WHERE id = ?", (board_id,)
        ).fetchone()
    return _public(row)


@router.delete("/boards/{board_id}")
def delete_board(board_id: int, user: dict = Depends(current_user)):
    with connect() as connection:
        found = connection.execute(
            "SELECT id FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user["id"]),
        ).fetchone()
        if found is None:
            raise HTTPException(status_code=404, detail="看板不存在")
        connection.execute(
            "DELETE FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user["id"]),
        )
    return {"ok": True}
