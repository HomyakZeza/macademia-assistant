"""Исследование структуры листов XLSX.

Запуск: python check_structure.py

Печатает для каждого листа:
  - Размер, A1 (заголовок листа)
  - Все координаты ячеек «Дата» (и вариантов)
  - Все координаты ячеек «Урок»
  - Для 3-4 выбранных листов — первые 5×10 ячеек, чтобы увидеть вёрстку
"""

from assistant.config import load_settings
from assistant.gsheets.extraction.xlsx_reader import load_workbook_matrices


# Для этих листов печатаем дополнительно матрицу 5×10
DETAIL_SHEETS = ["Математика 5", "Химия 8-9", "Информатика", "Алгебра 7"]


# Маркеры, которые ищем в ячейках
DATE_MARKERS = ["Дата", "Дата урока", "дата", "дата урока"]
LESSON_MARKERS = ["Урок", "урок"]


def find_markers(matrix, markers):
    """Возвращает список (row, col, value) для всех ячеек с маркером."""
    hits = []
    for r_idx, row in enumerate(matrix.rows):
        for c_idx, cell in enumerate(row):
            v = cell.value.strip()
            if v in markers:
                hits.append((r_idx, c_idx, v))
    return hits


def col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def short_cell(cell) -> str:
    """Компактное представление ячейки для печати."""
    v = cell.value
    if not v:
        return "."
    v = str(v)
    if len(v) > 12:
        v = v[:12] + "…"
    return v


def main() -> None:
    s = load_settings()
    mats = load_workbook_matrices(
        s.google_spreadsheet_id, s.google_application_credentials,
    )

    print(f"Всего листов: {len(mats)}\n")

    for m in mats:
        rows = len(m.rows)
        cols = len(m.rows[0]) if m.rows else 0
        a1 = m.rows[0][0].value if m.rows and m.rows[0] else ""

        print(f"=== {m.name!r} ({rows}×{cols}) ===")
        print(f"  A1: {a1!r}")

        date_hits = find_markers(m, DATE_MARKERS)
        lesson_hits = find_markers(m, LESSON_MARKERS)

        if date_hits:
            coords = ", ".join(
                f"{col_letter(c)}{r+1}" for r, c, _ in date_hits
            )
            print(f"  Дата: {len(date_hits)} → {coords}")
        else:
            print(f"  Дата: НЕ НАЙДЕНА ⚠")

        if lesson_hits:
            coords = ", ".join(
                f"{col_letter(c)}{r+1}" for r, c, _ in lesson_hits[:10]
            )
            suffix = "..." if len(lesson_hits) > 10 else ""
            print(f"  Урок: {len(lesson_hits)} → {coords}{suffix}")
        else:
            print(f"  Урок: НЕ НАЙДЕН ⚠")

        print()

    # Детальный просмотр для выбранных листов
    print("\n" + "=" * 60)
    print("ДЕТАЛЬНЫЙ ПРОСМОТР (первые 5×10 ячеек)")
    print("=" * 60)

    for name in DETAIL_SHEETS:
        if name not in [m.name for m in mats]:
            continue
        m = next(x for x in mats if x.name == name)
        print(f"\n=== {name!r} ===")

        # Шапка: буквы колонок
        header = "     " + " ".join(
            f"{col_letter(c):>6}" for c in range(min(10, len(m.rows[0])))
        )
        print(header)

        for r_idx in range(min(5, len(m.rows))):
            row = m.rows[r_idx]
            cells = [
                f"{short_cell(row[c])[:6]:>6}"
                for c in range(min(10, len(row)))
            ]
            print(f"  {r_idx+1:>2}: " + " ".join(cells))


if __name__ == "__main__":
    main()