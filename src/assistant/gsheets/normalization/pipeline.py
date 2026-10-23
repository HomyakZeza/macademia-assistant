from ..extraction.models import WorkbookExport
from .base import ParsedBlock
from .load import load_to_sqlite, StudentIdResolver
from .registry import get_parser


def run_pipeline(
    workbook: WorkbookExport,
    db_path: str,
    resolver: StudentIdResolver | None = None,
) -> dict:
    all_blocks: list[ParsedBlock] = []
    processed: list[str] = []

    for sheet in workbook.sheets:
        parser = get_parser(sheet.sheet_name)
        for class_block in sheet.classes:
            parsed = parser.transform(class_block, sheet.subject)
            all_blocks.append(parsed)
        processed.append(sheet.sheet_name)

    counts = load_to_sqlite(all_blocks, db_path, resolver)
    counts["sheets_processed"] = len(processed)
    counts["db_path"] = db_path
    return counts