"""
Intent inference + router.
Inlocuieste apelul LLM de routing cu un clasificator local; cade pe LLM doar la confidence mic.
"""

from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "intent_classifier.joblib"

_classifier = joblib.load(MODEL_PATH)

CONFIDENCE_THRESHOLD = 0.6


ROUTING = {
    "search": "orchestrator",
    "analyze": "analyst",
}


def detect_intent(query: str) -> tuple[str, float]:
    """Clasificator local: query -> (intent, confidence). ~ms, $0."""
    intent = _classifier.predict([query])[0]
    confidence = max(_classifier.predict_proba([query])[0])
    return intent, confidence


def detect_intent_llm(query: str, llm) -> str:
    """Fallback scump: intrebam LLM-ul cand clasificatorul nu e sigur."""
    prompt = (
        "Clasifica intentia intrebarii in EXACT una din:\n"
        "- search: cauta informatii in documente (facturi, contracte, clienti, rapoarte)\n"
        "- analyze: calcule pe date (achizitii/anunturi: sume, top, medii, numarari)\n\n"
        f"Intrebare: {query}\n"
        "Raspunde DOAR cu un cuvant: search sau analyze."
    )
    return llm.generate_sync([{"role": "user", "content": prompt}]).strip().lower()


def route(query: str, llm=None) -> dict:
    """Decide ce agent raspunde. Foloseste clasificatorul; cade pe LLM la confidence mic."""
    intent, confidence = detect_intent(query)
    used_llm_fallback = False

    if confidence < CONFIDENCE_THRESHOLD and llm is not None:
        intent = detect_intent_llm(query, llm)
        used_llm_fallback = True

    return {
        "intent": intent,
        "confidence": confidence,
        "target": ROUTING.get(intent, "orchestrator"),
        "used_llm_fallback": used_llm_fallback,
    }
