from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Cell:
    value: str = ""
    color: Optional[str] = None
    comment: str = ""


@dataclass
class RawStudent:
    name: str
    lesson: Cell = field(default_factory=Cell)
    homework: Cell = field(default_factory=Cell)
    test: Cell = field(default_factory=Cell)


@dataclass
class RawLesson:
    date: str
    topic: str
    homework: str
    lesson_seq: int = 1 # порядковый номер урока в дне
    additional_fields: dict = field(default_factory=dict)
    students: list = field(default_factory=list)


@dataclass
class RawExportMeta:
    schema_version: str
    source_spreadsheet_id: str
    source_sheet_name: str
    source_url: str
    exported_at: str
    parser_version: str


@dataclass
class ClassBlock:
    class_level: Optional[str]
    class_label: Optional[str]
    anchor_row: int
    anchor_col: int
    lessons: list = field(default_factory=list)


@dataclass
class SheetExport:
    sheet_name: str
    subject: str
    classes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkbookExport:
    meta: RawExportMeta
    sheets: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save(self, path: str) -> None:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_json(), encoding="utf-8")