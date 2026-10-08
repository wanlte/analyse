import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.csvdata import missing_columns, read_table
from app.db import ROOT, connect, data_root
from app.packs import SLOTS
from app.security import current_user
from app.sources import SourceError, assert_supported, export_sqlite
from app.warehouse import load_csvs, profile_database, table_columns, warehouse_file

router = APIRouter()


def _dir(user_id: int, dataset_id: int) -> Path:
    path = data_root() / f"tenant_{user_id}" / str(dataset_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _store_slots(files: dict[str, UploadFile], folder: Path) -> dict:
    summary = {}
    missing = {}
    for slot, required in SLOTS.items():
        upload = files.get(slot)
        if upload is None:
            missing[slot] = required
            continue
        target = folder / f"{slot}.csv"
        target.write_bytes(await upload.read())
        columns, count, preview = read_table(target)
        absent = missing_columns(columns, required)
        if absent:
            missing[slot] = absent
        summary[slot] = {"columns": columns, "row_count": count, "preview": preview}
    return {"files": summary, "missing": missing}


@router.get("/resource-packs")
def resource_packs():
    from app.packs import list_packs

    return list_packs()


@router.post("/datasets/preview")
async def preview(
    resource_pack: str = Form(""),
    orders: UploadFile | None = File(None),
    order_items: UploadFile | None = File(None),
    users: UploadFile | None = File(None),
    products: UploadFile | None = File(None),
    behaviors: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    user: dict = Depends(current_user),
):
    folder = data_root() / "preview" / str(user["id"])
    if folder.exists():
        for child in folder.glob("*"):
            child.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    if resource_pack:
        stored = await _store_slots(
            {
                "orders": orders,
                "order_items": order_items,
                "users": users,
                "products": products,
                "behaviors": behaviors,
            },
            folder,
        )
        return stored
    if file is None:
        raise HTTPException(status_code=400, detail="请上传文件")
    target = folder / "uploaded.csv"
    target.write_bytes(await file.read())
    columns, count, rows = read_table(target)
    return {
        "files": {"uploaded": {"columns": columns, "row_count": count, "preview": rows}},
        "missing": {},
    }


@router.post("/datasets")
async def create_dataset(
    name: str = Form(...),
    resource_pack: str = Form(""),
    source_type: str = Form("csv"),
    orders: UploadFile | None = File(None),
    order_items: UploadFile | None = File(None),
    users: UploadFile | None = File(None),
    products: UploadFile | None = File(None),
    behaviors: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    user: dict = Depends(current_user),
):
    try:
        kind = assert_supported(source_type)
    except SourceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO datasets (user_id, name, resource_pack, row_count, created_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (user["id"], name, resource_pack or None, created_at),
        )
        dataset_id = cursor.lastrowid
    folder = _dir(user["id"], dataset_id)
    if kind == "sqlite":
        if file is None:
            _delete_dataset(dataset_id, folder)
            raise HTTPException(status_code=400, detail="请上传文件")
        target = folder / "source.sqlite"
        target.write_bytes(await file.read())
        try:
            export_sqlite(target, folder)
        except SourceError as error:
            _delete_dataset(dataset_id, folder)
            raise HTTPException(status_code=400, detail=str(error)) from error
        missing = {}
        summary = {}
        for slot, required in SLOTS.items():
            columns, count, preview = read_table(folder / f"{slot}.csv")
            absent = missing_columns(columns, required)
            if absent:
                missing[slot] = absent
            summary[slot] = {"row_count": count}
        if missing:
            _delete_dataset(dataset_id, folder)
            raise HTTPException(status_code=400, detail={"missing": missing})
        load_csvs(folder, list(SLOTS))
        row_count = sum(item["row_count"] for item in summary.values())
    elif resource_pack:
        stored = await _store_slots(
            {
                "orders": orders,
                "order_items": order_items,
                "users": users,
                "products": products,
                "behaviors": behaviors,
            },
            folder,
        )
        if stored["missing"]:
            _delete_dataset(dataset_id, folder)
            raise HTTPException(status_code=400, detail={"missing": stored["missing"]})
        load_csvs(folder, list(SLOTS))
        row_count = sum(item["row_count"] for item in stored["files"].values())
    else:
        if file is None:
            _delete_dataset(dataset_id, folder)
            raise HTTPException(status_code=400, detail="请上传文件")
        target = folder / "uploaded.csv"
        target.write_bytes(await file.read())
        columns, row_count, _rows = read_table(target)
        if not columns:
            _delete_dataset(dataset_id, folder)
            raise HTTPException(status_code=400, detail="文件没有表头")
        load_csvs_uploaded(folder)
    with connect() as connection:
        connection.execute(
            "UPDATE datasets SET row_count = ? WHERE id = ?", (row_count, dataset_id)
        )
    return _one(user["id"], dataset_id)


def load_csvs_uploaded(folder: Path):
    from app.warehouse import warehouse_file
    import duckdb

    target = warehouse_file(folder)
    connection = duckdb.connect(str(target))
    try:
        connection.execute(
            "CREATE TABLE uploaded AS SELECT * FROM read_csv_auto(?, header=true)",
            [str(folder / "uploaded.csv")],
        )
    finally:
        connection.close()


def _delete_dataset(dataset_id: int, folder: Path) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    if folder.exists():
        for child in folder.glob("*"):
            child.unlink()
        folder.rmdir()


def _one(user_id: int, dataset_id: int) -> dict:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM datasets WHERE id = ? AND user_id = ?",
            (dataset_id, user_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return _public(dict(row))


def _public(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "resource_pack": row["resource_pack"],
        "row_count": row["row_count"],
        "created_at": row["created_at"],
    }


@router.get("/datasets")
def list_datasets(user: dict = Depends(current_user)):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM datasets
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user["id"],),
        ).fetchall()
    return [_public(dict(row)) for row in rows]


@router.get("/datasets/{dataset_id}")
def dataset_detail(dataset_id: int, user: dict = Depends(current_user)):
    item = _one(user["id"], dataset_id)
    folder = data_root() / f"tenant_{user['id']}" / str(dataset_id)
    files = {}
    for path in sorted(folder.glob("*.csv")):
        columns, count, preview = read_table(path)
        files[path.stem] = {"columns": columns, "row_count": count, "preview": preview}
    item["files"] = files
    return item


@router.get("/datasets/{dataset_id}/dimensions")
def dataset_dimensions(dataset_id: int, user: dict = Depends(current_user)):
    _one(user["id"], dataset_id)
    database = warehouse_file(_dir(user["id"], dataset_id))
    values = {}
    for column in ("channel", "category", "city"):
        values[column] = _distinct(database, "ods_orders", column) or _distinct(
            database, "ads_trade_daily", column
        )
    return values


def _distinct(database: Path, table: str, column: str) -> list[str]:
    if column not in table_columns(database, table):
        return []
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            f'SELECT DISTINCT "{column}" FROM {table} WHERE "{column}" IS NOT NULL ORDER BY 1'
        ).fetchall()
    finally:
        connection.close()
    return [str(row[0]) for row in rows if row[0] not in (None, "")]


@router.get("/datasets/{dataset_id}/profile")
def dataset_profile(dataset_id: int, user: dict = Depends(current_user)):
    item = _one(user["id"], dataset_id)
    folder = data_root() / f"tenant_{user['id']}" / str(dataset_id)
    return {"id": item["id"], "name": item["name"], "tables": profile_database(warehouse_file(folder))}


@router.get("/datasets/{dataset_id}/lineage")
def dataset_lineage(dataset_id: int, user: dict = Depends(current_user)):
    item = _one(user["id"], dataset_id)
    chain = json.loads((ROOT / "semantic" / "lineage.json").read_text(encoding="utf-8"))
    return {"dataset": item["name"], "metrics": chain}
