"""Список детей родителя"""

import psycopg

from ...config import load_settings
from ..db import get_db


def list_children(requester_people_id: str) -> dict:
    if not requester_people_id:
        return {"error": "requester_people_id is required", "children": []}

    settings = load_settings()
    if not settings.postgres_dsn:
        return {
            "error": "PostgreSQL не настроен (POSTGRES_DSN). "
                     "list_children требует доступ к school.families.",
            "children": [],
        }

    try:
        with psycopg.connect(settings.postgres_dsn) as pg:
            rows = pg.execute(
                """
                SELECT DISTINCT f2.people::text
                FROM school.families f1
                JOIN school.families f2 ON f1.family = f2.family
                WHERE f1.people = %s::uuid
                  AND f1.id <> f2.id
                """,
                (requester_people_id,),
            ).fetchall()
    except Exception as e:
        return {"error": f"PostgreSQL error: {e}", "children": []}

    member_ids = [r[0] for r in rows]
    if not member_ids:
        return {"children": []}

    conn, _ = get_db()
    try:
        placeholders = ",".join("?" * len(member_ids))
        rows = conn.execute(
            f"""
            SELECT external_id, name, class_level
            FROM students
            WHERE external_id IN ({placeholders})
            ORDER BY class_level, name
            """,
            member_ids,
        ).fetchall()
    finally:
        conn.close()

    children = [
        {"people_id": r[0], "name": r[1], "class_level": r[2]}
        for r in rows
    ]
    return {"children": children, "count": len(children)}