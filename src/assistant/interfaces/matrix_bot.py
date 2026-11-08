import asyncio
import json
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

if sys.platform == "win32":
    policy = (
        getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        or getattr(asyncio, "_WindowsSelectorEventLoopPolicy", None)
    )
    if policy:
        asyncio.set_event_loop_policy(policy())

from ..agent.loop import AgentLoop, SYSTEM_PROMPT
from ..agent.runner import mcp_stdio_session
from ..llm.client import DeepSeekClient
from ..sandbox.executor import SandboxExecutor
from ..config import load_settings
from ..mcp_server.db import get_pg_connection
from ..mcp_server.tools.students import list_children

CURRENT_USER_FILE = Path("data/output/.current_user.json")


def find_user_by_name(name: str) -> dict | None:
    settings = load_settings()
    if not settings.postgres_dsn:
        print("PostgreSQL не настроен (POSTGRES_DSN). Поиск пользователя недоступен.")
        return None

    try:
        with get_pg_connection(settings) as pg:
            row = pg.execute(
                """
                SELECT p.id::text, p.name || ' ' || p.last_name as full_name
                FROM school.people p
                JOIN school.families f ON f.people = p.id
                JOIN school.relations r ON r.id = f.relation
                WHERE (p.name || ' ' || p.last_name) ILIKE %s
                  AND r.name = 'parent'
                LIMIT 1
                """,
                (f"%{name.strip()}%",),
            ).fetchone()

            if row:
                return {"people_id": row[0], "name": row[1]}
    except Exception as e:
        print(f"Ошибка при поиске в PostgreSQL: {e}")

    return None


def load_current_user() -> dict | None:
    if CURRENT_USER_FILE.exists():
        try:
            return json.loads(CURRENT_USER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def save_current_user(user_data: dict) -> None:
    CURRENT_USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_USER_FILE.write_text(json.dumps(user_data, ensure_ascii=False), encoding="utf-8")


def build_system_prompt(user_id: str) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"requester_people_id твоего пользователя: {user_id}. "
        f"Если нужно узнать, о каких детях идёт речь, сначала вызови list_children "
        f"с этим ID, затем используй child_people_id из результата."
    )


async def interactive_loop():
    print("=" * 60)
    print("🤖 Macademia Assistant (эмуляция Matrix-бота)")
    print("Введите /help для списка команд.")
    print("=" * 60)

    current_user = load_current_user()

    if current_user:
        print(f"\n[Система] Вы вошли как: {current_user['name']} (ID: {current_user['people_id']})")
        requester_id = current_user["people_id"]
        messages = [{"role": "system", "content": build_system_prompt(requester_id)}]
    else:
        print("\n[Система] Вы не авторизованы. Введите `/user <ФИО>` для входа.")
        requester_id = None
        messages = []

    verbose = True

    async with mcp_stdio_session() as mcp_session:
        agent = AgentLoop(
            llm=DeepSeekClient(),
            sandbox=SandboxExecutor(),
            mcp_session=mcp_session,
            verbose=verbose,
        )

        while True:
            try:
                user_input = await asyncio.to_thread(input, "\nВы: ")
                user_input = user_input.strip()

                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "выход"):
                    print("До свидания!")
                    break

                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    cmd = parts[0].lower()
                    arg = parts[1] if len(parts) > 1 else ""

                    if cmd == "/help":
                        print("\n[Система] Доступные команды:")
                        print("  /user <ФИО>     - переключиться на другого пользователя (сброс контекста)")
                        print("  /verbose on|off - включить/выключить показ шагов агента")
                        print("  /help           - показать это сообщение")
                        print("  exit            - выйти")
                        continue

                    elif cmd == "/verbose":
                        if arg.lower() == "on":
                            verbose = True
                            agent.verbose = True
                            print("[Система] Verbose режим включен.")
                        elif arg.lower() == "off":
                            verbose = False
                            agent.verbose = False
                            print("[Система] Verbose режим выключен.")
                        else:
                            print("[Система] Используйте: /verbose on | off")
                        continue

                    elif cmd == "/user":
                        if not arg:
                            print("[Система] Используйте: /user <ФИО>")
                            continue

                        print(f"[Система] Ищем пользователя: {arg}...")
                        found = find_user_by_name(arg)

                        if not found:
                            print(f"[Система] ❌ Пользователь '{arg}' не найден (или у него нет детей).")
                            continue

                        requester_id = found["people_id"]
                        save_current_user(found)

                        # СБРОС КОНТЕКСТА
                        messages = [{"role": "system", "content": build_system_prompt(requester_id)}]

                        print(f"\n[Система] ✅ Вы переключились на: {found['name']}")
                        print("[Система] История диалога очищена.")

                        try:
                            children_res = list_children(requester_id)
                            if "children" in children_res and children_res["children"]:
                                print("[Система] Ваши дети:")
                                for c in children_res["children"]:
                                    print(f"  - {c['name']} ({c['class_level']} класс)")
                        except Exception as e:
                            print(f"[Система] Не удалось загрузить список детей: {e}")

                        continue

                    else:
                        print(f"[Система] Неизвестная команда: {cmd}. Введите /help.")
                        continue

                # ОБРАБОТКА ТЕКСТА ДЛЯ LLM
                if not requester_id:
                    print("[Система] Сначала авторизуйтесь: /user <ФИО>")
                    continue

                messages.append({"role": "user", "content": user_input})
                print("\n[Агент думает...]")

                final_response = await agent.run_with_history(messages)

                print(f"\nАгент: {final_response}")
                messages.append({"role": "assistant", "content": final_response})

            except KeyboardInterrupt:
                print("\n\n[Система] Завершение работы по Ctrl+C...")
                break
            except Exception as e:
                print(f"\n[Ошибка]: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        pass