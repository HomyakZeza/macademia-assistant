"""Посещаемость"""

from ..db import PermissionDenied, get_db, get_permission_service


def get_attendance(
    requester_people_id: str,
    child_people_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    subject: str | None = None,
) -> dict:
    if from_date and to_date and from_date > to_date:
        return {"error": f"from_date ({from_date}) > to_date ({to_date})"}

    try:
        perm = get_permission_service()
        if not perm.is_parent_of(requester_people_id, child_people_id):
            raise PermissionDenied(
                f"Requester {requester_people_id} не является родителем "
                f"ребёнка {child_people_id}"
            )
    except PermissionDenied as e:
        return {"error": str(e)}

    conn, _ = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, class_level FROM students WHERE external_id = ?",
            (child_people_id,),
        ).fetchone()
        if not row:
            return {"error": f"Ученик с people_id={child_people_id} не найден"}
        student = {"id": row[0], "name": row[1], "class_level": row[2]}

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
            SELECT l.date, l.subject, l.lesson_seq, l.topic, r.is_absent
            FROM records r
            JOIN lessons l ON l.id = r.lesson_id
            WHERE {' AND '.join(conditions)}
            ORDER BY l.date, l.lesson_seq
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    present = 0
    absent = 0
    entries: list[dict] = []

    for date, subj, seq, topic, is_absent in rows:
        if subject and subj.strip().lower() != subject.strip().lower():
            continue
        status = "absent" if is_absent else "present"
        if is_absent:
            absent += 1
        else:
            present += 1
        entries.append({
            "date": date,
            "subject": subj,
            "lesson_seq": seq,
            "topic": topic,
            "status": status,
        })

    return {
        "student": {"name": student["name"], "class_level": student["class_level"]},
        "summary": {"present": present, "absent": absent, "total": present + absent},
        "entries": entries,
    }