import re
from typing import Optional

from .models import (
    Cell, RawStudent, RawLesson, SheetExport, ClassBlock,
)
from .xlsx_reader import SheetMatrix


CLASS_RE = re.compile(r"\b(\d+)\s*класс", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STUDENT_MARKER = "Урок"

def _col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result

def find_anchors(matrix: SheetMatrix) -> list[tuple[int, int]]:
    anchors = []
    for r_idx, row in enumerate(matrix.rows):
        for c_idx, cell in enumerate(row):
            if cell.value.strip().lower() == "дата":
                anchors.append((r_idx, c_idx))
    return anchors


def find_bounds(
    matrix: SheetMatrix,
    anchors: list[tuple[int, int]],
    r: int,
    c: int,
) -> tuple[int, int]:
    rows = len(matrix.rows)
    cols = len(matrix.rows[r]) if rows else 0

    right = cols - 1
    for r2, c2 in anchors:
        if r2 == r and c2 > c:
            right = min(right, c2 - 1)

    bottom = rows - 1
    for r2, c2 in anchors:
        if c2 == c and r2 > r:
            bottom = min(bottom, r2 - 1)

    return right, bottom


def find_class_label(
    matrix: SheetMatrix,
    r: int,
    c: int,
) -> tuple[Optional[str], Optional[str]]:
    for dr in (1, 2, 3, 4):
        row_idx = r - dr
        if row_idx < 0:
            continue
        for dc in (0, -1, 1, -2, 2):
            col_idx = c + dc
            if col_idx < 0 or col_idx >= len(matrix.rows[row_idx]):
                continue
            v = matrix.rows[row_idx][col_idx].value.strip()
            if not v:
                continue
            m = CLASS_RE.search(v)
            if m:
                return m.group(1), v
    return None, None


def _resolve_student_name(row: list[Cell], idx: int) -> str:
    if idx < len(row) and row[idx].value.strip():
        return row[idx].value.strip()
    for j in range(idx - 1, -1, -1):
        if j < len(row) and row[j].value.strip():
            return row[j].value.strip()
    return f"student_{idx}"

def _detect_block_format(
    types_row: list[Cell],
    start: int,
    end: int,
) -> str:

    markers = set()
    for i in range(start, min(end + 1, len(types_row))):
        v = types_row[i].value.strip()
        if v:
            markers.add(v)
    if "Урок" in markers:
        return "standard"
    if "ДЗ" in markers:
        return "oge"
    return "unknown"

def _find_student_starts(
    types_row: list[Cell],
    start: int,
    end: int,
    block_format: str,
) -> list[tuple[int, dict]]:
    hits: list[tuple[int, dict]] = []

    if block_format == "standard":
        for i in range(start, min(end + 1, len(types_row))):
            if types_row[i].value.strip() == "Урок":
                hits.append((i, {
                    "lesson": i,
                    "homework": i + 1,
                    "test": i + 2,
                }))
    elif block_format == "oge":
        for i in range(start, min(end + 1, len(types_row))):
            if types_row[i].value.strip() == "ДЗ":
                hits.append((i, {
                    "homework": i,
                    "comment": i + 1,
                }))

    return hits


def _parse_block(
    matrix: SheetMatrix,
    r: int,
    c: int,
    right: int,
    bottom: int,
) -> list[RawLesson]:

    if r + 1 >= len(matrix.rows):
        return []

    names_row = matrix.rows[r]
    types_row = matrix.rows[r + 1]

    block_format = _detect_block_format(types_row, c, right)
    if block_format == "unknown":
        return []

    starts = _find_student_starts(types_row, c, right, block_format)
    if not starts:
        return []

    students_meta = []
    for i, (start_idx, cols) in enumerate(starts):
        students_meta.append({
            "name": _resolve_student_name(names_row, start_idx),
            "columns": cols,
        })

    lessons: list[RawLesson] = []

    first_student_idx = min(start_idx for start_idx, _ in starts)
    additional_cols: dict[int, str] = {}
    for idx in range(c + 3, first_student_idx):
        additional_cols[idx] = _col_letter(idx)

    for r_idx in range(r + 2, bottom + 1):
        row = matrix.rows[r_idx]
        date_value = row[c].value.strip() if c < len(row) else ""

        if not DATE_RE.match(date_value):
            continue

        def cell_at(idx):
            if idx is None or idx >= len(row):
                return Cell()
            return row[idx]

        additional = {
            name: cell_at(idx).value
            for idx, name in additional_cols.items()
        }

        lesson = RawLesson(
            date=date_value,
            topic=cell_at(c + 1).value,
            homework=cell_at(c + 2).value,
            additional_fields=additional,
        )

        for meta in students_meta:
            cols = meta["columns"]
            lesson_cell = cell_at(cols.get("lesson")) if "lesson" in cols else Cell()
            hw_cell = cell_at(cols.get("homework"))
            test_cell = cell_at(cols.get("test")) if "test" in cols else Cell()

            if "comment" in cols:
                comment_cell = cell_at(cols["comment"])
                hw_cell = Cell(
                    value=hw_cell.value,
                    color=hw_cell.color,
                    comment=comment_cell.value,
                )

            lesson.students.append(RawStudent(
                name=meta["name"],
                lesson=lesson_cell,
                homework=hw_cell,
                test=test_cell,
            ))

        lessons.append(lesson)

    return lessons



def extract_sheet(
    matrix: SheetMatrix,
    subject: str,
) -> SheetExport:
    anchors = find_anchors(matrix)
    if not anchors:
        return SheetExport(sheet_name=matrix.name, subject=subject)

    export = SheetExport(sheet_name=matrix.name, subject=subject)

    anchors_sorted = sorted(anchors, key=lambda x: (x[0], x[1]))

    for i, (r, c) in enumerate(anchors_sorted):
        right, bottom = find_bounds(matrix, anchors, r, c)

        if i == 0:
            a1 = matrix.rows[0][0].value.strip() if matrix.rows else ""
            m = CLASS_RE.search(a1)
            if m:
                class_level, class_label = m.group(1), a1
            else:
                class_level, class_label = find_class_label(matrix, r, c)
        else:
            class_level, class_label = find_class_label(matrix, r, c)

        lessons = _parse_block(matrix, r, c, right, bottom)

        export.classes.append(ClassBlock(
            class_level=class_level,
            class_label=class_label,
            anchor_row=r + 1,
            anchor_col=c + 1,
            lessons=lessons,
        ))

    return export