from typing import Optional

from ...extraction.models import Cell, ClassBlock
from ..base import LessonRow, ParsedBlock, RecordRow, SheetParser
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser


CATEGORY_TO_GRADE = {
    ColorCategory.RED: 2,
    ColorCategory.ORANGE: 2,
    ColorCategory.YELLOW: 3,
    ColorCategory.BLUE: 4,
    ColorCategory.GREEN: 5,
}


def _cell_to_grade(cell: Cell) -> Optional[int]:
    return CATEGORY_TO_GRADE.get(classify_color(cell.color))


def _to_int(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        return int(float(value.replace(",", ".")))
    except (ValueError, AttributeError):
        return None


def _is_absent(cell: Cell) -> bool:
    return cell.value.strip().lower() == "н"


@sheet_parser(
    r"Математика.*",
    r"Алгебра.*",
    r"Геометрия.*",
    r"ТВиС.*",
)
class MathParser(SheetParser):

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

            total = _to_int(lesson.additional_fields.get("D", ""))

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

                hw_grade = _cell_to_grade(st.homework)
                if hw_grade is not None:
                    record.homework_grade = float(hw_grade)
                    completed = _to_int(st.homework.value)
                    if completed is not None and total is not None and total > 0:
                        record.homework_completed_percent = round(
                            completed / total * 100, 1
                        )
                        record.homework_comment = (
                            f"сделано {completed} из {total}"
                        )

                lw_grade = _cell_to_grade(st.lesson)
                if lw_grade is not None:
                    record.lesson_grade = float(lw_grade)

                test_grade = _to_int(st.test.value)
                if test_grade is not None:
                    record.test_grade = float(test_grade)
                    if is_absent:
                        record.test_comment = "переписал позже"

                if (
                    record.is_absent
                    or record.lesson_grade is not None
                    or record.homework_grade is not None
                    or record.test_grade is not None
                ):
                    result.records.append(record)

        return result