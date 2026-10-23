"""
"есть" в ДЗ = проверила наличие, но без оценки
"нет" в ДЗ = не сдал
оценка в ДЗ = проверила выборочно и поставила
пусто + задание было + не absent = не сделал
"""

from typing import Optional

from ...extraction.models import Cell, ClassBlock
from ..base import LessonRow, ParsedBlock, RecordRow, SheetParser
from ..registry import sheet_parser


def _to_float(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _is_absent(cell: Cell) -> bool:
    return cell.value.strip().lower() == "н"


def _parse_homework(
    value: str,
    has_task: bool,
    is_absent: bool,
) -> tuple[Optional[float], Optional[str]]:
    v = value.strip().lower()

    if v == "есть":
        return None, "сдал"
    if v == "нет":
        return 0.0, "не сдал"
    if v == "н":
        return 0.0, "не сдал"

    num = _to_float(value)
    if num is not None:
        return num, None

    if has_task and not is_absent:
        return 0.0, None

    return None, None


@sheet_parser(r"Русский 6")
class Russian6Parser(SheetParser):

    def transform(self, block: ClassBlock, subject: str) -> ParsedBlock:
        result = ParsedBlock()
        class_level = block.class_level or ""
        block_label = block.class_label or ""

        for lesson in block.lessons:
            result.lessons.append(LessonRow(
                date=lesson.date,
                class_level=class_level,
                subject=subject,
                block_label=block_label,
                lesson_seq=lesson.lesson_seq,
                topic=lesson.topic or "",
                homework_text=lesson.homework or None,
            ))

            has_task = bool(lesson.homework and lesson.homework.strip())

            for st in lesson.students:
                is_absent = _is_absent(st.lesson)
                record = RecordRow(
                    student_name=st.name,
                    date=lesson.date,
                    class_level=class_level,
                    subject=subject,
                    block_label=block_label,
                    lesson_seq=lesson.lesson_seq,
                    is_absent=is_absent,
                )

                lesson_v = st.lesson.value.strip().lower()
                if lesson_v != "да" and not is_absent:
                    record.lesson_grade = _to_float(st.lesson.value)

                hw_grade, hw_comment = _parse_homework(
                    st.homework.value, has_task, is_absent,
                )
                record.homework_grade = hw_grade
                record.homework_comment = hw_comment

                record.test_grade = _to_float(st.test.value)

                if (
                    record.is_absent
                    or record.lesson_grade is not None
                    or record.homework_grade is not None
                    or record.test_grade is not None
                    or record.homework_comment
                ):
                    result.records.append(record)

        return result