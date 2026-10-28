from pathlib import Path


DB_PREFIX = "macademia_"
DB_SUFFIX = ".db"


def pick_next_db_name(output_dir: Path) -> str:
    n = 1
    while True:
        name = f"{DB_PREFIX}{n}{DB_SUFFIX}"
        if not (output_dir / name).exists():
            return name
        n += 1


def cleanup_old_dbs(
    output_dir: Path,
    current_db: str,
) -> tuple[list[str], list[str]]:
    deleted: list[str] = []
    failed: list[str] = []

    for path in output_dir.glob(f"{DB_PREFIX}*{DB_SUFFIX}"):
        if path.name == current_db:
            continue
        try:
            path.unlink()
            deleted.append(path.name)
        except PermissionError:
            failed.append(path.name)
        except OSError as e:
            print(f"Не удалось удалить {path.name}: {e}")
            failed.append(path.name)

    return deleted, failed