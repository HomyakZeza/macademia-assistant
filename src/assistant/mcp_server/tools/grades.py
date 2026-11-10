"""Оценки и сводка по успеваемости"""

from typing import Optional
from ..db import PermissionDenied, get_db, get_permission_service


VALID_KINDS = ("homework", "lesson_work", "test")


def _format_homework(grade: Optional[float]) -> Optional[str]:
    """Переводит оценку за ДЗ в текстовое описание (BR-17)"""
    if grade is None:
        return None
    if 0 <= grade <= 1.0:
        return "Домашнее задание не делалось."
    if 1.0 < grade <= 2.5:
        return "Домашнее задание не выполнено или выполнено совершенно неправильно."
    if 2.5 < grade <= 3.5:
        return "Домашнее задание выполнено, но недостаточно добросовестно."
    if 3.5 < grade <= 5.0:
        return "Домашнее задание выполнено хорошо."
    return "Некорректная оценка (вне шкалы 0-5)."


def _check_permission(requester_people_id: str, child_people_id: str) -> None:
    perm = get_permission_service()
    if not perm.is_allowed_to_see(requester_people_id, child_people_id):
        raise PermissionDenied(f"Нет доступа к данным ребенка {child_people_id}")


def _find_student(conn, child_people_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, name, class_level FROM students WHERE external_id = ?",
        (child_people_id,),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "class_level": row[2]}


def _subject_match(db_subject: str, query_subject: str) -> bool:
    return db_subject.strip().lower() == query_subject.strip().lower()


def get_grades(
    requester_people_id: str,
    child_people_id: str,
    subject: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    kind: Optional[str] = None,
) -> dict:
    """Возвращает оценки ребёнка с учетом правил раскрытия (BR-14, BR-17)"""
    if kind is not None and kind not in VALID_KINDS:
        return {"error": f"invalid kind: {kind!r}. Допустимо: {', '.join(VALID_KINDS)} или null"}
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
            return {"error": f"Ученик с people_id={child_people_id} не найден в текущей БД"}

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
                   r.homework_grade, r.homework_comment, r.homework_completed_percent,
                   r.lesson_grade, r.lesson_comment,
                   r.test_grade, r.test_comment
            FROM records r
            JOIN lessons l ON l.id = r.lesson_id
            WHERE {' AND '.join(conditions)}
            ORDER BY l.date, l.lesson_seq
            """,
            params,
        ).fetchall()

        grades = []
        for r in rows:
            (date, subj, topic, seq, absent,
             hw_g, hw_c, hw_p,
             lw_g, lw_c,
             ts_g, ts_c) = r

            if subject and not _subject_match(subj, subject):
                continue

            # BR-14: Скрываем оценки за классную работу ниже 4
            show_lesson_grade = lw_g is not None and lw_g >= 4.0

            # Фильтрация по запрошенному типу
            if kind == "homework" and hw_g is None:
                continue
            if kind == "lesson_work" and not show_lesson_grade:
                continue
            if kind == "test" and ts_g is None:
                continue
            if kind is None and hw_g is None and not show_lesson_grade and ts_g is None:
                continue

            grades.append({
                "date": date,
                "subject": subj,
                "topic": topic,
                "lesson_seq": seq,
                "absent": bool(absent),
                "homework": {
                    "grade": hw_g,
                    "description": _format_homework(hw_g), # BR-17
                    "comment": hw_c,
                    "completed_percent": hw_p
                },
                # BR-14: В JSON попадает только положительная оценка за урок
                "lesson_work": {
                    "grade": lw_g if show_lesson_grade else None,
                    "comment": lw_c
                },
                "test": {
                    "grade": ts_g,
                    "comment": ts_c
                }
            })

        return {"student": student, "grades": grades, "count": len(grades)}
    finally:
        conn.close()


def get_summary(
    requester_people_id: str,
    child_people_id: str,
    subject: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict:
    """Сводка: средние по типам, количество, пропуски (BR-14)"""
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
            SELECT l.date, l.subject, r.is_absent,
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
    present, absent = 0, 0
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
        # BR-14: Не учитываем в среднем оценки ниже 4
        if lw is not None and lw >= 4.0:
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
            "lesson_work": stats(lw_values), # Здесь только 4 и 5
            "test": stats(ts_values),
        },
    }