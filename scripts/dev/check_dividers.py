"""Показать строки-разделители между блоками и горизонтальное деление.

Запуск: python check_dividers.py
"""

from assistant.config import load_settings
from assistant.gsheets.extraction.xlsx_reader import load_workbook_matrices


def col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def dump_rows(m, r_start, r_end, c_limit=16, label=""):
    """Печатает строки r_start..r_end (1-based) с обрезкой по колонкам."""
    if label:
        print(f"  --- {label} ---")
    for r in range(max(1, r_start), min(r_end, len(m.rows)) + 1):
        row = m.rows[r - 1]
        cells = []
        for c in range(min(c_limit, len(row))):
            v = row[c].value
            if not v:
                cells.append("·")
            else:
                v = v.strip()
                if len(v) > 10:
                    v = v[:10] + "…"
                cells.append(v)
        print(f"  {r:>3}: " + " | ".join(cells))


def find_dates(m):
    """Координаты (row, col) ячеек «Дата» (0-based)."""
    hits = []
    for r_idx, row in enumerate(m.rows):
        for c_idx, cell in enumerate(row):
            if cell.value.strip() == "Дата":
                hits.append((r_idx, c_idx))
    return hits


def main():
    s = load_settings()
    mats = load_workbook_matrices(
        s.google_spreadsheet_id, s.google_application_credentials,
    )

    # Листы, где нужно увидеть разделители
    targets = [
        "ТВиС",            # 3 блока подряд
        "Информатика",     # 3 блока подряд
        "Русский 7-9",     # 4 блока подряд
        "Химия 8-9",       # 2 блока, разные классы
        "География",       # 5 блоков — что там?
        "Биология",        # 5 блоков
        "Физика",          # 3 блока РЯДОМ (в одной строке)
    ]

    for name in targets:
        if name not in [m.name for m in mats]:
            continue
        m = next(x for x in mats if x.name == name)
        dates = find_dates(m)

        print(f"\n{'=' * 60}")
        print(f"ЛИСТ: {name!r}  (A1={m.rows[0][0].value!r})")
        print(f"{'=' * 60}")

        # 1. Строки-разделители: 3 строки ПЕРЕД каждым «Дата» (кроме первого)
        for i, (r, c) in enumerate(dates):
            if i == 0:
                continue
            start = max(1, r - 4 + 1)  # 1-based, 3 строки до
            end = r + 2                # и 2 строки после
            dump_rows(m, start, end, c_limit=16,
                     label=f"Вокруг 'Дата' №{i+1} (строка {r+1})")

        # 2. Для Физики — горизонтальные блоки: показать строки 1-6 в колонках вокруг Q и AG
        if name == "Физика":
            print("\n  --- Горизонтальное деление (Физика) ---")
            # Q = 17-я колонка (index 16), AG = 33-я колонка (index 32)
            for label, c_start in [("Перед Q3 (колонки M-Q)", 12),
                                    ("Перед AG3 (колонки AC-AG)", 28)]:
                print(f"\n  {label}:")
                header = "     " + " ".join(
                    f"{col_letter(c):>6}" for c in range(c_start, c_start + 6)
                )
                print(header)
                for r in range(0, 6):
                    row = m.rows[r]
                    cells = [
                        f"{(row[c].value[:6] if row[c].value else '·'):>6}"
                        for c in range(c_start, min(c_start + 6, len(row)))
                    ]
                    print(f"  {r+1:>2}: " + " ".join(cells))


if __name__ == "__main__":
    main()