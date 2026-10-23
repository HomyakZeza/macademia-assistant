import argparse
import json
from pathlib import Path

from ..config import load_settings
from ..gsheets.extraction.workbook_extract import extract_workbook
from ..gsheets.normalization.pipeline import run_pipeline


def main() -> None:
    p = argparse.ArgumentParser(
        prog="assistant",
        description="ETL: Google Sheets → JSON (L1) + SQLite (L2).",
    )
    p.add_argument(
        "-o", "--output", required=True,
        help="Путь для JSON Layer 1 (сырые данные)",
    )
    p.add_argument(
        "--db-output", default=None,
        help="Путь к SQLite-файлу (канонический формат для LLM)",
    )
    args = p.parse_args()

    settings = load_settings()
    workbook = extract_workbook(
        settings.google_spreadsheet_id,
        settings.google_application_credentials,
    )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    workbook.save(args.output)

    summary = {
        "sheets": len(workbook.sheets),
        "class_blocks": sum(len(s.classes) for s in workbook.sheets),
        "lessons": sum(
            len(c.lessons) for s in workbook.sheets for c in s.classes
        ),
        "json_output": args.output,
    }

    if args.db_output:
        summary["sqlite"] = run_pipeline(workbook, args.db_output)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()