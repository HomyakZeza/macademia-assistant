from ...extraction.models import RawLesson, StudentCells
from ..base import RecordRow
from ..registry import sheet_parser
from ..utils import to_float, merge_comments
from .generic import GenericParser


@sheet_parser(r"Русский 6")
class Russian6Parser(GenericParser):
    def _fill_lesson(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        if student.lesson.value.strip().lower() != "да" and not record.is_absent:
            record.lesson_grade = to_float(student.lesson.value)
        record.lesson_comment = merge_comments(student.lesson.comment, "")

    def _fill_homework(self, record: RecordRow, student: StudentCells, lesson: RawLesson) -> None:
        v = student.homework.value.strip().lower()
        gen_comment = ""

        if v == "есть":
            record.homework_grade = None
            gen_comment = "сдал"
        elif v in ("нет", "н"):
            record.homework_grade = 0.0
            gen_comment = "не сдал"
        else:
            record.homework_grade = to_float(student.homework.value)

        record.homework_comment = merge_comments(student.homework.comment, gen_comment)