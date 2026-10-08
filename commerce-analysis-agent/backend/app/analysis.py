import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import configured_model, load_config, load_groups, load_user_metrics
from app.db import ROOT, connect, data_root
from app.model import current_prices, get_model
from app.ranges import resolve_window
from app.security import current_user
from app.warehouse import warehouse_file

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.analyze import run_analysis
from agent.metrics import category_line

router = APIRouter()


class AnalysisBody(BaseModel):
    dataset_id: int
    direction: str = ""
    question: str = ""
    gmv_mode: str = "含退款"
    grain: str = "月"
    time_range: str = ""
    date_from: str = ""
    date_to: str = ""
    channel: str = ""
    category: str = ""
    city: str = ""
    compare: str = "环比"


@router.post("/analyses")
def create_analysis(
    body: AnalysisBody,
    user: dict = Depends(current_user),
    model=Depends(get_model),
):
    question = body.question or body.direction
    if not question:
        raise HTTPException(status_code=400, detail="请选择方向或输入问题")
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM datasets WHERE id = ? AND user_id = ?",
            (body.dataset_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    dataset = dict(row)
    folder = data_root() / f"tenant_{user['id']}" / str(dataset["id"])
    files = {path.stem: path.name for path in sorted(folder.glob("*.csv"))}
    model = configured_model(user, model)
    config = load_config(user["id"])
    try:
        date_from, date_to = resolve_window(body.time_range, body.date_from, body.date_to)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    started = time.perf_counter()
    outcome = run_analysis(
        dataset,
        question,
        warehouse_file(folder),
        model,
        files,
        direction=body.direction,
        scope=user.get("data_scope") or "",
        groups=load_groups(user["id"]),
        output_preference=config["output_preference"],
        gmv_mode=body.gmv_mode,
        grain=body.grain,
        date_from=date_from,
        date_to=date_to,
        channel=body.channel,
        category=body.category,
        city=body.city,
        compare=body.compare,
        category_text=category_line(config.get("category") or ""),
        custom_metrics=load_user_metrics(user["id"]),
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    input_price, output_price = current_prices()
    cost = outcome["input_tokens"] * input_price + outcome["output_tokens"] * output_price
    failure_step = next(
        (step["name"] for step in outcome["steps"] if step["status"] == "失败"),
        "",
    )
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO qa_log (
                user_id, dataset_id, question, sql, status, error,
                request_count, input_tokens, output_tokens, created_at,
                elapsed_ms, input_price, output_price, cost, failure_step, steps_json,
                answer, table_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                dataset["id"],
                question,
                outcome["sql"],
                outcome["status"],
                outcome["error"],
                outcome["request_count"],
                outcome["input_tokens"],
                outcome["output_tokens"],
                created_at,
                elapsed_ms,
                input_price,
                output_price,
                cost,
                failure_step,
                json.dumps(outcome["steps"], ensure_ascii=False),
                outcome["answer"],
                json.dumps(outcome["table"], ensure_ascii=False, default=str),
            ),
        )
        log_id = cursor.lastrowid
    return {**outcome, "log_id": log_id, "dataset": dataset["name"], "cost": cost, "failure_step": failure_step}


class FeedbackBody(BaseModel):
    vote: str
    note: str = ""


@router.get("/analyses")
def list_analyses(user: dict = Depends(current_user)):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, dataset_id, question, status, created_at
            FROM qa_log WHERE user_id = ? ORDER BY id DESC
            """,
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/analyses/{log_id}")
def get_analysis(log_id: int, user: dict = Depends(current_user)):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM qa_log WHERE id = ? AND user_id = ?",
            (log_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    item = dict(row)
    return {
        "id": item["id"],
        "dataset_id": item["dataset_id"],
        "question": item["question"],
        "answer": item["answer"],
        "sql": item["sql"],
        "status": item["status"],
        "steps": json.loads(item["steps_json"] or "[]"),
        "table": json.loads(item["table_json"] or "null"),
        "log_id": item["id"],
    }


@router.post("/analyses/{log_id}/feedback")
def save_feedback(
    log_id: int, body: FeedbackBody, user: dict = Depends(current_user)
):
    if body.vote not in {"赞", "踩"}:
        raise HTTPException(status_code=400, detail="请选择赞或踩")
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        log = connection.execute(
            "SELECT id FROM qa_log WHERE id = ? AND user_id = ?",
            (log_id, user["id"]),
        ).fetchone()
        if log is None:
            raise HTTPException(status_code=404, detail="记录不存在")
        connection.execute(
            """
            INSERT INTO feedback (log_id, user_id, vote, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(log_id) DO UPDATE SET
                vote = excluded.vote,
                note = excluded.note,
                created_at = excluded.created_at
            """,
            (log_id, user["id"], body.vote, body.note, created_at),
        )
        row = connection.execute(
            "SELECT vote, note FROM feedback WHERE log_id = ?", (log_id,)
        ).fetchone()
        count = connection.execute(
            "SELECT COUNT(*) FROM feedback WHERE log_id = ?", (log_id,)
        ).fetchone()[0]
    return {"log_id": log_id, "vote": row["vote"], "note": row["note"], "count": count}


DIRECTIONS = {"看大盘", "看趋势", "看结构", "找异常"}


def _cases_path() -> Path:
    configured = os.environ.get("EVAL_CASES")
    if configured:
        return Path(configured)
    return ROOT / "eval" / "ecommerce" / "cases.json"


@router.post("/analyses/{log_id}/promote")
def promote_case(log_id: int, user: dict = Depends(current_user)):
    with connect() as connection:
        row = connection.execute(
            "SELECT question FROM qa_log WHERE id = ? AND user_id = ?",
            (log_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    path = _cases_path()
    cases = json.loads(path.read_text(encoding="utf-8"))
    question = row["question"]
    case = {
        "id": max((item["id"] for item in cases), default=0) + 1,
        "direction": question if question in DIRECTIONS else "看大盘",
        "question": question,
        "source_log_id": log_id,
    }
    cases.append(case)
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    return case
