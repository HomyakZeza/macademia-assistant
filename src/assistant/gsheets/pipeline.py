from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import load_settings
from .extraction.drive_meta import get_modified_time
from .extraction.workbook_extract import extract_workbook
from .normalization.load import StudentIdResolver
from .normalization.pipeline import run_pipeline
from .storage.manifest import (
    MANIFEST_FILENAME, MANIFEST_FORMAT, Manifest,
    read_manifest, write_manifest,
)
from .storage.versioning import cleanup_old_dbs, pick_next_db_name


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
    force: bool = False,
) -> dict:
    settings = load_settings()
    out_dir = Path(output_dir or settings.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / MANIFEST_FILENAME
    old_manifest = read_manifest(manifest_path)

    current_mtime: Optional[str] = None
    try:
        current_mtime = get_modified_time(
            settings.google_spreadsheet_id,
            settings.google_application_credentials,
        )
    except Exception as e:
        print(f"Не удалось получить modifiedTime: {e}")
        print("продолжаю без проверки")

    if not force and current_mtime and old_manifest:
        same_time = old_manifest.last_modified_time == current_mtime
        db_exists = (
            old_manifest.current_db
            and (out_dir / old_manifest.current_db).exists()
        )
        if same_time and db_exists:
            print(f"таблица не изменилась, использую {old_manifest.current_db}")
            return {
                "skipped": True,
                "reason": "not_modified",
                "last_modified_time": current_mtime,
                "db_path": str(out_dir / old_manifest.current_db),
                "db_name": old_manifest.current_db,
                "json_path": None,
                "counts": {},
                "resolver_used": False,
                "deleted_old_dbs": [],
                "failed_to_delete": [],
            }

    print("extract Google Sheets...")
    workbook = extract_workbook(
        settings.google_spreadsheet_id,
        settings.google_application_credentials,
    )

    if save_json is None:
        save_json = settings.save_intermediate_json

    json_path: Optional[Path] = None
    if save_json:
        json_path = out_dir / "workbook.json"
        workbook.save(str(json_path))
        print(f"JSON сохранён: {json_path}")

    resolver = _create_resolver(settings)

    db_name = pick_next_db_name(out_dir)
    db_path = out_dir / db_name
    print(f"transform + load {db_name}...")

    try:
        counts = run_pipeline(workbook, str(db_path), resolver)
    finally:
        if resolver is not None:
            resolver.close()

    new_manifest = Manifest(
        format=MANIFEST_FORMAT,
        last_modified_time=current_mtime,
        current_db=db_name,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    write_manifest(manifest_path, new_manifest)

    deleted, failed = cleanup_old_dbs(out_dir, db_name)
    if deleted:
        print(f"удалено старых БД: {len(deleted)} ({', '.join(deleted)})")
    if failed:
        print(f"не удалось удалить (залочены): {', '.join(failed)}")

    return {
        "skipped": False,
        "db_path": str(db_path),
        "db_name": db_name,
        "json_path": str(json_path) if json_path else None,
        "counts": counts,
        "resolver_used": resolver is not None,
        "last_modified_time": current_mtime,
        "deleted_old_dbs": deleted,
        "failed_to_delete": failed,
    }