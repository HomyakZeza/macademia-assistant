import os
import sqlite3
from typing import Optional
import psycopg

from ..config import load_settings
from ..gsheets.storage.reader import open_current_db


def get_db() -> tuple[sqlite3.Connection, str]:
    settings = load_settings()
    return open_current_db(settings.output_dir)


def get_pg_connection(settings) -> psycopg.Connection:
    kwargs = {}
    if settings.postgres_ssl_cert:
        kwargs["sslmode"] = settings.postgres_sslmode
        kwargs["sslcert"] = settings.postgres_ssl_cert
        if settings.postgres_ssl_key:
            kwargs["sslkey"] = settings.postgres_ssl_key
        if settings.postgres_ssl_rootcert:
            kwargs["sslrootcert"] = settings.postgres_ssl_rootcert
    return psycopg.connect(settings.postgres_dsn, **kwargs)


class PermissionDenied(Exception):
    pass


class PermissionService:
    """Права по новым правилам (родители/сотрудники)"""

    def __init__(self) -> None:
        settings = load_settings()
        self._dsn = settings.postgres_dsn
        self._allow_unsafe = (
            os.environ.get("MCP_ALLOW_UNSAFE", "").strip().lower() in ("1", "true", "yes")
        )

    def is_allowed_to_see(self, requester_people_id: str, child_people_id: str) -> bool:
        if not requester_people_id or not child_people_id:
            return False

        if not self._dsn:
            if self._allow_unsafe:
                return True
            raise PermissionDenied(
                "Проверка прав недоступна (нет POSTGRES_DSN). "
                "Для локальной разработки установи MCP_ALLOW_UNSAFE=true."
            )

        settings = load_settings()
        try:
            with get_pg_connection(settings) as pg:
                # 1. Доступ родителя
                row = pg.execute("""
                    SELECT 1 FROM school.families f_req
                    JOIN school.families f_child ON f_req.family = f_child.family
                    WHERE f_req.people = %s::uuid AND f_child.people = %s::uuid
                      AND f_req.id <> f_child.id
                    LIMIT 1
                """, (requester_people_id, child_people_id)).fetchone()
                if row: return True

                # 2. Доступ классного руководителя
                row = pg.execute("""
                    SELECT 1 FROM school.classes c
                    JOIN school.students s ON s.class = c.id
                    WHERE c.teacher = %s::uuid AND s.people = %s::uuid
                    LIMIT 1
                """, (requester_people_id, child_people_id)).fetchone()
                if row: return True

                # 3. Доступ учителя-предметника
                row = pg.execute("""
                    SELECT 1 FROM school.employes e
                    JOIN school."class-subjects" cs ON cs.employe = e.id
                    JOIN school.students s ON s.class = cs.class
                    WHERE e.people = %s::uuid AND s.people = %s::uuid
                    LIMIT 1
                """, (requester_people_id, child_people_id)).fetchone()
                if row: return True

                # 4. Доступ power-пользователя
                row = pg.execute("""
                    SELECT 1 FROM school.employes e
                    WHERE e.people = %s::uuid AND e.power = true
                    LIMIT 1
                """, (requester_people_id,)).fetchone()
                if row: return True

                return False
        except Exception as e:
            print(f"PermissionService: ошибка запроса: {e}")
            return False


def get_permission_service() -> PermissionService:
    return PermissionService()