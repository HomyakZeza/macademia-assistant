"""Инструменты MCP-сервера."""

from .students import list_children
from .grades import get_grades, get_summary
from .attendance import get_attendance

__all__ = [
    "list_children",
    "get_grades",
    "get_summary",
    "get_attendance",
]