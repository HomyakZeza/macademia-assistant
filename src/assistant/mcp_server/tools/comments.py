"""Комментарии учителей к ребенку."""

from ..db import PermissionDenied, get_db, get_permission_service

def get_comments(
    requester_people_id: str,
    child_people_id: str,
    subject: str | None = None,
) -> dict:
    try:
        perm = get_permission_service()
        if not perm.is_allowed_to_see(requester_people_id, child_people_id):
            raise PermissionDenied(f"Requester не имеет доступа к ребенку")
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

        query = "SELECT subject, date, text FROM student_comments WHERE student_id = ?"
        params = [student["id"]]

        rows = conn.execute(query + " ORDER BY date", params).fetchall()

        comments = []
        for subj, date, text in rows:
            if subject and subj.strip().lower() != subject.strip().lower():
                continue
            comments.append({"date": date, "subject": subj, "text": text})

        return {"student": student, "comments": comments, "count": len(comments)}
    finally:
        conn.close()