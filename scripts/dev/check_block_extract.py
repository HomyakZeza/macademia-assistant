"""Проверка block_extract. Запуск: python check_block_extract.py"""

import json

from assistant.config import load_settings
from assistant.gsheets.extraction.discovery import parse_sheet_name
from assistant.gsheets.extraction.xlsx_reader import load_workbook_matrices
from assistant.gsheets.extraction.block_extract import extract_sheet


def main():
    s = load_settings()
    mats = load_workbook_matrices(
        s.google_spreadsheet_id, s.google_application_credentials,
    )

    all_exports = []

    for m in mats:
        parsed_name = parse_sheet_name(m.name)
        export = extract_sheet(m, parsed_name.subject)
        all_exports.append(export)

        print(f"\n=== {m.name!r} (subject={parsed_name.subject!r}) ===")
        print(f"  Блоков: {len(export.classes)}")

        for blk in export.classes:
            label = blk.class_label or "<не найден>"
            print(
                f"    class_level={blk.class_level!r:6} "
                f"anchor=({blk.anchor_row},{blk.anchor_col}) "
                f"lessons={len(blk.lessons):3} "
                f"label={label!r}"
            )

        # По первому блоку с уроками — показать первого ученика первого урока
        for blk in export.classes:
            if blk.lessons:
                first = blk.lessons[0]
                print(f"    Первый урок: {first.date!r} topic={first.topic[:30]!r}")
                if first.students:
                    st = first.students[0]
                    print(
                        f"    Первый ученик: {st.name!r} "
                        f"Урок={st.lesson.value!r}/color={st.lesson.color} "
                        f"ДЗ={st.homework.value!r}/color={st.homework.color} "
                        f"КР={st.test.value!r}/color={st.test.color}"
                    )
                break

    # Сохранить полный JSON для просмотра
    out = {
        "sheets": [e.to_dict() for e in all_exports],
    }
    with open("data/output/block_extract.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n\nПолный JSON → data/output/block_extract.json")


if __name__ == "__main__":
    main()