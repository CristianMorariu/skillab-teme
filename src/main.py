"""
Main - Test agenții cu memorie, router și caching.
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "skillab-py" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from orchestrator import Orchestrator
from skillab import get_llm

_PROVIDER_ALIASES = {"gemini": "google", "ollama": "local"}
_MODEL_ENV_VARS = {
    "google": "GOOGLE_MODEL",
    "anthropic": "ANTHROPIC_MODEL",
    "openai": "OPENAI_MODEL",
    "local": "OLLAMA_MODEL",
}


def _resolve_provider(provider: str | None) -> str | None:
    if not provider:
        return None
    return _PROVIDER_ALIASES.get(provider.lower(), provider.lower())


def _get_model_from_env(provider: str | None) -> str | None:
    resolved = _resolve_provider(provider)
    if not resolved:
        return None
    env_var = _MODEL_ENV_VARS.get(resolved, f"{resolved.upper()}_MODEL")
    return os.getenv("LLM_MODEL") or os.getenv(env_var)


LLM_PROVIDER = _resolve_provider(os.getenv("LLM_PROVIDER"))
LLM_MODEL = _get_model_from_env(os.getenv("LLM_PROVIDER"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)


def _build_analyst(llm):
    from analyst_agent import AnalystAgent
    DATA_DIR = Path(__file__).parent.parent / "data"
    return AnalystAgent(
        tables_config={
            "achizitii_directe": {
                "schema_path": str(DATA_DIR / "nl2sql_agent" / "schema_achizitii_directe.json"),
                "business_path": str(DATA_DIR / "nl2sql_agent" / "business_achizitii_directe.json"),
            },
            "anunturi_initiere": {
                "schema_path": str(DATA_DIR / "nl2sql_agent" / "schema_anunturi_initiere.json"),
                "business_path": str(DATA_DIR / "nl2sql_agent" / "business_anunturi_initiere.json"),
            },
        },
        llm=llm,
    )


def test_memory():
    """Demo memorie persistentă: 2 ture cu același session_id, restart-safe."""
    print("\n" + "=" * 60)
    print("TEST: Conversation Memory (load → invoke → save)")
    print("=" * 60)

    llm = get_llm(provider=LLM_PROVIDER, model=LLM_MODEL)
    orch = Orchestrator(llm=llm)
    session_id = "demo-memory-test"

    print(f"\n--- Tura 1 (session: {session_id}) ---")
    result1 = orch.chat(session_id=session_id, query="Ce contact are DataPro?")
    print(f"Raspuns: {result1.get('answer', '')[:200]}")

    print(f"\n--- Tura 2 (acelasi session_id, referinta la tura 1) ---")
    result2 = orch.chat(session_id=session_id, query="Si ce facturi are firma asta?")
    print(f"Raspuns: {result2.get('answer', '')[:200]}")

    print("\n[OK] Memoria a supravietuit intre ture (salvata in PostgreSQL).")


def test_router():
    """Demo intent router: sklearn classifier trimite la agentul corect."""
    print("\n" + "=" * 60)
    print("TEST: Intent Router (sklearn → Orchestrator / Analyst)")
    print("=" * 60)

    from intent import route
    from state import OrchestratorState

    llm = get_llm(provider=LLM_PROVIDER, model=LLM_MODEL)
    orch = Orchestrator(llm=llm)
    orch_app = orch.build_graph()
    analyst = _build_analyst(llm)

    queries = [
        "Ce contact are DataPro?",
        "Care sunt top 5 furnizori dupa valoare?",
    ]

    for query in queries:
        routing = route(query, llm)
        print(f"\nQuery: {query}")
        print(f"[router] intent={routing['intent']} ({routing['confidence']:.0%}) -> {routing['target']}")

        if routing["target"] == "analyst":
            result = analyst.chat(query)
        else:
            result = orch_app.invoke(OrchestratorState(query=query))

        print(f"Raspuns: {result.get('answer', '')[:200]}...")


if __name__ == "__main__":
    test_memory()
    test_router()
