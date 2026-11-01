from typing import Optional
from ...extraction.models import Cell, ClassBlock
from ..base import LessonRow, ParsedBlock, RecordRow, SheetParser, StudentCommentRow
from ..registry import sheet_parser

def _to_float(value: str) -> Optional[float]:
    if not value: return None
    try: return float(value.replace(",", "."))
    except (ValueError, AttributeError): return None

def _is_absent(cell: Cell) -> bool:
    return cell.value.strip().lower() == "н"

def _parse_homework(value: str) -> tuple[Optional[float], Optional[str]]:
    v = value.strip().lower()
    if v == "есть": return None, "сдал"
    if v in ("нет", "н"): return 0.0, "не сдал"
    num = _to_float(value)
    if num is not None: return num, None
    return None, None # Пустая ячейка - не смотрели

@sheet_parser(r"Русский 6")
class Russian6Parser(SheetParser):
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

                lesson_v = st.lesson.value.strip().lower()
                if lesson_v != "да" and not record.is_absent:
                    record.lesson_grade = _to_float(st.lesson.value)
                record.lesson_comment = st.lesson.comment or None

                record.homework_grade, gen_hw_comment = _parse_homework(st.homework.value)
                native_hw = st.homework.comment or ""
                record.homework_comment = "\n".join([p for p in (native_hw, gen_hw_comment) if p]) or None

                record.test_grade = _to_float(st.test.value)
                record.test_comment = st.test.comment or None

                result.records.append(record)

        return result