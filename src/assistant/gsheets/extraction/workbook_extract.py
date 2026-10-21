from datetime import datetime, timezone

from ...config import load_settings
from .block_extract import extract_sheet
from .discovery import parse_sheet_name
from .models import (
    RawExportMeta, WorkbookExport, SheetExport,
)
from .xlsx_reader import load_workbook_matrices


PARSER_VERSION = "1.0"
SCHEMA_VERSION = "2.0"


def extract_workbook(
    spreadsheet_id: str,
    credentials_path: str,
) -> WorkbookExport:
    matrices = load_workbook_matrices(spreadsheet_id, credentials_path)

    meta = RawExportMeta(
        schema_version=SCHEMA_VERSION,
        source_spreadsheet_id=spreadsheet_id,
        source_sheet_name="",
        source_url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
        exported_at=datetime.now(timezone.utc).isoformat(),
        parser_version=PARSER_VERSION,
    )

    workbook = WorkbookExport(meta=meta)

    for matrix in matrices:
        parsed_name = parse_sheet_name(matrix.name)
        sheet_export = extract_sheet(matrix, parsed_name.subject)
        workbook.sheets.append(sheet_export)

    return workbook


def run_etl(
    output_path: str,
) -> dict:
    from pathlib import Path

    settings = load_settings()
    workbook = extract_workbook(
        settings.google_spreadsheet_id,
        settings.google_application_credentials,
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)

    total_lessons = sum(
        len(blk.lessons)
        for sheet in workbook.sheets
        for blk in sheet.classes
    )
    non_empty_blocks = sum(
        1
        for sheet in workbook.sheets
        for blk in sheet.classes
        if blk.lessons
    )
    total_blocks = sum(len(sheet.classes) for sheet in workbook.sheets)

    return {
        "spreadsheet_id": settings.google_spreadsheet_id,
        "sheets": len(workbook.sheets),
        "class_blocks": total_blocks,
        "non_empty_blocks": non_empty_blocks,
        "lessons": total_lessons,
        "output_path": output_path,
    }