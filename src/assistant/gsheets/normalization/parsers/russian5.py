from ...extraction.models import RawLesson, StudentCells
from ..base import RecordRow
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser
from .generic import GenericParser


@sheet_parser(r"Русский 5")
class Russian5Parser(GenericParser):
    def _fill_homework(
        self, record: RecordRow, student: StudentCells, lesson: RawLesson
    ) -> None:
        super()._fill_homework(record, student, lesson)
        if classify_color(student.homework.color) == ColorCategory.RED:
            record.homework_grade = 0
