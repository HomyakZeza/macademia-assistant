import argparse
import json

from .etl_l1_raw import run_etl_l1

def main():
    p = argparse.ArgumentParser(prog="assistant")
    p.add_argument("url", help="Ссылка на Google Sheets или spreadsheet_id")
    p.add_argument("--sheet", required=True, help="Имя листа")
    p.add_argument("--creds", required=True, help="Путь к JSON сервисного аккаунта")
    p.add_argument("-o", "--output", required=True, help="Путь для выходного JSON")
    args = p.parse_args()

    result = run_etl_l1(
        url_or_id=args.url,
        sheet_name=args.sheet,
        credentials_path=args.creds,
        output_path=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()