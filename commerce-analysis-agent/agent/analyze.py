from app.sandbox import SandboxError, execute_readonly
from app.warehouse import table_columns

from agent.attribute import (
    channel_contribution,
    keep_compare,
    largest_gap,
    period_change,
    structure_shares,
)
from agent.metrics import category_line, gmv_metric, lines_for, metric_detail
from agent.queries import load_queries

NEEDS_COLUMN = {"看结构": "channel", "找异常": "channel"}


def run_analysis(
    dataset: dict,
    question: str,
    database,
    model,
    files: dict,
    direction: str = "",
    scope: str = "",
    groups: list | None = None,
    output_preference: str = "汇总结论",
    gmv_mode: str = "含退款",
    grain: str = "月",
    date_from: str = "",
    date_to: str = "",
    channel: str = "",
    category: str = "",
    city: str = "",
    compare: str = "环比",
    category_text: str = "",
    custom_metrics: list | None = None,
) -> dict:
    metric = gmv_metric() if dataset["resource_pack"] else None
    steps = [_source_step(dataset, files)]
    if metric:
        steps.append(
            {
                "name": "口径",
                "status": "完成",
                "detail": _metric_text(question, groups, database, gmv_mode, category_text),
            }
        )
    applied, missing_dimension = _dimensions(database, channel, category, city)
    if missing_dimension:
        if metric:
            steps[-1]["detail"] += f" {missing_dimension}"
        else:
            steps.append({"name": "口径", "status": "完成", "detail": missing_dimension})
    table_name = "ods_orders" if dataset["resource_pack"] else "uploaded"
    columns = table_columns(database, table_name)
    custom = _custom_hit(question, custom_metrics)
    if custom and custom["field_name"] not in columns:
        steps.extend(
            [
                {"name": "生成查询", "status": "完成", "detail": "未生成查询"},
                {"name": "校验", "status": "完成", "detail": "未执行"},
                {"name": "读数", "status": "失败", "detail": f"缺少列 {custom['field_name']}"},
            ]
        )
        return _done(
            steps, None, None, None, f"缺少列 {custom['field_name']}", metric, "", dataset, database, columns, scope
        )
    needed = _needed_column(direction, question, columns, database)
    if needed and needed not in columns:
        steps.extend(
            [
                {"name": "生成查询", "status": "完成", "detail": "未生成查询"},
                {"name": "校验", "status": "完成", "detail": "未执行"},
                {"name": "读数", "status": "失败", "detail": f"缺少列 {needed}"},
            ]
        )
        return _done(
            steps, None, None, None, f"缺少列 {needed}", metric, "", dataset, database, columns, scope
        )
    sql_prompt = f"方向：{direction}\n问题：{question}\n表：{', '.join(files)}"
    sql_result = model.complete("sql", sql_prompt)
    steps.append({"name": "生成查询", "status": "完成", "detail": "已生成"})
    steps.append({"name": "校验", "status": "进行中", "detail": "只读 · 已限制行数"})
    try:
        table = execute_readonly(
            database,
            sql_result.content,
            scope=scope,
            date_from=date_from,
            date_to=date_to,
            channel=applied["channel"],
            category=applied["category"],
            city=applied["city"],
        )
    except SandboxError as error:
        steps[-1] = {"name": "校验", "status": "失败", "detail": str(error)}
        return _done(
            steps, sql_result, None, None, str(error), metric, "", dataset, database, columns, scope
        )
    steps[-1] = {"name": "校验", "status": "完成", "detail": "只读 · 已限制行数 · 通过"}
    steps.append({"name": "读数", "status": "完成", "detail": f"返回 {len(table['rows'])} 行"})
    compare = _calculate(
        direction,
        question,
        table,
        database,
        columns,
        scope,
        gmv_mode,
        grain,
        date_from,
        date_to,
        applied["channel"],
        applied["category"],
        applied["city"],
        compare,
        custom,
    )
    steps.append({"name": "计算", "status": "完成", "detail": compare})
    answer = model.complete(
        "answer",
        f"{_preference_text(output_preference)}\n问题：{question}\n结果：{table}\n{compare}",
    )
    steps.append({"name": "结论", "status": "完成", "detail": "已写出"})
    return _done(
        steps,
        sql_result,
        answer,
        table,
        "",
        metric,
        table["sql"],
        dataset,
        database,
        columns,
        scope,
        date_from,
        date_to,
    )


