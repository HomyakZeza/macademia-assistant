import argparse
import json

from ..config import load_settings
from ..gsheets.extraction.workbook_extract import extract_workbook


def main() -> None:
    p = argparse.ArgumentParser(
        prog="assistant",
        description="ETL: Google Sheets → JSON (XLSX-путь).",
    )
    p.add_argument(
        "-o", "--output",
        required=True,
        help="Путь для выходного JSON",
    )
    args = p.parse_args()

    settings = load_settings()

    workbook = extract_workbook(
        settings.google_spreadsheet_id,
        settings.google_application_credentials,
    )

    from pathlib import Path
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    workbook.save(args.output)

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

    print(json.dumps({
        "spreadsheet_id": settings.google_spreadsheet_id,
        "sheets": len(workbook.sheets),
        "class_blocks": total_blocks,
        "non_empty_blocks": non_empty_blocks,
        "lessons": total_lessons,
        "output_path": args.output,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()