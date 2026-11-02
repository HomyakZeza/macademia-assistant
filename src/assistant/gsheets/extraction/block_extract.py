import re
from typing import Optional
from openpyxl.utils import get_column_letter
from .models import Cell, RawStudentInfo, StudentCells, StudentComment, RawLesson, SheetExport, ClassBlock
from .xlsx_reader import SheetMatrix

CLASS_RE = re.compile(r"\b(\d+)\s*класс", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STUDENT_MARKER = "Урок"
OGE_MARKER = "ДЗ"


def _col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def find_anchors(matrix: SheetMatrix) -> list[tuple[int, int]]:
    return [(r, c) for r, row in enumerate(matrix.rows) for c, cell in enumerate(row) if
            cell.value.strip().lower() == "дата"]


def find_bounds(matrix: SheetMatrix, anchors: list[tuple[int, int]], r: int, c: int) -> tuple[int, int]:
    right = (len(matrix.rows[r]) if matrix.rows else 0) - 1
    for r2, c2 in anchors:
        if r2 == r and c2 > c: right = min(right, c2 - 1)
    bottom = len(matrix.rows) - 1
    for r2, c2 in anchors:
        if c2 == c and r2 > r: bottom = min(bottom, r2 - 1)
    return right, bottom


def find_class_label(matrix: SheetMatrix, r: int, c: int) -> tuple[Optional[str], Optional[str]]:
    for dr in (1, 2, 3, 4):
        row_idx = r - dr
        if row_idx < 0: continue
        for dc in (0, -1, 1, -2, 2):
            col_idx = c + dc
            if col_idx < 0 or col_idx >= len(matrix.rows[row_idx]): continue
            v = matrix.rows[row_idx][col_idx].value.strip()
            m = CLASS_RE.search(v) if v else None
            if m: return m.group(1), v
    return None, None


def _detect_block_format(types_row: list[Cell], start: int, end: int) -> str:
    markers = {types_row[i].value.strip() for i in range(start, min(end + 1, len(types_row))) if
               types_row[i].value.strip()}
    if STUDENT_MARKER in markers: return "standard"
    if OGE_MARKER in markers: return "oge"
    return "unknown"


def _find_student_starts(types_row: list[Cell], start: int, end: int, fmt: str) -> list[tuple[int, dict]]:
    hits = []
    if fmt == "standard":
        for i in range(start, min(end + 1, len(types_row))):
            if types_row[i].value.strip() == STUDENT_MARKER:
                hits.append((i, {"lesson": i, "homework": i + 1, "test": i + 2}))
    elif fmt == "oge":
        for i in range(start, min(end + 1, len(types_row))):
            if types_row[i].value.strip() == OGE_MARKER:
                hits.append((i, {"homework": i, "comment": i + 1}))
    return hits


def _resolve_student_name(row: list[Cell], idx: int) -> str:
    if idx < len(row) and row[idx].value.strip(): return row[idx].value.strip()
    for j in range(idx - 1, -1, -1):
        if j < len(row) and row[j].value.strip(): return row[j].value.strip()
    return f"student_{idx}"


def _parse_block(matrix: SheetMatrix, r: int, c: int, right: int, bottom: int) -> tuple[
    dict[str, RawStudentInfo], list[RawLesson]]:
    if r + 1 >= len(matrix.rows): return {}, []
    names_row, types_row = matrix.rows[r], matrix.rows[r + 1]
    fmt = _detect_block_format(types_row, c, right)
    starts = _find_student_starts(types_row, c, right, fmt)
    if not starts: return {}, []

    students_info = {}
    students_meta = []

    for start_idx, cols in starts:
        name = _resolve_student_name(names_row, start_idx)
        cell_ref = f"{get_column_letter(start_idx + 1)}{r + 1}"

        raw_comments = matrix.threaded_comments.get(cell_ref, [])
        comments = [StudentComment(date=d, text=t) for d, t in raw_comments]

        if not comments:
            name_cell = names_row[start_idx] if start_idx < len(names_row) else Cell()
            if name_cell.comment:
                comments = [StudentComment(date=name_cell.comment_date, text=name_cell.comment)]

        students_info[name] = RawStudentInfo(name=name, comments=comments)
        students_meta.append({"name": name, "columns": cols})

    first_student_idx = min(idx for idx, _ in starts)
    additional_cols = {idx: _col_letter(idx) for idx in range(c + 3, first_student_idx)}

    lessons, date_counters = [], {}

    for r_idx in range(r + 2, bottom + 1):
        row = matrix.rows[r_idx]
        date_value = row[c].value.strip() if c < len(row) else ""
        if not DATE_RE.match(date_value): continue

        date_counters[date_value] = date_counters.get(date_value, 0) + 1
        lesson_seq = date_counters[date_value]

        def cell_at(idx):
            return row[idx] if idx is not None and idx < len(row) else Cell()

        lesson = RawLesson(
            date=date_value, topic=cell_at(c + 1).value, homework=cell_at(c + 2).value,
            lesson_seq=lesson_seq, additional_fields={name: cell_at(idx).value for idx, name in additional_cols.items()}
        )

        for meta in students_meta:
            cols = meta["columns"]
            lesson_cell = cell_at(cols.get("lesson")) if "lesson" in cols else Cell()
            hw_cell = cell_at(cols.get("homework"))
            test_cell = cell_at(cols.get("test")) if "test" in cols else Cell()

            if "comment" in cols:
                hw_cell = Cell(value=hw_cell.value, color=hw_cell.color, comment=cell_at(cols["comment"]).value)

            lesson.students.append(StudentCells(
                student_name=meta["name"], lesson=lesson_cell, homework=hw_cell, test=test_cell
            ))
        lessons.append(lesson)

    return students_info, lessons


def extract_sheet(matrix: SheetMatrix, subject: str) -> SheetExport:
    anchors = find_anchors(matrix)
    if not anchors: return SheetExport(sheet_name=matrix.name, subject=subject)

    export = SheetExport(sheet_name=matrix.name, subject=subject)
    for i, (r, c) in enumerate(sorted(anchors, key=lambda x: (x[0], x[1]))):
        right, bottom = find_bounds(matrix, anchors, r, c)
        if i == 0:
            m = CLASS_RE.search(matrix.rows[0][0].value.strip() if matrix.rows else "")
            class_level, class_label = (m.group(1), matrix.rows[0][0].value.strip()) if m else find_class_label(matrix,
                                                                                                                r, c)
        else:
            class_level, class_label = find_class_label(matrix, r, c)

        students_info, lessons = _parse_block(matrix, r, c, right, bottom)

        export.classes.append(ClassBlock(
            class_level=class_level, class_label=class_label,
            anchor_row=r + 1, anchor_col=c + 1,
            students_info=students_info, lessons=lessons
        ))
    return export