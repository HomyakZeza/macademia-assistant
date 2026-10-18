import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    Cell, RawStudent, RawLesson, RawExport, RawExportMeta,
)


PARSER_VERSION = "0.2"
SCHEMA_VERSION = "1.0"

DATE_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
TITLE_RE = re.compile(r"^(.+?)\s+(\d+)\s*класс", re.IGNORECASE)

STUDENT_MARKER = "Урок"



def list_sheet_titles(spreadsheet_id: str, credentials_path: str) -> list[str]:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    result = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        includeGridData=False,
    ).execute()

    return [s["properties"]["title"] for s in result.get("sheets", [])]


def _resolve_sheet_name(requested: str, available: list[str]) -> str:
    if requested in available:
        return requested

    def norm(s: str) -> str:
        return s.strip().lower()

    for name in available:
        if norm(name) == norm(requested):
            return name

    available_list = "\n".join(f"  - {repr(n)}" for n in available)
    raise ValueError(
        f"Лист '{requested}' не найден в таблице.\n"
        f"Доступные листы:\n{available_list}"
    )


def read_sheet(spreadsheet_id: str, sheet_name: str, credentials_path: str):
    import httplib2
    from google.oauth2.service_account import Credentials
    from google_auth_httplib2 import AuthorizedHttp
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)

    http = httplib2.Http(decode_limit_ratio=500)
    auth_http = AuthorizedHttp(creds, http=http)
    service = build("sheets", "v4", http=auth_http, cache_discovery=False)

    available = list_sheet_titles(spreadsheet_id, credentials_path)
    sheet_name = _resolve_sheet_name(sheet_name, available)

    fields = (
        "sheets(data(rowData(values("
        "formattedValue,"
        "effectiveFormat(backgroundColor,backgroundColorStyle(rgbColor))"
        "))))"
    )

    result = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[f"'{sheet_name}'!A1:ZZ10000"],
        includeGridData=True,
        fields=fields,
    ).execute()

    sheets = result.get("sheets", [])
    if not sheets:
        raise ValueError(f"Лист '{sheet_name}' не вернул данных")

    grid = sheets[0].get("data", [{}])[0]
    rows = grid.get("rowData", [])

    values, colors = [], []
    for row in rows:
        vals, cols = [], []
        for cell in row.get("values", []):
            vals.append((cell.get("formattedValue") or "").strip())
            cols.append(_cell_color(cell))
        values.append(vals)
        colors.append(cols)

    return values, colors


def _cell_color(cell: dict) -> Optional[str]:
    fmt = cell.get("effectiveFormat") or {}
    rgb = None
    style = fmt.get("backgroundColorStyle")
    if style:
        rgb = style.get("rgbColor")
    if not rgb:
        rgb = fmt.get("backgroundColor")
    if not rgb:
        return None

    r = float(rgb.get("red", 1.0))
    g = float(rgb.get("green", 1.0))
    b = float(rgb.get("blue", 1.0))

    if abs(r - 1) < 0.01 and abs(g - 1) < 0.01 and abs(b - 1) < 0.01:
        return None

    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, int(round(r * 255)))),
        max(0, min(255, int(round(g * 255)))),
        max(0, min(255, int(round(b * 255)))),
    )



def _col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def _find_header_row(values) -> int:
    for i, row in enumerate(values):
        if row and row[0].strip().lower() == "дата":
            return i
    raise ValueError("Не найдена строка с 'Дата'")


def _parse_title(values):
    if not values or not values[0]:
        return None, None, ""
    title = values[0][0].strip()
    m = TITLE_RE.match(title)
    if m:
        return m.group(1).strip(), m.group(2), title
    return (title or None), None, title


def _find_student_starts(types_row) -> list:
    return [i for i, t in enumerate(types_row) if t.strip() == STUDENT_MARKER]


def _resolve_student_name(names_row, idx) -> str:
    if idx < len(names_row) and names_row[idx].strip():
        return names_row[idx].strip()
    for j in range(idx - 1, -1, -1):
        if j < len(names_row) and names_row[j].strip():
            return names_row[j].strip()
    return f"student_{idx}"


def _cell(row, idx):
    return row[idx] if 0 <= idx < len(row) else ""


def _parse_date(s: str) -> Optional[str]:
    m = DATE_RE.match(s.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    try:
        return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _additional_field_names(names_row, types_row, first_student_start) -> dict:
    fields = {}
    for idx in range(3, first_student_start):
        name = ""
        if idx < len(names_row) and names_row[idx].strip():
            name = names_row[idx].strip()
        elif idx < len(types_row) and types_row[idx].strip():
            name = types_row[idx].strip()
        if not name:
            name = _col_letter(idx)
        fields[idx] = name
    return fields


def parse_sheet(values, colors) -> RawExport:
    subject, class_level, raw_title = _parse_title(values)

    h1 = _find_header_row(values)
    h2 = h1 + 1
    if h2 >= len(values):
        raise ValueError("После строки 'Дата' нет строки с маркерами Урок/ДЗ/КР")

    names_row = values[h1]
    types_row = values[h2]

    starts = _find_student_starts(types_row)
    if not starts:
        raise ValueError("Не найдено ни одного 'Урок' в шапке")

    add_fields = _additional_field_names(names_row, types_row, starts[0])

    students_meta = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(types_row)
        block_len = end - start
        students_meta.append({
            "name": _resolve_student_name(names_row, start),
            "lesson_idx": start,
            "homework_idx": start + 1 if block_len >= 2 else None,
            "test_idx": start + 2 if block_len >= 3 else None,
        })

    export = RawExport(
        meta=RawExportMeta(
            schema_version=SCHEMA_VERSION,
            source_spreadsheet_id="",
            source_sheet_name=raw_title,
            source_url="",
            exported_at=datetime.now(timezone.utc).isoformat(),
            parser_version=PARSER_VERSION,
        ),
        class_level=class_level,
        subject=subject,
    )

    for r_idx in range(h2 + 1, len(values)):
        row = values[r_idx]
        if not row:
            continue

        date_iso = _parse_date(_cell(row, 0))
        if not date_iso:
            continue

        row_colors = colors[r_idx] if r_idx < len(colors) else []

        lesson = RawLesson(
            date=date_iso,
            topic=_cell(row, 1),
            homework=_cell(row, 2),
            additional_fields={
                name: _cell(row, idx) for idx, name in add_fields.items()
            },
        )

        for meta in students_meta:
            def make_cell(idx):
                if idx is None:
                    return Cell()
                return Cell(
                    value=_cell(row, idx),
                    color=_cell(row_colors, idx) or None,
                    comment="",
                )

            lesson.students.append(RawStudent(
                name=meta["name"],
                lesson=make_cell(meta["lesson_idx"]),
                homework=make_cell(meta["homework_idx"]),
                test=make_cell(meta["test_idx"]),
            ))

        export.lessons.append(lesson)

    return export



def run_etl_l1(
    spreadsheet_id: str,
    sheet_name: str,
    credentials_path: str,
    output_path: str,
) -> dict:
    values, colors = read_sheet(spreadsheet_id, sheet_name, credentials_path)
    export = parse_sheet(values, colors)

    export.meta.source_spreadsheet_id = spreadsheet_id
    export.meta.source_url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    export.save(output_path)

    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "class": export.class_level,
        "subject": export.subject,
        "lessons": len(export.lessons),
        "output_path": output_path,
    }