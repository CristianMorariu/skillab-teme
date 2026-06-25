from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
logging.disable(logging.INFO)

sys.path.insert(0, str(Path(__file__).parent.parent / "skillab-py" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP

from guardrails import (
    AnalystInput,
    GuardrailError,
    OrchestratorInput,
    validate,
)

# ── Rezolvare provider/model LLM (identic cu main.py) ───────────────────────
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


# ── Constructie LAZY a agentilor (cache la nivel de modul) ───────────────────
_analyst = None
_orchestrator_app = None


def _get_analyst():
    """Construiește AnalystAgent o singură dată (NL2SQL pe cele 2 tabele)."""
    global _analyst
    if _analyst is None:
        from skillab import get_llm

        from analyst_agent import AnalystAgent

        data_dir = Path(__file__).parent.parent / "data" / "nl2sql_agent"
        llm = get_llm(provider=LLM_PROVIDER, model=LLM_MODEL)
        _analyst = AnalystAgent(
            tables_config={
                "achizitii_directe": {
                    "schema_path": str(data_dir / "schema_achizitii_directe.json"),
                    "business_path": str(data_dir / "business_achizitii_directe.json"),
                },
                "anunturi_initiere": {
                    "schema_path": str(data_dir / "schema_anunturi_initiere.json"),
                    "business_path": str(data_dir / "business_anunturi_initiere.json"),
                },
            },
            llm=llm,
        )
    return _analyst


def _get_orchestrator_app():
    """Construiește și compilează graful Orchestrator o singură dată."""
    global _orchestrator_app
    if _orchestrator_app is None:
        from skillab import get_llm

        from orchestrator import Orchestrator

        llm = get_llm(provider=LLM_PROVIDER, model=LLM_MODEL)
        _orchestrator_app = Orchestrator(llm=llm).build_graph()
    return _orchestrator_app


# ── Server MCP ──────────────────────────────────────────────────────────────
mcp = FastMCP("skillab-agents")


def _run_analyst(question: str) -> dict:
    """Munca blocantă a agentului (build lazy + invoke + LLM). Rulează pe thread."""
    result = _get_analyst().chat(question)
    return {
        "status": result.get("status", "unknown"),
        "answer": result.get("answer", ""),
    }


@mcp.tool()
async def data_analyst(question: str) -> dict:
    """
    Analizează datele de achiziții publice răspunzând la o întrebare în limbaj
    natural. Generează SQL pe tabelele `achizitii_directe` și `anunturi_initiere`,
    execută planul (query → join/filter) și sintetizează un răspuns.

    Args:
        question: Întrebarea de analiză (ex: "Top 5 furnizori după valoare").
    """
    try:
        valid = validate(AnalystInput, {"question": question})
    except GuardrailError as e:
        return {"status": "blocked", "answer": "", "error": str(e)}

    return await asyncio.to_thread(_run_analyst, valid.question)


def _run_orchestrator(query: str) -> dict:
    """Munca blocantă a Orchestratorului (RAG + LLM). Rulează pe thread."""
    from state import OrchestratorState

    result = _get_orchestrator_app().invoke(OrchestratorState(query=query))

    rag_result = result.get("rag_result")
    sources = []
    if rag_result is not None:
        sources = sorted({r.file_name for r in rag_result.results})

    return {
        "status": result.get("status", "unknown"),
        "answer": result.get("answer", ""),
        "sources": sources,
    }


@mcp.tool()
async def orchestrator(query: str) -> dict:
    """
    Caută în documentele indexate (RAG) și răspunde la o întrebare, sub
    supervizarea unui Orchestrator care reia căutarea dacă rezultatele sunt slabe.

    Args:
        query: Întrebarea de căutat în documente (ex: "Ce contact are DataPro?").
    """
    try:
        valid = validate(OrchestratorInput, {"query": query})
    except GuardrailError as e:
        return {"status": "blocked", "answer": "", "error": str(e)}

    return await asyncio.to_thread(_run_orchestrator, valid.query)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        # Claude Desktop / Claude Code porneste serverul ca subprocess.
        mcp.run()
    else:
        print(
            "MCP server 'skillab-agents' pe http://127.0.0.1:8000/mcp", file=sys.stderr
        )
        print("Tools: data_analyst, orchestrator", file=sys.stderr)
        mcp.run(transport="http", host="127.0.0.1", port=8000)
