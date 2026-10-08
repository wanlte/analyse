def period_change(rows: list[tuple]) -> str:
    periods = [(str(period), float(amount)) for period, amount in rows]
    if len(periods) < 2:
        return "环比：没有上一期。同比：没有去年同期。"
    current_period, current = periods[-1]
    previous_period, previous = periods[-2]
    ratio = _ratio(current, previous)
    year_period = _last_year(current_period)
    yearly = next((amount for period, amount in periods if period == year_period), None)
    year_text = (
        f"同比：相对 {year_period} {_ratio(current, yearly)}"
        if yearly is not None
        else "同比：没有去年同期。"
    )
    return f"环比：{current_period} 相对 {previous_period} {ratio}。{year_text}"


def channel_contribution(rows: list[tuple]) -> str:
    items = [(str(name), float(amount)) for name, amount in rows]
    total = sum(amount for _, amount in items)
    if total == 0 or not items:
        return "维度贡献：没有可汇总的金额。"
    name, amount = max(items, key=lambda item: item[1])
    share = amount / total
    return f"维度贡献：{name} 占 {share:.0%}（{amount:g}/{total:g}）。"


def largest_gap(rows: list[tuple]) -> str:
    items = [(str(name), float(amount)) for name, amount in rows]
    if len(items) < 2:
        return "异常：分组不足，无法比较偏离。"
    average = sum(amount for _, amount in items) / len(items)
    name, amount = max(items, key=lambda item: abs(item[1] - average))
    return f"异常：{name} 为 {amount:g}，离均值 {average:g} 最远。"


def structure_shares(rows: list[tuple]) -> str:
    items = [(str(name), float(amount)) for name, amount in rows]
    total = sum(amount for _, amount in items)
    if total == 0:
        return "结构：金额合计为 0。"
    parts = [f"{name} {amount / total:.0%}" for name, amount in items]
    return "结构：" + "，".join(parts)


def _ratio(current: float, previous: float) -> str:
    if previous == 0:
        return "上一期为 0，无法计算比率"
    return f"{(current - previous) / previous:.0%}"


def _last_year(period: str) -> str:
    if "-W" in period:
        year, week = period.split("-W", 1)
        return f"{int(year) - 1}-W{week}"
    if "-Q" in period:
        year, quarter = period.split("-Q", 1)
        return f"{int(year) - 1}-Q{quarter}"
    year, rest = period.split("-", 1)
    return f"{int(year) - 1}-{rest}"


def keep_compare(text: str, compare: str) -> str:
    if "同比：" not in text:
        return text
    ring, _, year = text.partition("同比：")
    if compare == "同比":
        return "同比：" + year
    return ring.strip()
