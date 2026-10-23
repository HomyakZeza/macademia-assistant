import re

from .base import SheetParser

_registry: list[tuple[re.Pattern, type[SheetParser]]] = []

def sheet_parser(*patterns: str):
    def decorator(cls: type[SheetParser]) -> type[SheetParser]:
        for pattern in patterns:
            _registry.append((re.compile(pattern), cls))
        return cls
    return decorator

def get_parser(sheet_name: str) -> SheetParser:
    for pattern, cls in _registry:
        if pattern.fullmatch(sheet_name):
            return cls()
    raise ValueError(f"Нет парсера для листа: {sheet_name!r}")

def list_registered() -> list[tuple[str, str]]:
    return [(p.pattern, c.__name__) for p, c in _registry]