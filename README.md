# Macademia Assistant
Диалоговый ассистент для родителей: получение информации об успеваемости и посещаемости детей из Google Spreadsheet на естественном языке.

## Документация
- [Техническое задание](doc/Техническое задание.md) — цели, границы, use cases, business rules.

## Структура проекта
```
src/assistant/
├── config.py           # конфигурация приложения (из .env)
├── google/
│   ├── extraction/     # извлечение сырых данных из Google Sheets
│   │   ├── extract.py
│   │   └── models.py
│   └── normalization/  # нормализация под правила преподавателя
└── interfaces/
    ├── cli.py          # интерфейс для MVP
    └── matrix_bot.py   # интерфейс для применения
```

- **extraction** — читает Google Sheets и сохраняет сырые значения, цвета, структуру уроков.
- **normalization** — применяет правила конкретного преподавателя и строит канонический формат, который впоследствии передаётся в языковую модель.
- **interfaces** — точки входа.

## Требования
- Python 3.11+
- PostgreSQL 15+

## Установка
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell

pip install -e .
```

Зависимости ставятся через `pip` и описаны в `pyproject.toml`.

## Конфигурация
```bash
cp .env.sample .env
```

Ключи:
- `GOOGLE_SPREADSHEET_ID` — идентификатор Google-таблицы.
- `GOOGLE_APPLICATION_CREDENTIALS` — путь к JSON-ключу сервисного аккаунта.


## Пример запуска
Извлечь данные из указанного листа:

```bash
python -m assistant --sheet "Математика 5" -o "data/output/math_5.json"
```

Результат — JSON во внутреннем формате.