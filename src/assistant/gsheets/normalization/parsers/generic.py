"""
Нет особенностей
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
    return cell.value.strip().lower() in ("н", "н.")


@sheet_parser(r".*")
class GenericParser(SheetParser):

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

            for st in lesson.students:
                record = RecordRow(
                    student_name=st.name,
                    date=lesson.date,
                    class_level=class_level,
                    subject=subject,
                    block_label=block_label,
                    lesson_seq=lesson.lesson_seq,
                    is_absent=_is_absent(st.lesson),
                )

                record.lesson_grade = _to_float(st.lesson.value)
                record.lesson_comment = st.lesson.comment or None

                record.homework_grade = _to_float(st.homework.value)
                record.homework_comment = st.homework.comment or None

                record.test_grade = _to_float(st.test.value)
                record.test_comment = st.test.comment or None

                if (
                    record.is_absent
                    or record.lesson_grade is not None
                    or record.homework_grade is not None
                    or record.test_grade is not None
                    or record.lesson_comment
                    or record.homework_comment
                    or record.test_comment
                ):
                    result.records.append(record)

        return result