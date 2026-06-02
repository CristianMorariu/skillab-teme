import datetime
import os

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from prompts.registry import PromptRegistry
from tools import ToolWrapper
from tools.registry import TOOL_REGISTRY

load_dotenv()
MAX_ITERATIONS = 10
registry = PromptRegistry("prompts")


class QAAgent:
    """Agent conversational cu istoric si provider switching."""

    def __init__(self, provider: str, system_prompt: str):
        self.provider = provider
        self.llm = self._create_llm(provider)  # factory
        self.llm_with_tools = self.llm.bind_tools(ToolWrapper.catalog_langchain())
        self.system_prompt = system_prompt
        self.history: list[BaseMessage] = []  # lista goala la start

    def _create_llm(self, provider: str) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_ollama import ChatOllama
        from langchain_openai import ChatOpenAI

        providers = {
            "anthropic": lambda: ChatAnthropic(model="claude-sonnet-4-5"),
            "gemini": lambda: ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY")
            ),
            "ollama": lambda: ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ),
            "openrouter": lambda: ChatOpenAI(
                model=os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free"),
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
            ),
        }
        if provider not in providers:
            raise ValueError(
                f"Provider necunoscut: '{provider}'. Disponibili: {list(providers.keys())}"
            )
        return providers[provider]()

    def chat(self, message: str) -> str:
        """Trimite mesaj, primeste raspuns complet, actualizeaza istoricul."""
        user_message = HumanMessage(content=message)
        messages = (
            [SystemMessage(content=self.system_prompt)] + self.history + [user_message]
        )
        response = self.llm.invoke(messages)
        self.history.append(user_message)
        self.history.append(response)
        return response.content

    def stream(self, message: str):
        """Yield chunks pe masura ce vin de la LLM."""
        user_message = HumanMessage(content=message)
        messages = (
            [SystemMessage(content=self.system_prompt)] + self.history + [user_message]
        )

        full_response = ""
        for chunk in self.llm.stream(messages):
            full_response += chunk.content
            yield chunk.content

        self.history.append(user_message)
        self.history.append(AIMessage(content=full_response))

    def get_history(self) -> list[dict]:
        """Returneaza istoricul serializabil."""
        result = []
        for msg in self.history:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
        return result

    def clear_history(self) -> None:
        """Reset complet al conversatiei."""
        self.history = []

    def execute_tool(self, tool_call: dict) -> str:
        name = tool_call["name"]
        args = tool_call["args"]
        if name not in TOOL_REGISTRY:
            return f"Eroare: tool '{name}' nu există."
        try:
            params = TOOL_REGISTRY[name]["params_model"](**args)
            return str(TOOL_REGISTRY[name]["func"](params))
        except Exception as e:
            return f"Eroare la execuția '{name}': {e}"

    @staticmethod
    def _build_tools_description() -> str:
        lines = []
        for tool in ToolWrapper.catalog():
            props = tool["params_schema"].get("properties", {})
            required = tool["params_schema"].get("required", [])
            params = ", ".join(
                f"{k}{'*' if k in required else ''}: {v.get('type', 'any')}"
                for k, v in props.items()
            )
            lines.append(f"- {tool['name']}({params}): {tool['description']}")
        return "\n".join(lines)

    def run_agent(self, question: str) -> str:
        system_prompt = registry.render(
            "planner",
            current_date=datetime.date.today().isoformat(),
            tools_description=self._build_tools_description(),
        )

        self.history.append(HumanMessage(content=question))

        for i in range(MAX_ITERATIONS):
            messages = [SystemMessage(content=system_prompt)] + self.history
            response = self.llm_with_tools.invoke(messages)
            self.history.append(response)

            # print(f"\n[Step {i + 1}] tool_calls: {response.tool_calls}")

            if not response.tool_calls:
                return response.content

            for tool_call in response.tool_calls:
                result = self.execute_tool(tool_call)
                self.history.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        return "Nu am găsit răspunsul în numărul maxim de iterații."


if __name__ == "__main__":
    agent = QAAgent(
        provider=os.getenv("LLM_PROVIDER", "ollama"),
        system_prompt="",
    )

    print(
        f"QA Agent pornit (provider: {agent.provider}). Scrie 'exit' pentru a ieși.\n"
    )
    while True:
        question = input("Tu: ").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue
        answer = agent.run_agent(question)
        print(f"\nAgent: {answer}\n")
