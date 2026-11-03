"""Общие утилиты для парсеров."""
from typing import Optional

def to_float(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None

def to_int(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        return int(float(value.replace(",", ".")))
    except (ValueError, AttributeError):
        return None

def merge_comments(native: str, generated: str) -> Optional[str]:
    native = (native or "").strip()
    generated = (generated or "").strip()

    if not native and not generated:
        return None
    if native == generated:
        return native

    return "\n".join(filter(None, [native, generated]))