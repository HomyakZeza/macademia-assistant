from ..base import LessonRow, ParsedBlock, RecordRow, SheetParser, StudentCommentRow
from ..utils import to_float, merge_comments
from ...extraction.models import Cell, ClassBlock, RawLesson, StudentCells
from ..registry import sheet_parser


class GenericParser(SheetParser):
    def transform(self, block: ClassBlock, subject: str) -> ParsedBlock:
        result = ParsedBlock()
        class_level, block_label = block.class_level or "", block.class_label or ""

        for name, info in block.students_info.items():
            for c in info.comments:
                result.comments.append(
                    StudentCommentRow(
                        student_name=name,
                        class_level=class_level,
                        subject=subject,
                        date=c.date,
                        text=c.text,
                    )
                )

        for lesson in block.lessons:
            result.lessons.append(
                LessonRow(
                    date=lesson.date,
                    class_level=class_level,
                    subject=subject,
                    block_label=block_label,
                    lesson_seq=lesson.lesson_seq,
                    topic=lesson.topic or "",
                    homework_text=lesson.homework or None,
                )
            )

            for student in lesson.students:
                if student.lesson.value.strip() == "#":
                    continue

                record = RecordRow(
                    student_name=student.student_name,
                    date=lesson.date,
                    class_level=class_level,
                    subject=subject,
                    block_label=block_label,
                    lesson_seq=lesson.lesson_seq,
                    is_absent=self._get_is_absent(student.lesson),
                )

                self._fill_lesson(record, student, lesson)
                self._fill_homework(record, student, lesson)
                self._fill_test(record, student, lesson)

                result.records.append(record)

        return result

    def _get_is_absent(self, cell: Cell) -> bool:
        return cell.value.strip().lower() in ("н", "н.", "h")

    def _fill_lesson(
        self, record: RecordRow, student: StudentCells, lesson: RawLesson
    ) -> None:
        record.lesson_grade = to_float(student.lesson.value)
        record.lesson_comment = merge_comments(student.lesson.comment, "")

    def _fill_homework(
        self, record: RecordRow, student: StudentCells, lesson: RawLesson
    ) -> None:
        record.homework_grade = to_float(student.homework.value)
        record.homework_comment = merge_comments(student.homework.comment, "")

    def _fill_test(
        self, record: RecordRow, student: StudentCells, lesson: RawLesson
    ) -> None:
        record.test_grade = to_float(student.test.value)
        record.test_comment = merge_comments(student.test.comment, "")
