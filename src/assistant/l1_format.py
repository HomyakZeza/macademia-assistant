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
class RawExport:
    meta: RawExportMeta
    class_level: Optional[str]
    subject: Optional[str]
    lessons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())