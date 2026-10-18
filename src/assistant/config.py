import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


@dataclass
class Settings:
    google_spreadsheet_id: str
    google_application_credentials: str


def load_settings() -> Settings:
    
    sid = os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()
    if not sid:
        raise RuntimeError(
            "GOOGLE_SPREADSHEET_ID не задан. Проверь .env (см. .env.sample)."
        )

    creds_raw = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not creds_raw:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS не задан. Проверь .env (см. .env.sample)."
        )

    creds_path = Path(creds_raw)
    if not creds_path.is_absolute():
        creds_path = _PROJECT_ROOT / creds_path

    if not creds_path.exists():
        raise RuntimeError(
            f"Файл ключа не найден: {creds_path}. "
            "Проверь GOOGLE_APPLICATION_CREDENTIALS в .env."
        )

    return Settings(
        google_spreadsheet_id=sid,
        google_application_credentials=str(creds_path),
    )