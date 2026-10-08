import re
from datetime import date, datetime, timedelta

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_window(
    time_range: str, date_from: str = "", date_to: str = "", today: date | None = None
) -> tuple[str, str]:
    current = today or datetime.now().date()
    if time_range == "今天":
        day = current.isoformat()
        return day, day
    if time_range == "本周":
        start = current - timedelta(days=current.weekday())
        return start.isoformat(), current.isoformat()
    if time_range == "本月":
        return current.replace(day=1).isoformat(), current.isoformat()
    if time_range == "自定义":
        if not DATE.fullmatch(date_from or "") or not DATE.fullmatch(date_to or ""):
            raise ValueError("日期格式不正确")
        return date_from, date_to
    return "", ""
