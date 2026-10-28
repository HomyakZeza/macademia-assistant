from typing import Optional

import psycopg

from ..load import StudentIdResolver


class PostgresResolver(StudentIdResolver):
    def __init__(
        self,
        dsn: str,
        *,
        sslmode: Optional[str] = None,
        sslcert: Optional[str] = None,
        sslkey: Optional[str] = None,
        sslrootcert: Optional[str] = None,
    ):
        kwargs = {}

        if sslcert:
            kwargs["sslmode"] = sslmode or "verify-full"
            kwargs["sslcert"] = sslcert
            if sslkey:
                kwargs["sslkey"] = sslkey
            if sslrootcert:
                kwargs["sslrootcert"] = sslrootcert

        self._conn = psycopg.connect(dsn, **kwargs)

    def resolve(self, name: str, class_level: str) -> Optional[str]:
        if not name or not class_level:
            return None

        try:
            row = self._conn.execute(
                """
                SELECT p.id
                FROM school.people p
                JOIN school.students s ON s.people = p.id
                JOIN school.classes c ON c.id = s.class
                WHERE (p.name || ' ' || p.last_name) = %s
                  AND c.level::text = %s
                  AND s.active = true
                  AND p.active = true
                LIMIT 1
                """,
                (name.strip(), str(class_level).strip()),
            ).fetchone()
        except psycopg.Error as e:
            print(f"PostgresResolver: ошибка запроса для {name!r}: {e}")
            return None

        return str(row[0]) if row else None

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass