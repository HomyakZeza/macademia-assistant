import argparse
import json

from ..gsheets.pipeline import run_full_pipeline


def main() -> None:
    p = argparse.ArgumentParser(
        prog="assistant",
        description="ETL: Google Sheets → версионированная SQLite (опц. JSON).",
    )
    p.add_argument(
        "--save-json",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Сохранять промежуточный JSON Layer 1. "
             "По умолчанию — из .env (SAVE_INTERMEDIATE_JSON).",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Папка вывода (по умолчанию из .env OUTPUT_DIR)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Игнорировать modifiedTime, пересобрать БД принудительно",
    )
    args = p.parse_args()

    result = run_full_pipeline(
        save_json=args.save_json,
        output_dir=args.output_dir,
        force=args.force,
    )

    summary = {
        "skipped": result["skipped"],
        "db_path": result.get("db_path"),
        "db_name": result.get("db_name"),
        "json_path": result.get("json_path"),
        "resolver_used": result.get("resolver_used", False),
        "last_modified_time": result.get("last_modified_time"),
    }
    if result["skipped"]:
        summary["reason"] = result.get("reason")
    else:
        counts = result.get("counts", {})
        summary.update({
            k: v for k, v in counts.items()
            if k not in ("duplicate_examples", "db_path")
        })
        summary["deleted_old_dbs"] = result.get("deleted_old_dbs", [])
        summary["failed_to_delete"] = result.get("failed_to_delete", [])

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()