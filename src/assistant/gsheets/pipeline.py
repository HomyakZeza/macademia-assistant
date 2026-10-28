from pathlib import Path
from typing import Optional

from ..config import load_settings
from .extraction.workbook_extract import extract_workbook
from .normalization.load import StudentIdResolver
from .normalization.pipeline import run_pipeline


def _create_resolver(settings) -> Optional[StudentIdResolver]:
    if not settings.postgres_dsn:
        return None

    try:
        from .normalization.resolvers.postgres import PostgresResolver
    except ImportError:
        print("psycopg не установлен — работаю без PostgreSQL")
        return None

    try:
        return PostgresResolver(
            settings.postgres_dsn,
            sslmode=settings.postgres_sslmode,
            sslcert=settings.postgres_ssl_cert,
            sslkey=settings.postgres_ssl_key,
            sslrootcert=settings.postgres_ssl_rootcert,
        )
    except Exception as e:
        print(f"Не удалось подключиться к PostgreSQL: {e}")
        print("продолжаю без резолвера (external_id будет NULL)")
        return None


def run_full_pipeline(
    *,
    save_json: Optional[bool] = None,
    output_dir: Optional[str] = None,
    db_name: str = "macademia.db",
) -> dict:
    settings = load_settings()

    if save_json is None:
        save_json = settings.save_intermediate_json

    out_dir = Path(output_dir or settings.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path: Optional[Path] = None
    if save_json:
        json_path = out_dir / "workbook.json"

    db_path = out_dir / db_name

    print("  → extract Google Sheets...")
    workbook = extract_workbook(
        settings.google_spreadsheet_id,
        settings.google_application_credentials,
    )

    if json_path is not None:
        workbook.save(str(json_path))
        print(f"  → JSON сохранён: {json_path}")

    resolver = _create_resolver(settings)
    resolver_used = resolver is not None

    print("  → transform + load sqlite...")
    try:
        counts = run_pipeline(workbook, str(db_path), resolver)
    finally:
        if resolver is not None:
            resolver.close()

    return {
        "db_path": str(db_path),
        "json_path": str(json_path) if json_path else None,
        "counts": counts,
        "resolver_used": resolver_used,
    }