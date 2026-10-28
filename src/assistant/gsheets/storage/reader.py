import sqlite3
import time
from pathlib import Path
from typing import Optional, Union

from .manifest import MANIFEST_FILENAME, read_manifest


def open_current_db(
    output_dir: Union[str, Path],
    *,
    max_retries: int = 2,
    retry_delay: float = 0.1,
) -> tuple[sqlite3.Connection, str]:
    out_dir = Path(output_dir)
    manifest_path = out_dir / MANIFEST_FILENAME

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        manifest = read_manifest(manifest_path)
        if not manifest or not manifest.current_db:
            raise FileNotFoundError(
                f"manifest.json не содержит current_db: {manifest_path}"
            )

        db_path = out_dir / manifest.current_db

        if not db_path.exists():
            last_error = FileNotFoundError(f"БД не найдена: {db_path}")
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            raise last_error

        uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"
        try:
            conn = sqlite3.connect(uri, uri=True)
            return conn, manifest.current_db
        except sqlite3.OperationalError as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            raise

    raise last_error