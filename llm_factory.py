import os

from langchain_core.language_models.chat_models import BaseChatModel


def create_llm(provider: str) -> BaseChatModel:
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
