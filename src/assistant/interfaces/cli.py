import argparse
import json

from ..gsheets.pipeline import run_full_pipeline


def main() -> None:
    p = argparse.ArgumentParser(
        prog="assistant",
        description="ETL: Google Sheets → SQLite (опционально JSON).",
    )
    p.add_argument(
        "--save-json",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Сохранять промежуточный JSON (Layer 1). "
             "По умолчанию — из .env (SAVE_INTERMEDIATE_JSON).",
    )
    p.add_argument(
        "--db-name",
        default="macademia.db",
        help="Имя файла SQLite внутри OUTPUT_DIR",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Папка вывода (по умолчанию из .env OUTPUT_DIR)",
    )
    args = p.parse_args()

    result = run_full_pipeline(
        save_json=args.save_json,
        output_dir=args.output_dir,
        db_name=args.db_name,
    )

    summary = {
        "db_path": result["db_path"],
        "json_path": result["json_path"],
        "resolver_used": result["resolver_used"],
        **{k: v for k, v in result["counts"].items()
           if k not in ("duplicate_examples", "db_path")},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()