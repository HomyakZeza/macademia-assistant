import os
import sqlite3
from pathlib import Path
from typing import Optional

from ..config import load_settings
from ..gsheets.storage.reader import open_current_db



def get_db() -> tuple[sqlite3.Connection, str]:
    settings = load_settings()
    return open_current_db(settings.output_dir)



class PermissionDenied(Exception):
    """Пользователь не имеет права видеть данные этого ребёнка."""


class PermissionService:
    def __init__(self) -> None:
        settings = load_settings()
        self._dsn = settings.postgres_dsn
        self._allow_unsafe = (
            os.environ.get("MCP_ALLOW_UNSAFE", "").strip().lower()
            in ("1", "true", "yes")
        )

        self._pg_conn = None
        if self._dsn:
            try:
                import psycopg
                kwargs = {}
                if settings.postgres_ssl_cert:
                    kwargs["sslmode"] = settings.postgres_sslmode
                    kwargs["sslcert"] = settings.postgres_ssl_cert
                    if settings.postgres_ssl_key:
                        kwargs["sslkey"] = settings.postgres_ssl_key
                    if settings.postgres_ssl_rootcert:
                        kwargs["sslrootcert"] = settings.postgres_ssl_rootcert
                self._pg_conn = psycopg.connect(self._dsn, **kwargs)
            except Exception as e:
                print(f"PermissionService: PostgreSQL недоступен: {e}")
                self._pg_conn = None

    def is_parent_of(
        self,
        requester_people_id: str,
        child_people_id: str,
    ) -> bool:
        if not requester_people_id or not child_people_id:
            return False

        if self._pg_conn is not None:
            return self._check_postgres(requester_people_id, child_people_id)

        if self._allow_unsafe:
            return True

        raise PermissionDenied(
            "Проверка прав недоступна (нет POSTGRES_DSN). "
            "Для локальной разработки установи MCP_ALLOW_UNSAFE=true."
        )

    def _check_postgres(
        self,
        requester_people_id: str,
        child_people_id: str,
    ) -> bool:
        try:
            row = self._pg_conn.execute(
                """
                SELECT 1
                FROM school.families f_req
                JOIN school.families f_child ON f_req.family = f_child.family
                WHERE f_req.people   = %s::uuid
                  AND f_child.people = %s::uuid
                  AND f_req.id <> f_child.id
                LIMIT 1
                """,
                (requester_people_id, child_people_id),
            ).fetchone()
            return row is not None
        except Exception as e:
            print(f"PermissionService: ошибка запроса: {e}")
            return False

    def close(self) -> None:
        if self._pg_conn is not None:
            try:
                self._pg_conn.close()
            except Exception:
                pass


_permission_service: Optional[PermissionService] = None


def get_permission_service() -> PermissionService:
    global _permission_service
    if _permission_service is None:
        _permission_service = PermissionService()
    return _permission_service