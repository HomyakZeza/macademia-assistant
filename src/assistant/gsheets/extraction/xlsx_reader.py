import io
import re
import warnings
import zipfile
import posixpath
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from .models import Cell

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl.worksheet._reader")

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_THREADED_PREFIX = re.compile(r"^\[Threaded comment\].*?Comment:\s*", re.DOTALL)


@dataclass
class SheetMatrix:
    name: str
    rows: list[list[Cell]]
    threaded_comments: dict[str, list[tuple[str, str]]] = field(default_factory=dict)


def download_xlsx(spreadsheet_id: str, credentials_path: str, max_retries: int = 5) -> bytes:
    import socket, ssl, time
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    creds = Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return drive.files().export_media(fileId=spreadsheet_id, mimeType=XLSX_MIME).execute()
        except HttpError as e:
            if e.resp.status < 500 or attempt == max_retries:
                raise
            last_error = e
            reason = f"HTTP {e.resp.status}"
        except (TimeoutError, socket.timeout, ssl.SSLError) as e:
            if attempt == max_retries:
                raise
            last_error = e
            reason = f"сетевая ошибка ({type(e).__name__})"

        delay = 2 ** (attempt - 1)
        print(f"  {reason}, попытка {attempt}/{max_retries}, повтор через {delay} сек...")
        time.sleep(delay)
    raise last_error


def _extract_value(cell) -> str:
    v = cell.value
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return str(v)
    if isinstance(v, int):
        return str(v)
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def _extract_color(cell) -> Optional[str]:
    fill = cell.fill
    if not fill or fill.patternType is None:
        return None

    color = getattr(fill, "start_color", None) or getattr(fill, "fgColor", None)
    if color is None:
        return None

    rgb = color.rgb
    if not isinstance(rgb, str):
        return None

    if len(rgb) == 8:
        if rgb in ("FFFFFFFF", "00FFFFFF"):
            return None
        return f"#{rgb[2:4]}{rgb[4:6]}{rgb[6:8]}".upper()

    if len(rgb) == 6:
        if rgb.upper() == "FFFFFF":
            return None
        return f"#{rgb}".upper()

    return None


def _extract_comment(cell) -> tuple[str, str]:
    if not cell.comment:
        return "", ""

    text = _THREADED_PREFIX.sub("", cell.comment.text or "").strip()
    date_str = ""
    if hasattr(cell.comment, "date") and cell.comment.date:
        date_str = cell.comment.date.strftime("%Y-%m-%d")

    return text, date_str


def extract_threaded_comments(zip_file: zipfile.ZipFile) -> dict[str, dict[str, list[tuple[str, str]]]]:
    result = {}
    try:
        wb_root = ET.fromstring(zip_file.read("xl/workbook.xml").decode("utf-8"))
        rels_root = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels").decode("utf-8"))
        rels_dict = {r.get("Id"): r.get("Target").lstrip("/") for r in rels_root}

        for sheet in wb_root.iter():
            if not sheet.tag.endswith("sheet"):
                continue

            name = sheet.get("name")
            r_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rels_dict.get(r_id)
            if not target:
                continue

            if target.startswith("xl/"):
                sheet_path = target
            else:
                sheet_path = "xl/" + target

            rels_path = posixpath.join(posixpath.dirname(sheet_path), "_rels", posixpath.basename(sheet_path) + ".rels")
            if rels_path not in zip_file.namelist():
                continue

            sheet_rels_root = ET.fromstring(zip_file.read(rels_path).decode("utf-8"))

            tc_target = None
            for rel in sheet_rels_root:
                if rel.get("Type", "").endswith("/threadedComment"):
                    tc_target = rel.get("Target")
                    break

            if not tc_target:
                continue

            tc_target = tc_target.lstrip("/")
            tc_path = posixpath.normpath(posixpath.join(posixpath.dirname(sheet_path), tc_target))

            if tc_path not in zip_file.namelist():
                continue

            tc_root = ET.fromstring(zip_file.read(tc_path).decode("utf-8"))
            sheet_comments = {}

            for tc in tc_root.iter():
                if not tc.tag.endswith("threadedComment"):
                    continue

                ref = tc.get("ref")
                d_t = tc.get("dT", "")
                text_elem = next((child for child in tc if child.tag.endswith("text")), None)

                if text_elem is not None and text_elem.text and ref:
                    date_only = d_t[:10] if d_t else ""
                    sheet_comments.setdefault(ref, []).append((date_only, text_elem.text))

            if sheet_comments:
                result[name] = sheet_comments

    except Exception as e:
        print(f"Не удалось извлечь threaded comments: {e}")

    return result


def _find_real_bounds(ws: Worksheet, max_rows: int = 2000, max_cols: int = 100):
    last_row = 0
    last_col = 0
    for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(max_rows, ws.max_row)), start=1):
        for c_idx, cell in enumerate(row, start=1):
            if c_idx > max_cols:
                break
            if cell.value is not None and str(cell.value).strip():
                last_row = max(last_row, r_idx)
                last_col = max(last_col, c_idx)
    return last_row, last_col


def parse_workbook(data: bytes) -> list[SheetMatrix]:
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        all_threaded = extract_threaded_comments(zf)

    matrices = []
    for name in wb.sheetnames:
        ws = wb[name]
        last_row, last_col = _find_real_bounds(ws)
        rows = []

        for r in range(1, last_row + 1):
            row_cells = []
            for c in range(1, last_col + 1):
                cell = ws.cell(row=r, column=c)
                c_text, c_date = _extract_comment(cell)
                row_cells.append(Cell(
                    value=_extract_value(cell),
                    color=_extract_color(cell),
                    comment=c_text,
                    comment_date=c_date
                ))
            rows.append(row_cells)

        matrices.append(SheetMatrix(
            name=name,
            rows=rows,
            threaded_comments=all_threaded.get(name, {})
        ))
    return matrices


def load_workbook_matrices(spreadsheet_id: str, credentials_path: str) -> list[SheetMatrix]:
    data = download_xlsx(spreadsheet_id, credentials_path)
    return parse_workbook(data)