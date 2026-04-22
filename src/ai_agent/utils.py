from __future__ import annotations

from datetime import date, timedelta

from .models import Priority, TaskStatus


PRIORITY_ALIASES = {
    "\u4f4e": Priority.LOW,
    "low": Priority.LOW,
    "l": Priority.LOW,
    "\u4e2d": Priority.MEDIUM,
    "medium": Priority.MEDIUM,
    "m": Priority.MEDIUM,
    "\u9ad8": Priority.HIGH,
    "high": Priority.HIGH,
    "h": Priority.HIGH,
    "\u7d27\u6025": Priority.URGENT,
    "urgent": Priority.URGENT,
    "u": Priority.URGENT,
}

STATUS_ALIASES = {
    "todo": TaskStatus.TODO,
    "\u5f85\u529e": TaskStatus.TODO,
    "\u8fdb\u884c\u4e2d": TaskStatus.TODO,
    "done": TaskStatus.DONE,
    "\u5df2\u5b8c\u6210": TaskStatus.DONE,
    "\u5b8c\u6210": TaskStatus.DONE,
}


def parse_priority(text: str | None, default: Priority = Priority.MEDIUM) -> Priority:
    if not text:
        return default
    return PRIORITY_ALIASES.get(text.strip().lower(), default)


def parse_status(text: str | None) -> TaskStatus | None:
    if not text:
        return None
    return STATUS_ALIASES.get(text.strip().lower())


def normalize_tags(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item.strip() for item in raw if item.strip()]
    separators = [",", "\uff0c", ";", "\uff1b", " "]
    values = [raw]
    for sep in separators:
        split_values: list[str] = []
        for item in values:
            split_values.extend(item.split(sep))
        values = split_values
    return [item.strip() for item in values if item.strip()]


def parse_natural_date(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip().lower()
    today = date.today()

    if text in {"\u4eca\u5929", "today"}:
        return today.isoformat()
    if text in {"\u660e\u5929", "tomorrow"}:
        return (today + timedelta(days=1)).isoformat()
    if text in {"\u540e\u5929"}:
        return (today + timedelta(days=2)).isoformat()
    if text in {"\u4e0b\u5468", "next week"}:
        return (today + timedelta(days=7)).isoformat()

    try:
        if len(text) == 10:
            return date.fromisoformat(text).isoformat()
    except ValueError:
        return None
    return None


def safe_float(raw: str | float | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (float, int)):
        return float(raw)
    cleaned = raw.strip().lower().replace("\u5c0f\u65f6", "").replace("h", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

