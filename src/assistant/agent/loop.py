import json
from datetime import datetime
from typing import Any
from mcp import ClientSession

from ..llm.client import DeepSeekClient
from ..sandbox.executor import SandboxExecutor

SYSTEM_PROMPT = (
    "Ты — школьный ассистент. Твоя задача — помогать родителям и сотрудникам школы. "
    "Для получения данных всегда используй инструменты.\n\n"

    "ПРАВИЛА ОБЩЕНИЯ:\n"
    "1. НИКОГДА не упоминай названия инструментов, баз данных, JSON, системные поля. "
    "Если данных нет — просто скажи, что их нет в системе, не рассказывай про устройство.\n"
    "2. Отвечай ТОЛЬКО на темы, связанные с учебой. На любые другие вопросы вежливо отказывай.\n"

    "3. ГРАНИЦЫ ЧЕТВЕРТЕЙ (используй для анализа):\n"
    "   - 1 четверть: 01 сентября — 31 октября\n"
    "   - 2 четверть: 01 ноября — 31 декабря\n"
    "   - 3 четверть: 01 января — 31 марта\n"
    "   - 4 четверть: 01 апреля — 31 мая\n"
    "   ПЕРИОД ПО УМОЛЧАНИЮ: Если пользователь не указал период, ВСЕГДА анализируй ТЕКУЩУЮ четверть. "
    "Если в текущей четверти данных мало (она только началась), ответь по тем данным, что есть. "
    "Не расширяй период на предыдущие четверти без прямой просьбы пользователя.\n\n"

    "4. КОГДА СЧИТАТЬ (использовать `execute_python`):\n"
    "   - ЗАПРЕЩЕНО использовать инструмент `execute_python` для общих вопросов (например, 'Как дела?'). "
    "В этом случае дай качественную, описательную характеристику на основе текстовых комментариев, "
    "статусов домашек и фактов посещаемости.\n"
    "   - ИСПОЛЬЗУЙ `execute_python` ТОЛЬКО если пользователь ПРЯМО просит числа: "
    "('какой средний балл', 'сколько пропусков', 'процент выполнения').\n"
    "   - В коде для execute_python всегда используй print().\n\n"

    "5. СТРУКТУРА ОТВЕТА НА ОБЩИЙ ВОПРОС 'Как дела?' (BR-16):\n"
    "   - Сначала: 'Что было хорошо' (посещаемость, положительные комментарии, хорошие отметки словами).\n"
    "   - Потом: 'Что можно улучшить' (пропуски, долги по домашкам, замечания).\n"
    "   - В конце: краткий абзац (1-2 предложения) с изученными темами за период.\n"
    "   - НЕ ВЫВАЛИВАЙ сухие цифры без просьбы. Пиши как друг семьи: 'Успеваемость стабильная', "
    "'Есть трудности с домашними заданиями по математике'.\n\n"

    "6. Если в комментарии к тесту в начале стоит '--', это переписанная работа. "
    "Показывай её в истории, но при подсчете четвертной (если попросят) не включай её. "
    "Ориентируйся на поле 'is_significant'."
)


class AgentLoop:
    """
    Оркестратор: LLM + MCP + Sandbox
    """
    def __init__(
            self,
            llm: DeepSeekClient,
            sandbox: SandboxExecutor,
            mcp_session: ClientSession,
            max_steps: int = 10,
            verbose: bool = False,
    ):
        self.llm = llm
        self.sandbox = sandbox
        self.mcp_session = mcp_session
        self.max_steps = max_steps
        self.verbose = verbose
        self._tools_schema: list[dict] | None = None

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    async def _load_tools(self) -> list[dict]:
        if self._tools_schema is not None:
            return self._tools_schema

        mcp_tools = await self.mcp_session.list_tools()
        schema = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema,
                },
            }
            for t in mcp_tools.tools
        ]

        schema.append({
            "type": "function",
            "function": {
                "name": "execute_python",
                "description": (
                    "Выполняет Python-код для точных вычислений (только когда просят числа). "
                    "ОБЯЗАТЕЛЬНО выводи результат через print()."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python-код для выполнения с вызовом print()",
                        },
                    },
                    "required": ["code"],
                },
            },
        })

        self._tools_schema = schema
        return schema

    async def _execute_tool(self, tool_name: str, args: dict) -> Any:
        if tool_name == "execute_python":
            return self.sandbox.execute(args["code"])

        mcp_res = await self.mcp_session.call_tool(tool_name, args)
        text_content = mcp_res.content[0].text

        try:
            return json.loads(text_content)
        except json.JSONDecodeError:
            return {"error": text_content}

    async def run(self, user_query: str, requester_people_id: str) -> dict:
        tools_schema = await self._load_tools()

        # Текущая дата
        current_date = datetime.now().strftime("%Y-%m-%d")

        system_content = (
            f"{SYSTEM_PROMPT}\n\n"
            f"СЕГОДНЯШНЯЯ ДАТА: {current_date}\n"
            f"requester_people_id твоего пользователя: {requester_people_id}. "
            f"Если нужно узнать, о каких детях идёт речь, сначала вызови list_children "
            f"с этим ID, затем используй child_people_id из результата."
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_query},
        ]
        return await self._run_loop(messages, tools_schema)

    async def run_with_history(self, messages: list[dict]) -> str:
        tools_schema = await self._load_tools()
        result = await self._run_loop(messages, tools_schema)
        return result.get("final_response", "")

    async def _run_loop(self, messages: list[dict], tools_schema: list[dict]) -> dict:
        for step in range(1, self.max_steps + 1):
            self._log(f"\n--- Шаг {step} ---")
            response = self.llm.chat(messages, tools=tools_schema)
            messages.append(response)

            tool_calls = response.get("tool_calls")
            if not tool_calls:
                if response.get("content"):
                    self._log(f"LLM: {response['content']}")
                return {
                    "final_response": response.get("content") or "",
                    "messages": messages,
                    "steps": step,
                }

            if response.get("content"):
                self._log(f"LLM (промежуточный): {response['content']}")

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                self._log(f"Инструмент: {func_name}({list(args.keys())})")

                try:
                    result = await self._execute_tool(func_name, args)
                    self._log(f"  Результат: {str(result)[:150]}...")
                except Exception as e:
                    result = {"error": str(e)}
                    self._log(f"  Ошибка: {e}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return {
            "final_response": "Не удалось завершить за отведённое число шагов",
            "messages": messages,
            "steps": self.max_steps,
        }