"""Безопасный исполнитель Python-кода для LLM"""
import warnings
from typing import Any
from RestrictedPython import compile_restricted, safe_builtins, utility_builtins
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safer_getattr,
)
from RestrictedPython.PrintCollector import PrintCollector

class SandboxExecutor:
    def __init__(self):
        self._globals = {
            "__builtins__": {
                **safe_builtins,
                **utility_builtins,
                "sum": sum, "min": min, "max": max, "len": len,
                "round": round, "abs": abs, "sorted": sorted,
                "str": str, "int": int, "float": float, "list": list, "dict": dict, "set": set,
            },
            "_getiter_": iter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_unpack_sequence_": guarded_unpack_sequence,
            "_getattr_": safer_getattr,
            "_getitem_": lambda obj, index: obj[index],
            "_print_": PrintCollector,
        }

    def execute(self, code: str) -> dict[str, Any]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                byte_code = compile_restricted(code, filename="<sandbox>", mode="exec")
        except SyntaxError as e:
            return {"success": False, "output": "", "error": f"Синтаксическая ошибка: {e}"}

        try:
            exec(byte_code, self._globals)

            output = ""
            if "_print" in self._globals:
                collector = self._globals["_print"]
                if isinstance(collector, PrintCollector):
                    output = collector().strip()

            return {"success": True, "output": output, "error": None}
        except Exception as e:
            output = ""
            if "_print" in self._globals:
                collector = self._globals["_print"]
                if isinstance(collector, PrintCollector):
                    output = collector().strip()

            return {"success": False, "output": output, "error": f"{type(e).__name__}: {e}"}