def _dimensions(database, channel: str, category: str, city: str) -> tuple[dict, str]:
    columns = set(table_columns(database, "ods_orders"))
    applied = {"channel": "", "category": "", "city": ""}
    missing = []
    for name, value in (("channel", channel), ("category", category), ("city", city)):
        if not value or value == "全部":
            continue
        if name not in columns:
            missing.append(name)
        else:
            applied[name] = value
    note = f"没有对应列 {'、'.join(missing)}" if missing else ""
    return applied, note


def _needed_column(direction: str, question: str, columns: list[str], database) -> str:
    if "下钻到单品" in question:
        items = table_columns(database, "ods_order_items")
        if "product_id" not in columns and "product_id" not in items:
            return "product_id"
        return ""
    return NEEDS_COLUMN.get(direction, "") if NEEDS_COLUMN.get(direction, "") not in columns else ""


def _metric_text(question: str, groups: list | None, database, gmv_mode: str, category_text: str = "") -> str:
    detail = metric_detail()
    extras = []
    for group in groups or []:
        if group["name"] and group["name"] in question:
            extras.append(lines_for(group["metrics"]))
    extra = " ".join(part for part in extras if part)
    detail = f"{detail} {extra}".strip()
    if category_text:
        detail = f"{detail} {category_text}".strip()
    if gmv_mode == "净GMV" and "refund_amount" not in table_columns(database, "ods_order_items"):
        detail += " 没有退款列"
    return detail


def _preference_text(preference: str) -> str:
    if preference == "完整报告":
        return "写出结论、数据支撑和建议。SQL 留在证据里。"
    if preference == "结论加图表":
        return "写出结论，并说明对应的图。"
    return "只写结论一句。"


def _source_step(dataset: dict, files: dict) -> dict:
    pack = dataset["resource_pack"] or "未使用资源包"
    names = "、".join(files) or "无文件"
    detail = f"{dataset['name']} · {names} · 保存于 {dataset['created_at']} · {pack}"
    return {"name": "数据来源", "status": "完成", "detail": detail}


def _custom_hit(question: str, metrics: list | None) -> dict | None:
    for item in metrics or []:
        if item["name"] and item["name"] in question:
            return item
    return None


def _custom_value(database, scope, metric: dict, date_from, date_to, channel, category, city) -> str:
    field = metric["field_name"]
    if metric["agg"] == "rate":
        expression = f'COUNT("{field}") * 1.0 / NULLIF(COUNT(*), 0)'
    else:
        expression = f'{metric["agg"].upper()}("{field}")'
    try:
        result = execute_readonly(
            database,
            f"SELECT {expression} AS value FROM ods_orders",
            scope=scope,
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            category=category,
            city=city,
        )
        amount = result["rows"][0][0] if result["rows"] else None
    except SandboxError as error:
        return f"{metric['name']} 无法计算：{error}"
    shown = f"{amount:g}" if isinstance(amount, float) else str(amount)
    return f"{metric['name']} 为 {shown}"


def _calculate(
    direction: str,
    question: str,
    table: dict,
    database,
    columns: list[str],
    scope: str,
    gmv_mode: str,
    grain: str,
    date_from: str = "",
    date_to: str = "",
    channel: str = "",
    category: str = "",
    city: str = "",
    compare: str = "环比",
    custom: dict | None = None,
) -> str:
    parts = [_gmv_text(database, scope, gmv_mode, table, date_from, date_to, channel, category, city)]
    if "pay_time" in columns:
        period_name = {"周": "period_week", "季": "period_quarter"}.get(grain, "period")
        period_text = _fixed(
            period_name, database, scope, period_change, date_from, date_to, channel, category, city
        )
        parts.append(keep_compare(period_text, compare))
    if custom:
        parts.append(_custom_value(database, scope, custom, date_from, date_to, channel, category, city))
    if "channel" in columns:
        parts.append(_fixed("channel", database, scope, channel_contribution, date_from, date_to, channel, category, city))
    if "下钻到单品" in question and "product_id" in table_columns(database, "ods_order_items"):
        parts.append(_fixed("product", database, scope, structure_shares, date_from, date_to, channel, category, city))
    grouped = _grouped(direction, table)
    if grouped:
        parts.append(grouped)
    return " ".join(parts)


