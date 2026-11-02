from typing import Optional
from ...extraction.models import Cell, RawLesson, StudentCells
from ..base import RecordRow
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser
from ..utils import to_int, merge_comments
from .generic import GenericParser

CATEGORY_TO_GRADE = {
    ColorCategory.RED: 2, ColorCategory.ORANGE: 2,
    ColorCategory.YELLOW: 3, ColorCategory.BLUE: 4, ColorCategory.GREEN: 5,
}


@sheet_parser(r"Математика.*", r"Алгебра.*", r"Геометрия.*", r"ТВиС.*")
class MathParser(GenericParser):
    def _get_is_absent(self, cell: Cell) -> bool:
        return cell.value.strip().lower() == "н"

    def _fill_homework(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        hw_grade = CATEGORY_TO_GRADE.get(classify_color(student.homework.color))
        if hw_grade is not None:
            record.homework_grade = float(hw_grade)
            completed = to_int(student.homework.value)
            total = to_int(lesson.additional_fields.get("D", ""))
            if completed is not None and total is not None and total > 0:
                record.homework_completed_percent = round(completed / total * 100, 1)
                record.homework_comment = merge_comments(student.homework.comment, f"{completed} из {total}")
            else:
                record.homework_comment = merge_comments(student.homework.comment, "")
        else:
            record.homework_comment = merge_comments(student.homework.comment, "")

    def _fill_lesson(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        lw_grade = CATEGORY_TO_GRADE.get(classify_color(student.lesson.color))
        if lw_grade is not None:
            record.lesson_grade = float(lw_grade)
        record.lesson_comment = merge_comments(student.lesson.comment, "")

    def _fill_test(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        test_grade = to_int(student.test.value)
        if test_grade is not None:
            record.test_grade = float(test_grade)

        gen_comment = "переписано позже" if record.is_absent and test_grade is not None else ""
        record.test_comment = merge_comments(student.test.comment, gen_comment)