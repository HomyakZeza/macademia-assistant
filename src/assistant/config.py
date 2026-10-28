import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


@dataclass
class Settings:
    google_spreadsheet_id: str
    google_application_credentials: str

    postgres_dsn: Optional[str] = None
    postgres_sslmode: str = "verify-full"
    postgres_ssl_cert: Optional[str] = None
    postgres_ssl_key: Optional[str] = None
    postgres_ssl_rootcert: Optional[str] = None

    save_intermediate_json: bool = False
    output_dir: str = "data/output"


def _resolve_path(raw: str) -> str:
    p = Path(raw)
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return str(p)


def _env_optional(key: str) -> Optional[str]:
    v = os.environ.get(key, "").strip()
    return v or None


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


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
    creds_path = _resolve_path(creds_raw)
    if not Path(creds_path).exists():
        raise RuntimeError(f"Файл ключа не найден: {creds_path}")

    postgres_dsn = _env_optional("POSTGRES_DSN")

    ssl_cert_raw = _env_optional("POSTGRES_SSL_CERT")
    ssl_key_raw = _env_optional("POSTGRES_SSL_KEY")
    ssl_root_raw = _env_optional("POSTGRES_SSL_ROOTCERT")

    ssl_cert = _resolve_path(ssl_cert_raw) if ssl_cert_raw else None
    ssl_key = _resolve_path(ssl_key_raw) if ssl_key_raw else None
    ssl_root = _resolve_path(ssl_root_raw) if ssl_root_raw else None

    for name, path in (
        ("POSTGRES_SSL_CERT", ssl_cert),
        ("POSTGRES_SSL_KEY", ssl_key),
        ("POSTGRES_SSL_ROOTCERT", ssl_root),
    ):
        if path and not Path(path).exists():
            raise RuntimeError(f"{name}: файл не найден: {path}")

    return Settings(
        google_spreadsheet_id=sid,
        google_application_credentials=creds_path,
        postgres_dsn=postgres_dsn,
        postgres_sslmode=os.environ.get("POSTGRES_SSLMODE", "verify-full").strip(),
        postgres_ssl_cert=ssl_cert,
        postgres_ssl_key=ssl_key,
        postgres_ssl_rootcert=ssl_root,
        save_intermediate_json=_env_bool("SAVE_INTERMEDIATE_JSON", default=False),
        output_dir=os.environ.get("OUTPUT_DIR", "data/output").strip(),
    )