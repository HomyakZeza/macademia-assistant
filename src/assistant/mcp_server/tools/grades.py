"""Оценки и сводка по успеваемости"""

from ..db import PermissionDenied, get_db, get_permission_service


VALID_KINDS = ("homework", "lesson_work", "test")


def _find_student(conn, child_people_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, name, class_level FROM students WHERE external_id = ?",
        (child_people_id,),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "class_level": row[2]}


def _check_permission(requester_people_id: str, child_people_id: str) -> None:
    perm = get_permission_service()
    if not perm.is_parent_of(requester_people_id, child_people_id):
        raise PermissionDenied(
            f"Requester {requester_people_id} не является родителем "
            f"ребёнка {child_people_id}"
        )


def _subject_match(db_subject: str, query_subject: str) -> bool:
    return db_subject.strip().lower() == query_subject.strip().lower()


def get_grades(
    requester_people_id: str,
    child_people_id: str,
    subject: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    kind: str | None = None,
) -> dict:
    if kind is not None and kind not in VALID_KINDS:
        return {
            "error": f"invalid kind: {kind!r}. "
                     f"Допустимо: {', '.join(VALID_KINDS)} или null",
        }

    if from_date and to_date and from_date > to_date:
        return {"error": f"from_date ({from_date}) > to_date ({to_date})"}

    try:
        _check_permission(requester_people_id, child_people_id)
    except PermissionDenied as e:
        return {"error": str(e)}

    conn, _ = get_db()
    try:
        student = _find_student(conn, child_people_id)
        if not student:
            return {
                "error": f"Ученик с people_id={child_people_id} не найден "
                         f"в текущей БД",
            }

        conditions = ["r.student_id = ?"]
        params: list = [student["id"]]

        if from_date:
            conditions.append("l.date >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("l.date <= ?")
            params.append(to_date)

        rows = conn.execute(
            f"""
            SELECT l.date, l.subject, l.topic, l.lesson_seq,
                   r.is_absent,
                   r.homework_grade, r.homework_comment,
                   r.homework_completed_percent,
                   r.lesson_grade, r.lesson_comment,
                   r.test_grade, r.test_comment
            FROM records r
            JOIN lessons l ON l.id = r.lesson_id
            WHERE {' AND '.join(conditions)}
            ORDER BY l.date, l.lesson_seq
            """,
            params,
        ).fetchall()

        grades: list[dict] = []
        for r in rows:
            (date, subj, topic, seq, absent,
             hw_g, hw_c, hw_p,
             lw_g, lw_c,
             ts_g, ts_c) = r

            if subject and not _subject_match(subj, subject):
                continue

            if kind == "homework" and hw_g is None:
                continue
            if kind == "lesson_work" and lw_g is None:
                continue
            if kind == "test" and ts_g is None:
                continue
            if kind is None and hw_g is None and lw_g is None and ts_g is None:
                continue

            grades.append({
                "date": date,
                "subject": subj,
                "topic": topic,
                "lesson_seq": seq,
                "absent": bool(absent),
                "homework": {
                    "grade": hw_g,
                    "comment": hw_c,
                    "completed_percent": hw_p,
                },
                "lesson_work": {"grade": lw_g, "comment": lw_c},
                "test": {"grade": ts_g, "comment": ts_c},
            })

        return {
            "student": student,
            "grades": grades,
            "count": len(grades),
        }
    finally:
        conn.close()


def get_summary(
    requester_people_id: str,
    child_people_id: str,
    subject: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    if from_date and to_date and from_date > to_date:
        return {"error": f"from_date ({from_date}) > to_date ({to_date})"}

    try:
        _check_permission(requester_people_id, child_people_id)
    except PermissionDenied as e:
        return {"error": str(e)}

    conn, _ = get_db()
    try:
        student = _find_student(conn, child_people_id)
        if not student:
            return {"error": f"Ученик с people_id={child_people_id} не найден"}

        conditions = ["r.student_id = ?"]
        params: list = [student["id"]]
        if from_date:
            conditions.append("l.date >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("l.date <= ?")
            params.append(to_date)

        rows = conn.execute(
            f"""
            SELECT l.date, l.subject,
                   r.is_absent,
                   r.homework_grade, r.lesson_grade, r.test_grade
            FROM records r
            JOIN lessons l ON l.id = r.lesson_id
            WHERE {' AND '.join(conditions)}
            ORDER BY l.date
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    hw_values: list[float] = []
    lw_values: list[float] = []
    ts_values: list[float] = []
    present = 0
    absent = 0
    dates_seen: list[str] = []

    for date, subj, is_absent, hw, lw, ts in rows:
        if subject and not _subject_match(subj, subject):
            continue
        dates_seen.append(date)
        if is_absent:
            absent += 1
        else:
            present += 1
        if hw is not None:
            hw_values.append(hw)
        if lw is not None:
            lw_values.append(lw)
        if ts is not None:
            ts_values.append(ts)

    def stats(values: list[float]) -> dict:
        if not values:
            return {"values": [], "avg": None, "count": 0}
        return {
            "values": values,
            "avg": round(sum(values) / len(values), 2),
            "count": len(values),
        }

    return {
        "student": student,
        "period": {
            "from": min(dates_seen) if dates_seen else None,
            "to": max(dates_seen) if dates_seen else None,
        },
        "attendance": {
            "present": present,
            "absent": absent,
            "total": present + absent,
        },
        "by_kind": {
            "homework": stats(hw_values),
            "lesson_work": stats(lw_values),
            "test": stats(ts_values),
        },
    }