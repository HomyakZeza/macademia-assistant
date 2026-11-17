import asyncio
import json
import sys
import warnings
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

warnings.filterwarnings("ignore", category=DeprecationWarning)

if sys.platform == "win32":
    policy = (
            getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
            or getattr(asyncio, "_WindowsSelectorEventLoopPolicy", None)
    )
    if policy:
        asyncio.set_event_loop_policy(policy())

from ..agent.loop import AgentLoop
from ..agent.runner import mcp_stdio_session
from ..llm.client import DeepSeekClient
from ..sandbox.executor import SandboxExecutor
from ..config import load_settings
from ..mcp_server.db import get_pg_connection
from ..mcp_server.tools.students import list_children

console = Console()
CURRENT_USER_FILE = Path("data/output/.current_user.json")


def find_user_by_name(name: str) -> dict | None:
    settings = load_settings()
    if not settings.postgres_dsn:
        console.print("[red]PostgreSQL не настроен (POSTGRES_DSN).[/red]")
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
        console.print(f"[red]Ошибка при поиске в PostgreSQL: {e}[/red]")
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


async def interactive_loop():
    console.print("[bold cyan]============================================================[/bold cyan]")
    console.print("[bold cyan]🤖 Macademia Assistant (эмуляция Matrix-бота)[/bold cyan]")
    console.print("[bold cyan]Введите /help для списка команд.[/bold cyan]")
    console.print("[bold cyan]============================================================[/bold cyan]\n")

    current_user = load_current_user()

    if current_user:
        console.print(
            f"[green][Система] Вы вошли как: {current_user['name']} (ID: {current_user['people_id']})[/green]")
        requester_id = current_user["people_id"]
    else:
        console.print("[yellow][Система] Вы не авторизованы. Введите `/user <ФИО>` для входа.[/yellow]")
        requester_id = None

    messages = []
    verbose = True

    async with mcp_stdio_session() as mcp_session:
        agent = None
        if requester_id:
            agent = AgentLoop(
                llm=DeepSeekClient(),
                sandbox=SandboxExecutor(),
                mcp_session=mcp_session,
                requester_people_id=requester_id,
                verbose=verbose,
            )

        while True:
            try:
                user_input = await asyncio.to_thread(console.input, "\n[bold]Вы:[/bold] ")
                user_input = user_input.strip()

                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "выход"):
                    console.print("[yellow]До свидания![/yellow]")
                    break

                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    cmd = parts[0].lower()
                    arg = parts[1] if len(parts) > 1 else ""

                    if cmd == "/help":
                        console.print("\n[cyan][Система] Доступные команды:[/cyan]")
                        console.print("  /user <ФИО>     - переключиться на другого пользователя (сброс контекста)")
                        console.print("  /verbose on|off - включить/выключить показ шагов агента")
                        console.print("  /help           - показать это сообщение")
                        console.print("  exit            - выйти")
                        continue

                    elif cmd == "/verbose":
                        if arg.lower() == "on":
                            verbose = True
                            if agent: agent.verbose = True
                            console.print("[green][Система] Verbose режим включен.[/green]")
                        elif arg.lower() == "off":
                            verbose = False
                            if agent: agent.verbose = False
                            console.print("[green][Система] Verbose режим выключен.[/green]")
                        else:
                            console.print("[red][Система] Используйте: /verbose on | off[/red]")
                        continue

                    elif cmd == "/user":
                        if not arg:
                            console.print("[red][Система] Используйте: /user <ФИО>[/red]")
                            continue

                        console.print(f"[yellow][Система] Ищем пользователя: {arg}...[/yellow]")
                        found = find_user_by_name(arg)

                        if not found:
                            console.print(
                                f"[red][Система] ❌ Пользователь '{arg}' не найден (или у него нет детей).[/red]")
                            continue

                        requester_id = found["people_id"]
                        save_current_user(found)

                        # СБРОС КОНТЕКСТА
                        messages = []

                        agent = AgentLoop(
                            llm=DeepSeekClient(),
                            sandbox=SandboxExecutor(),
                            mcp_session=mcp_session,
                            requester_people_id=requester_id,
                            verbose=verbose,
                        )

                        console.print(f"\n[green][Система] ✅ Вы переключились на: {found['name']}[/green]")
                        console.print("[green][Система] История диалога очищена.[/green]")

                        try:
                            children_res = list_children(requester_id)
                            if "children" in children_res and children_res["children"]:
                                console.print("[cyan][Система] Ваши дети:[/cyan]")
                                for c in children_res["children"]:
                                    console.print(f"  - {c['name']} ({c['class_level']} класс)")
                        except Exception as e:
                            console.print(f"[red][Система] Не удалось загрузить список детей: {e}[/red]")
                        continue

                    else:
                        console.print(f"[red][Система] Неизвестная команда: {cmd}. Введите /help.[/red]")
                        continue

                if not requester_id or not agent:
                    console.print("[red][Система] Сначала авторизуйтесь: /user <ФИО>[/red]")
                    continue

                messages.append({"role": "user", "content": user_input})
                console.print("\n[yellow][Агент думает...][/yellow]")

                final_response = await agent.run_with_history(messages)

                console.print("\n[bold green]Агент:[/bold green]")
                console.print(Markdown(final_response))

            except KeyboardInterrupt:
                console.print("\n[yellow][Система] Завершение работы по Ctrl+C...[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red][Ошибка]: {e}[/red]")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        pass