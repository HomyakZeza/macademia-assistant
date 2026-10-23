import os
import sqlite3
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional

from .base import ParsedBlock


class StudentIdResolver(ABC):
    @abstractmethod
    def resolve(self, name: str, class_level: str) -> Optional[str]:
        ...


class NullResolver(StudentIdResolver):
    def resolve(self, name: str, class_level: str) -> Optional[str]:
        return None


def _init_db(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema)


def load_to_sqlite(
    parsed_blocks: Iterable[ParsedBlock],
    db_path: str,
    resolver: Optional[StudentIdResolver] = None,
) -> dict:
    resolver = resolver or NullResolver()

    db_path_obj = Path(db_path)
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=".loading_", suffix=".db", dir=str(db_path_obj.parent)
    )
    os.close(fd)

    counts = {
        "lessons": 0, "students": 0, "records": 0,
        "grades": 0, "absent": 0,
        "missing_student": 0, "missing_lesson": 0,
        "duplicate_record": 0,
    }
    duplicate_examples: list[tuple] = []

    try:
        conn = sqlite3.connect(tmp_name)
        try:
            _init_db(conn)

            seen_lessons = set()
            lesson_rows = []
            for block in parsed_blocks:
                for lesson in block.lessons:
                    key = (
                        lesson.date,
                        lesson.class_level,
                        lesson.subject,
                        lesson.block_label,
                        lesson.lesson_seq,
                    )
                    if key in seen_lessons:
                        continue
                    seen_lessons.add(key)
                    lesson_rows.append(lesson)

            for lesson in lesson_rows:
                conn.execute(
                    """INSERT INTO lessons
                       (date, class_level, subject, block_label,
                        lesson_seq, topic, homework_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (lesson.date, lesson.class_level, lesson.subject,
                     lesson.block_label, lesson.lesson_seq,
                     lesson.topic, lesson.homework_text),
                )
            counts["lessons"] = len(lesson_rows)

            lesson_id_map = {}
            for row in conn.execute(
                "SELECT id, date, class_level, subject, block_label, lesson_seq "
                "FROM lessons"
            ):
                lesson_id_map[
                    (row[1], row[2], row[3], row[4], row[5])
                ] = row[0]

            all_students = {}
            for block in parsed_blocks:
                for rec in block.records:
                    key = (rec.student_name, rec.class_level)
                    if key not in all_students:
                        all_students[key] = resolver.resolve(*key)

            for (name, class_level), external_id in all_students.items():
                conn.execute(
                    """INSERT INTO students (external_id, name, class_level)
                       VALUES (?, ?, ?)""",
                    (external_id, name, class_level),
                )
            counts["students"] = len(all_students)

            student_id_map = {}
            for row in conn.execute(
                "SELECT id, name, class_level FROM students"
            ):
                student_id_map[(row[1], row[2])] = row[0]

            seen_records: set[tuple[int, int]] = set()

            for block in parsed_blocks:
                for rec in block.records:
                    sid = student_id_map.get(
                        (rec.student_name, rec.class_level)
                    )
                    if sid is None:
                        counts["missing_student"] += 1
                        continue

                    lid = lesson_id_map.get(
                        (rec.date, rec.class_level, rec.subject,
                         rec.block_label, rec.lesson_seq)
                    )
                    if lid is None:
                        counts["missing_lesson"] += 1
                        continue

                    key = (sid, lid)
                    if key in seen_records:
                        counts["duplicate_record"] += 1
                        if len(duplicate_examples) < 10:
                            duplicate_examples.append((
                                rec.student_name, rec.class_level,
                                rec.date, rec.subject,
                                rec.block_label, rec.lesson_seq,
                            ))
                        continue
                    seen_records.add(key)

                    conn.execute(
                        """INSERT OR IGNORE INTO records
                           (student_id, lesson_id, is_absent,
                            lesson_grade, lesson_comment,
                            homework_grade, homework_comment,
                            homework_completed_percent,
                            test_grade, test_comment)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (sid, lid,
                         int(rec.is_absent),
                         rec.lesson_grade, rec.lesson_comment,
                         rec.homework_grade, rec.homework_comment,
                         rec.homework_completed_percent,
                         rec.test_grade, rec.test_comment),
                    )
                    counts["records"] += 1
                    if rec.is_absent:
                        counts["absent"] += 1
                    for g in (rec.lesson_grade,
                              rec.homework_grade,
                              rec.test_grade):
                        if g is not None:
                            counts["grades"] += 1

            conn.commit()
        finally:
            conn.close()

        os.replace(tmp_name, db_path)
    except Exception:
        if Path(tmp_name).exists():
            Path(tmp_name).unlink()
        raise

    counts["duplicate_examples"] = duplicate_examples
    return counts