def _gmv_text(
    database,
    scope: str,
    gmv_mode: str,
    table: dict,
    date_from: str = "",
    date_to: str = "",
    channel: str = "",
    category: str = "",
    city: str = "",
) -> str:
    has_refund = "refund_amount" in table_columns(database, "ods_order_items")
    query_name = "gmv_net" if gmv_mode == "净GMV" and has_refund else "gmv_gross"
    try:
        result = execute_readonly(
            database,
            load_queries()[query_name],
            scope=scope,
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            category=category,
            city=city,
        )
        amount = result["rows"][0][0] if result["rows"] else None
    except SandboxError:
        amount = _gmv(table)
    if amount is None:
        return "本次结果没有 GMV 列"
    if gmv_mode == "净GMV" and has_refund:
        return f"净 GMV 为 {amount:g}" if isinstance(amount, float) else f"净 GMV 为 {amount}"
    if gmv_mode == "净GMV":
        shown = f"{amount:g}" if isinstance(amount, float) else str(amount)
        return f"净 GMV 为 {shown}"
    shown = f"{amount:g}" if isinstance(amount, float) else str(amount)
    return f"本期 GMV 为 {shown}"


def _fixed(
    name: str,
    database,
    scope: str,
    summarize,
    date_from: str = "",
    date_to: str = "",
    channel: str = "",
    category: str = "",
    city: str = "",
) -> str:
    try:
        table = execute_readonly(
            database,
            load_queries()[name],
            scope=scope,
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            category=category,
            city=city,
        )
    except SandboxError as error:
        return f"{name} 无法计算：{error}"
    return summarize(table["rows"])


def _grouped(direction: str, table: dict) -> str:
    columns = table["columns"]
    if direction not in NEEDS_COLUMN:
        return ""
    if "channel" not in columns or "gmv" not in columns:
        return "查询结果没有 channel 列"
    rows = [
        (row[columns.index("channel")], row[columns.index("gmv")]) for row in table["rows"]
    ]
    if direction == "看结构":
        return structure_shares(rows)
    return largest_gap(rows)


def _gmv(table: dict):
    if "gmv" not in table["columns"] or not table["rows"]:
        return None
    return table["rows"][0][table["columns"].index("gmv")]


def _data_date(
    database, columns: list[str], dataset: dict, scope: str, date_from: str = "", date_to: str = ""
) -> str:
    fallback = str(dataset["created_at"])[:10]
    if "pay_time" not in columns:
        return fallback
    try:
        table = execute_readonly(
            database, load_queries()["data_date"], scope=scope, date_from=date_from, date_to=date_to
        )
    except SandboxError:
        return fallback
    if not table["rows"] or table["rows"][0][0] is None:
        return fallback
    return str(table["rows"][0][0])


def _done(
    steps,
    sql_result,
    answer,
    table,
    error: str,
    metric,
    executed_sql: str,
    dataset: dict,
    database,
    columns: list[str],
    scope: str,
    date_from: str = "",
    date_to: str = "",
) -> dict:
    calls = [item for item in (sql_result, answer) if item is not None]
    return {
        "steps": steps,
        "sql": "" if sql_result is None else sql_result.content,
        "executed_sql": executed_sql,
        "answer": "" if answer is None else answer.content,
        "table": table,
        "error": error,
        "status": "失败" if error else "成功",
        "request_count": len(calls),
        "input_tokens": sum(item.input_tokens for item in calls),
        "output_tokens": sum(item.output_tokens for item in calls),
        "metric_version": "" if metric is None else metric["version"],
        "data_date": _data_date(database, columns, dataset, scope, date_from, date_to),
    }
