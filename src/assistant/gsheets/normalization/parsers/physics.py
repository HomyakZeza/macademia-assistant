from typing import Optional
from ...extraction.models import Cell, ClassBlock
from ..base import LessonRow, ParsedBlock, RecordRow, SheetParser, StudentCommentRow
from ..colors import ColorCategory, classify_color
from ..registry import sheet_parser

CATEGORY_TO_COMMENT = {
    ColorCategory.GREEN: "всё хорошо", ColorCategory.YELLOW: "есть вопросы",
    ColorCategory.ORANGE: "требует доработки", ColorCategory.RED: "всё плохо",
}


def _cell_to_comment(cell: Cell) -> Optional[str]:
    return CATEGORY_TO_COMMENT.get(classify_color(cell.color))


def _to_float(value: str) -> Optional[float]:
    if not value: return None
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _is_absent(cell: Cell) -> bool:
    return cell.value.strip().lower() == "н"


def _merge_comments(native: str, generated: Optional[str]) -> Optional[str]:
    parts = [p for p in (native, generated) if p]
    return "\n".join(parts) if parts else None


@sheet_parser(r"Физика.*")
class PhysicsParser(SheetParser):
    def transform(self, block: ClassBlock, subject: str) -> ParsedBlock:
        result = ParsedBlock()
        class_level = block.class_level or ""
        block_label = block.class_label or ""

        for lesson in block.lessons:
            result.lessons.append(LessonRow(
                date=lesson.date, class_level=class_level, subject=subject,
                block_label=block_label, lesson_seq=lesson.lesson_seq,
                topic=lesson.topic or "", homework_text=lesson.homework or None,
            ))

            for st in lesson.students:
                if st.comment:
                    result.comments.append(StudentCommentRow(
                        student_name=st.name, class_level=class_level, subject=subject,
                        date=st.comment_date, text=st.comment
                    ))

                if st.lesson.value.strip() == "#":
                    continue

                record = RecordRow(
                    student_name=st.name, date=lesson.date, class_level=class_level,
                    subject=subject, block_label=block_label, lesson_seq=lesson.lesson_seq,
                    is_absent=_is_absent(st.lesson),
                )

                hw_value = _to_float(st.homework.value)
                if hw_value is not None:
                    percent = hw_value * 100 if hw_value <= 1.0 else hw_value
                    record.homework_completed_percent = round(percent, 1)
                record.homework_comment = _merge_comments(st.homework.comment, _cell_to_comment(st.homework))

                record.test_grade = _to_float(st.test.value)
                record.test_comment = _merge_comments(st.test.comment, _cell_to_comment(st.test))

                record.lesson_comment = st.lesson.comment or None

                result.records.append(record)

        return result