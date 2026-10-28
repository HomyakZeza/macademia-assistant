import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


MANIFEST_FORMAT = "1.0"
MANIFEST_FILENAME = "manifest.json"


@dataclass
class Manifest:
    format: str
    last_modified_time: Optional[str] = None
    current_db: Optional[str] = None
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def read_manifest(path: Path) -> Optional[Manifest]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict) or data.get("format") != MANIFEST_FORMAT:
        return None

    return Manifest(
        format=data["format"],
        last_modified_time=data.get("last_modified_time"),
        current_db=data.get("current_db"),
        updated_at=data.get("updated_at", ""),
    )


def write_manifest(path: Path, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=".manifest_", suffix=".json", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise