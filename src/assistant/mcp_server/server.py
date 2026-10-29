from mcp.server.fastmcp import FastMCP

from .tools.attendance import get_attendance as _get_attendance
from .tools.grades import get_grades as _get_grades
from .tools.grades import get_summary as _get_summary
from .tools.students import list_children as _list_children


mcp = FastMCP("macademia-assistant")


@mcp.tool(
    description=(
        "Возвращает список учеников, связанных с родителем. "
        "Принимает UUID родителя (people.id из PostgreSQL). "
        "Возвращает {children: [{people_id, name, class_level}], count}."
    ),
)
def list_children(requester_people_id: str) -> dict:
    return _list_children(requester_people_id)


@mcp.tool(
    description=(
        "Возвращает оценки ребёнка с фильтрами. "
        "requester_people_id — UUID родителя (кто спрашивает). "
        "child_people_id — UUID ребёнка (о ком). "
        "subject — название предмета (регистронезависимо), опционально. "
        "from_date / to_date — YYYY-MM-DD, включительно, опционально. "
        "kind — 'homework' | 'lesson_work' | 'test' | null (все типы). "
        "Возвращает {student, grades: [...], count}. "
        "Если requester — не родитель ребёнка, возвращает {error}."
    ),
)
def get_grades(
    requester_people_id: str,
    child_people_id: str,
    subject: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    kind: str | None = None,
) -> dict:
    return _get_grades(
        requester_people_id, child_people_id,
        subject, from_date, to_date, kind,
    )


@mcp.tool(
    description=(
        "Сводка по успеваемости: средние оценки по типам работ, "
        "количество, пропуски. Принимает те же фильтры, что get_grades, "
        "кроме kind. Возвращает {student, period, attendance, by_kind: "
        "{homework, lesson_work, test}}."
    ),
)
def get_summary(
    requester_people_id: str,
    child_people_id: str,
    subject: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    return _get_summary(
        requester_people_id, child_people_id,
        subject, from_date, to_date,
    )


@mcp.tool(
    description=(
        "Посещаемость ребёнка за период. "
        "from_date / to_date — YYYY-MM-DD, включительно, опционально. "
        "subject — фильтр по предмету, опционально. "
        "Возвращает {student, summary: {present, absent, total}, entries: [...]}."
    ),
)
def get_attendance(
    requester_people_id: str,
    child_people_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    subject: str | None = None,
) -> dict:
    return _get_attendance(
        requester_people_id, child_people_id,
        from_date, to_date, subject,
    )


def main() -> None:
    mcp.run()