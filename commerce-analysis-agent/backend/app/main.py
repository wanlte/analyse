from contextlib import asynccontextmanager
import json
import re

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.analysis import router as analysis_router
from app.boards import router as board_router
from app.config import router as config_router
from app.datasets import router as dataset_router
from app.config import load_config
from app.db import connect, data_root, init_db
from app.ranges import resolve_window
from app.security import (
    create_token,
    current_user,
    hash_password,
    public_user,
    verify_password,
)
from app.warehouse import summarize_cards, warehouse_file


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="电商数据分析工作台", lifespan=lifespan)
app.include_router(dataset_router)
app.include_router(analysis_router)
app.include_router(board_router)
app.include_router(config_router)
init_db()


class RegisterBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    nickname: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


class ProfileBody(BaseModel):
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    username: str | None = None
    password: str | None = None
    current_password: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/home/cards")
def home_cards(user: dict = Depends(current_user)):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM datasets
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user["id"],),
        ).fetchone()
    if row is None:
        body = summarize_cards(data_root() / "missing.duckdb")
        body["source"] = ""
        return body
    folder = data_root() / f"tenant_{user['id']}" / str(row["id"])
    config = load_config(user["id"])
    try:
        date_from, date_to = resolve_window(
            config["default_range"], config["date_from"], config["date_to"]
        )
    except ValueError:
        date_from, date_to = "", ""
    body = summarize_cards(warehouse_file(folder), date_from, date_to)
    body["source"] = row["name"]
    return body


@app.post("/auth/register")
def register(body: RegisterBody):
    nickname = body.nickname or body.username
    try:
        with connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash, nickname)
                VALUES (?, ?, ?)
                """,
                (body.username, hash_password(body.password), nickname),
            )
            user_id = cursor.lastrowid
    except Exception as error:
        if "UNIQUE" in str(error):
            raise HTTPException(status_code=409, detail="登录账号已存在") from error
        raise
    return {"access_token": create_token(user_id)}


@app.post("/auth/login")
def login(body: LoginBody):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?", (body.username,)
        ).fetchone()
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return {"access_token": create_token(row["id"])}


@app.get("/me")
def me(user: dict = Depends(current_user)):
    return public_user(user)


@app.get("/me/usage")
def usage(user: dict = Depends(current_user)):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, question, status, request_count, input_tokens, output_tokens,
                   cost, failure_step, input_price, output_price
            FROM qa_log WHERE user_id = ? ORDER BY id
            """,
            (user["id"],),
        ).fetchall()
    items = [dict(row) for row in rows]
    return {
        "request_count": sum(item["request_count"] for item in items),
        "input_tokens": sum(item["input_tokens"] for item in items),
        "output_tokens": sum(item["output_tokens"] for item in items),
        "cost": sum(item["cost"] for item in items),
        "items": items,
    }


@app.get("/me/usage/{log_id}")
def usage_item(log_id: int, user: dict = Depends(current_user)):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM qa_log WHERE id = ? AND user_id = ?",
            (log_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    item = dict(row)
    item["steps"] = json.loads(item.pop("steps_json") or "[]")
    return item


@app.patch("/me")
def update_me(body: ProfileBody, user: dict = Depends(current_user)):
    updates = body.model_dump(exclude_unset=True)
    updates.pop("current_password", None)
    if "password" in updates:
        if not body.current_password or not verify_password(
            body.current_password, user["password_hash"]
        ):
            raise HTTPException(status_code=400, detail="当前密码不正确")
        updates["password_hash"] = hash_password(updates.pop("password"))
    if not updates:
        return public_user(user)
    if "email" in updates and updates["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", updates["email"]):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if "phone" in updates and updates["phone"] and not re.fullmatch(r"\d{11}", updates["phone"]):
        raise HTTPException(status_code=400, detail="手机号须为11位数字")
    if "username" in updates:
        with connect() as connection:
            taken = connection.execute(
                "SELECT id FROM users WHERE username = ? AND id != ?",
                (updates["username"], user["id"]),
            ).fetchone()
        if taken is not None:
            raise HTTPException(status_code=409, detail="登录账号已存在")
    assignments = ", ".join(f"{column} = ?" for column in updates)
    with connect() as connection:
        connection.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            (*updates.values(), user["id"]),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    return public_user(dict(row))


@app.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...), user: dict = Depends(current_user)
):
    raw = await file.read()
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    elif raw.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    else:
        raise HTTPException(status_code=400, detail="只接受 JPG 或 PNG")
    folder = data_root() / "avatars"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{user['id']}.*"):
        old.unlink()
    target = folder / f"{user['id']}.{extension}"
    target.write_bytes(raw)
    avatar_url = f"/avatars/{user['id']}.{extension}"
    with connect() as connection:
        connection.execute(
            "UPDATE users SET avatar_url = ? WHERE id = ?",
            (avatar_url, user["id"]),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    return public_user(dict(row))


@app.get("/avatars/{name}")
def avatar_file(name: str):
    path = data_root() / "avatars" / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="头像不存在")
    media = "image/png" if name.endswith(".png") else "image/jpeg"
    return FileResponse(path, media_type=media)
