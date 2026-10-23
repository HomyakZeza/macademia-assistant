from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ..extraction.models import ClassBlock


@dataclass
class LessonRow:
    date: str
    class_level: str
    subject: str
    block_label: str
    lesson_seq: int
    topic: str
    homework_text: Optional[str]


@dataclass
class RecordRow:
    student_name: str
    date: str
    class_level: str
    subject: str
    block_label: str
    lesson_seq: int

    is_absent: bool = False

    lesson_grade: Optional[float] = None
    lesson_comment: Optional[str] = None

    homework_grade: Optional[float] = None
    homework_comment: Optional[str] = None
    homework_completed_percent: Optional[float] = None

    test_grade: Optional[float] = None
    test_comment: Optional[str] = None


@dataclass
class ParsedBlock:
    lessons: list[LessonRow] = field(default_factory=list)
    records: list[RecordRow] = field(default_factory=list)


class SheetParser(ABC):

    @abstractmethod
    def transform(self, block: ClassBlock, subject: str) -> ParsedBlock:
        ...