from .registry import TOOL_REGISTRY


class ToolWrapper:
    @staticmethod
    def call(name: str, args: dict) -> str:
        # 1. Lookup în registry
        if name not in TOOL_REGISTRY:
            return f"Eroare: tool '{name}' nu există."

        tool = TOOL_REGISTRY[name]

        # 2. Validate — Pydantic verifică tipuri și constrângeri
        try:
            params = tool["params_model"](**args)
        except Exception as e:
            return f"Eroare validare pentru '{name}': {e}"

        # 3. Execute + 4. Return
        try:
            return str(tool["func"](params))
        except Exception as e:
            return f"Eroare execuție '{name}': {e}"

    @staticmethod
    def catalog() -> list[dict]:
        return [
            {
                "name": name,
                "description": tool["description"],
                "params_schema": tool["params_model"].model_json_schema(),
            }
            for name, tool in TOOL_REGISTRY.items()
        ]

    @staticmethod
    def catalog_langchain() -> list:
        from langchain_core.tools import StructuredTool

        return [
            StructuredTool.from_function(
                func=tool["func"],
                name=name,
                description=tool["description"],
                args_schema=tool["params_model"],
            )
            for name, tool in TOOL_REGISTRY.items()
        ]
