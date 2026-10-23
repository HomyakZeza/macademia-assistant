"""
- красный = не сдано / не зачтено
- оранжевый = зачтено с ошибками
- зелёный = зачтено, ошибок мало/нет
- серый = не задано
"""

from typing import Optional

from ...extraction.models import Cell, ClassBlock
from ..base import LessonRow, ParsedBlock, RecordRow, SheetParser
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser


CATEGORY_TO_GRADE = {
    ColorCategory.RED: 2,
    ColorCategory.ORANGE: 3,
    ColorCategory.GREEN: 5,
}


def _cell_to_grade(cell: Cell) -> Optional[float]:
    cat = classify_color(cell.color)
    if cat in CATEGORY_TO_GRADE:
        return float(CATEGORY_TO_GRADE[cat])

    if cell.value:
        try:
            return float(cell.value.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def _is_absent(cell: Cell) -> bool:
    return cell.value.strip().lower() == "н"


@sheet_parser(r"Русский 7-9")
class Russian79Parser(SheetParser):

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

                record.homework_grade = _cell_to_grade(st.homework)
                if not is_absent:
                    record.lesson_grade = _cell_to_grade(st.lesson)
                record.test_grade = _cell_to_grade(st.test)

                if (
                    record.is_absent
                    or record.lesson_grade is not None
                    or record.homework_grade is not None
                    or record.test_grade is not None
                ):
                    result.records.append(record)

        return result