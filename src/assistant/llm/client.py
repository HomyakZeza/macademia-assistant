import os
from openai import OpenAI
from ..config import load_settings


class DeepSeekClient:
    def __init__(self):
        settings = load_settings()
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY не задан в .env")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=0.1,
            )
            return response.choices[0].message.model_dump()
        except Exception as e:
            return {"content": f"Ошибка API: {e}", "tool_calls": None}