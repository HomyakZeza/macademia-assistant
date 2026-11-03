from typing import Optional
from ...extraction.models import Cell, RawLesson, StudentCells
from ..base import RecordRow
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser
from ..utils import to_float, merge_comments
from .generic import GenericParser

CATEGORY_TO_GRADE = {
    ColorCategory.RED: 2,
    ColorCategory.ORANGE: 3,
    ColorCategory.GREEN: 5,
}

def _cell_to_grade(cell: Cell) -> Optional[float]:
    cat = classify_color(cell.color)
    if cat in CATEGORY_TO_GRADE:
        return float(CATEGORY_TO_GRADE[cat])
    return to_float(cell.value)

@sheet_parser(r"Русский 7-9")
class Russian79Parser(GenericParser):
    def _fill_lesson(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        if not record.is_absent:
            record.lesson_grade = _cell_to_grade(student.lesson)
        record.lesson_comment = merge_comments(student.lesson.comment, "")

    def _fill_homework(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        record.homework_grade = _cell_to_grade(student.homework)
        record.homework_comment = merge_comments(student.homework.comment, "")

    def _fill_test(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        record.test_grade = _cell_to_grade(student.test)
        record.test_comment = merge_comments(student.test.comment, "")