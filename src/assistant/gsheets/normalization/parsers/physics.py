from ...extraction.models import RawLesson, StudentCells
from ..base import RecordRow
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser
from ..utils import to_float, merge_comments
from .generic import GenericParser

CATEGORY_TO_COMMENT = {
    ColorCategory.GREEN: "всё хорошо",
    ColorCategory.YELLOW: "есть вопросы",
    ColorCategory.ORANGE: "требует доработки",
    ColorCategory.RED: "всё плохо",
}


@sheet_parser(r"Физика.*")
class PhysicsParser(GenericParser):
    def _fill_lesson(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        record.lesson_comment = merge_comments(student.lesson.comment, "")

    def _fill_homework(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        hw_value = to_float(student.homework.value)
        if hw_value is not None:
            if hw_value <= 1.0:
                percent = hw_value * 100
            else:
                percent = hw_value
            record.homework_completed_percent = round(percent, 1)

        gen_comment = CATEGORY_TO_COMMENT.get(classify_color(student.homework.color), "")
        record.homework_comment = merge_comments(student.homework.comment, gen_comment)

    def _fill_test(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        record.test_grade = to_float(student.test.value)
        gen_comment = CATEGORY_TO_COMMENT.get(classify_color(student.test.color), "")
        record.test_comment = merge_comments(student.test.comment, gen_comment)