import json
from typing import Any

from mcp import ClientSession

from ..llm.client import DeepSeekClient
from ..sandbox.executor import SandboxExecutor


SYSTEM_PROMPT = (
    "Ты — школьный ассистент для родителей. Твоя задача — помогать родителям "
    "узнавать информацию об успеваемости и посещаемости их детей. "
    "Для получения данных всегда используй инструменты (tools). "
    "ВАЖНО: ты плохо считаешь в уме. Для ЛЮБЫХ вычислений (средние, проценты, суммы) "
    "ты ОБЯЗАН использовать инструмент `execute_python`. "
    "В коде для execute_python всегда используй print(), чтобы результат был виден. "
    "Не используй import в коде, не оставляй просто переменные в конце — только print()."
)


class AgentLoop:
    """
    Оркестратор: LLM + MCP + Sandbox
    Принимает уже инициализированную MCP-сессию (ClientSession)
    Возвращает финальный ответ LLM и полную историю сообщений
    """
    def __init__(
        self,
        llm: DeepSeekClient,
        sandbox: SandboxExecutor,
        mcp_session: ClientSession,
        max_steps: int = 5,
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
                    "Выполняет Python-код для точных вычислений. "
                    "ОБЯЗАТЕЛЬНО выводи результат через print(). "
                    "Пример: print('Средний балл:', sum(grades)/len(grades))"
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
        return json.loads(mcp_res.content[0].text)

    async def run(
        self,
        user_query: str,
        requester_people_id: str,
    ) -> dict:
        tools_schema = await self._load_tools()

        system_content = (
            f"{SYSTEM_PROMPT}\n\n"
            f"requester_people_id твоего пользователя: {requester_people_id}. "
            f"Если нужно узнать, о каких детях идёт речь, сначала вызови list_children "
            f"с этим ID, затем используй child_people_id из результата."
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_query},
        ]

        for step in range(1, self.max_steps + 1):
            self._log(f"\n--- Шаг {step} ---")
            response = self.llm.chat(messages, tools=tools_schema)
            messages.append(response)

            if response.get("content"):
                self._log(f"LLM: {response['content']}")

            tool_calls = response.get("tool_calls")
            if not tool_calls:
                return {
                    "final_response": response.get("content") or "",
                    "messages": messages,
                    "steps": step,
                }

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                self._log(f"Инструмент: {func_name}({list(args.keys())})")

                try:
                    result = await self._execute_tool(func_name, args)
                except Exception as e:
                    result = {"error": str(e)}

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

    async def run_with_history(self, messages: list[dict]) -> str:
        tools_schema = await self._load_tools()

        for step in range(1, self.max_steps + 1):
            self._log(f"\n--- Шаг {step} ---")
            response = self.llm.chat(messages, tools=tools_schema)
            messages.append(response)

            tool_calls = response.get("tool_calls")
            if not tool_calls:
                return response.get("content") or ""

            if response.get("content"):
                self._log(f"LLM: {response['content']}")


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

        return "Не удалось завершить за отведённое число шагов"