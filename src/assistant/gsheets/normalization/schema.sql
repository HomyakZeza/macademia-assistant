PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id  TEXT,
    name         TEXT NOT NULL,
    class_level  TEXT NOT NULL,
    UNIQUE(name, class_level)
);

CREATE TABLE IF NOT EXISTS lessons (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT NOT NULL,
    class_level    TEXT NOT NULL,
    subject        TEXT NOT NULL,
    block_label    TEXT NOT NULL DEFAULT '',
    lesson_seq     INTEGER NOT NULL DEFAULT 1,
    topic          TEXT,
    homework_text  TEXT,
    UNIQUE(date, class_level, subject, block_label, lesson_seq)
);

CREATE TABLE IF NOT EXISTS records (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id                  INTEGER NOT NULL,
    lesson_id                   INTEGER NOT NULL,
    is_absent                   INTEGER NOT NULL DEFAULT 0,

    lesson_grade                REAL,
    lesson_comment              TEXT,

    homework_grade              REAL,
    homework_comment            TEXT,
    homework_completed_percent  REAL,

    test_grade                  REAL,
    test_comment                TEXT,

    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (lesson_id)  REFERENCES lessons(id),
    UNIQUE(student_id, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_records_student        ON records(student_id);
CREATE INDEX IF NOT EXISTS idx_records_lesson         ON records(lesson_id);
CREATE INDEX IF NOT EXISTS idx_lessons_subject_date   ON lessons(subject, date);
CREATE INDEX IF NOT EXISTS idx_lessons_date           ON lessons(date);
CREATE INDEX IF NOT EXISTS idx_students_name          ON students(name);
CREATE INDEX IF NOT EXISTS idx_students_class         ON students(class_level);