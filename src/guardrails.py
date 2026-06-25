"""
guardrails.py — protecția la granița serverului MCP.

Înainte ca un input să ajungă la agent (AnalystAgent / Orchestrator), trece
prin DOUĂ filtre, în ordine:

  1. Input validation (tip · dimensiune · câmpuri permise)
     → modele Pydantic cu `extra="forbid"` (respinge câmpuri necunoscute) +
       constrângeri de lungime (min/max). Asta e cerința "tip, dimensiune,
       câmpuri permise" din brief.

  2. Prompt-injection guard (denylist regex)
     → un set de tipare care semnalează încercări clasice de injection
       ("ignore previous instructions", "system:", exfiltrare de secrete etc.).
       Dacă vreun tipar se potrivește, input-ul e BLOCAT înainte să atingă LLM-ul.

Filozofia: fail-closed. La cea mai mică suspiciune, ridicăm `GuardrailError`,
iar handler-ul MCP o transformă într-un răspuns de eroare clar (nu rulează agentul).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, ValidationError

MAX_QUERY_LEN = 2000
MIN_QUERY_LEN = 3


class AnalystInput(BaseModel):
    """Input permis pentru tool-ul data_analyst. `extra="forbid"` => orice câmp
    în plus (ex. un parametru ascuns trimis de un client ostil) e respins."""

    model_config = {"extra": "forbid"}

    question: str = Field(
        ...,
        min_length=MIN_QUERY_LEN,
        max_length=MAX_QUERY_LEN,
        description="Întrebarea de analiză pe datele tabelare.",
    )


class OrchestratorInput(BaseModel):
    """Input permis pentru tool-ul orchestrator (căutare RAG în documente)."""

    model_config = {"extra": "forbid"}

    query: str = Field(
        ...,
        min_length=MIN_QUERY_LEN,
        max_length=MAX_QUERY_LEN,
        description="Întrebarea de căutat în documente.",
    )


_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?|context)",
        "Încercare de a anula instrucțiunile anterioare",
    ),
    (
        r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?)",
        "Încercare de a ignora instrucțiunile",
    ),
    (
        r"forget\s+(everything|all|your\s+instructions|previous)",
        "Încercare de resetare a contextului",
    ),
    (
        r"\b(system|assistant|developer)\s*:\s*",
        "Injectare de rol fals (system:/assistant:)",
    ),
    (r"<\s*/?\s*(system|im_start|im_end)\b", "Injectare de tag-uri de chat template"),
    (r"you\s+are\s+now\s+(a|an|in)\b", "Încercare de redefinire a personei agentului"),
    (
        r"\b(reveal|show|print|repeat|leak)\b.{0,30}\b(system\s+prompt|instructions|api[\s_-]?key|secret|password)",
        "Încercare de exfiltrare a promptului/secretelor",
    ),
    (r"\bDAN\b|do\s+anything\s+now|jailbreak", "Tipar de jailbreak cunoscut"),
    (r"(drop|delete|truncate)\s+table\b|;\s*--", "Tipar de SQL injection"),
]

_COMPILED = [
    (re.compile(p, re.IGNORECASE | re.DOTALL), reason)
    for p, reason in _INJECTION_PATTERNS
]


class GuardrailError(Exception):
    """Ridicată când un input pică validarea sau e marcat ca prompt injection."""


def check_prompt_injection(text: str) -> None:
    """Rulează denylist-ul regex. Ridică GuardrailError la primul tipar găsit."""
    for pattern, reason in _COMPILED:
        if pattern.search(text):
            raise GuardrailError(f"Prompt injection blocat: {reason}.")


def validate(model: type[BaseModel], data: dict) -> BaseModel:
    """
    Aplică ambele straturi și întoarce modelul validat.

    1. Pydantic: tip + lungime + câmpuri permise (extra="forbid").
    2. Regex injection guard pe fiecare câmp string.

    Ridică GuardrailError cu mesaj lizibil dacă ceva nu trece.
    """
    try:
        validated = model(**data)
    except ValidationError as e:
        problems = "; ".join(
            f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
            for err in e.errors()
        )
        raise GuardrailError(f"Input invalid: {problems}") from e

    for field_name, value in validated.model_dump().items():
        if isinstance(value, str):
            check_prompt_injection(value)

    return validated
