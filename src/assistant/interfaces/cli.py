import argparse
import json

from ..config import load_settings
from ..google.extraction.extract import run_etl_l1


def main() -> None:
    p = argparse.ArgumentParser(
        prog="assistant",
        description="Извлечение данных из Google Sheets в Layer 1.",
    )
    p.add_argument("--sheet", required=True, help="Имя листа в Google-таблице")
    p.add_argument("-o", "--output", required=True, help="Путь для выходного JSON")
    args = p.parse_args()

    settings = load_settings()

    result = run_etl_l1(
        spreadsheet_id=settings.google_spreadsheet_id,
        sheet_name=args.sheet,
        credentials_path=settings.google_application_credentials,
        output_path=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()