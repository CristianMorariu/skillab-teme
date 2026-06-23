"""
Compara Intent Classifier (sklearn local) vs LLM pe: accuracy, latenta, cost.
Ruleaza (din radacina):  $env:PYTHONUTF8=1; python src/compare_intent.py
"""

import os
import sys
import time
from pathlib import Path

# path bootstrap (ca in main.py): src/ + skillab-py/src
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "skillab-py" / "src"))

from dotenv import load_dotenv

load_dotenv()

from skillab import get_llm

from intent import detect_intent, detect_intent_llm
from intent_data import TEST_DATA

# --- LLM din .env (acelasi pattern ca main.py) ---
_ALIASES = {"gemini": "google", "ollama": "local"}
_prov = os.getenv("LLM_PROVIDER")
_prov = _ALIASES.get(_prov.lower(), _prov.lower()) if _prov else None
_model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
llm = get_llm(provider=_prov, model=_model)
print(f"LLM: {_prov} / {llm.model}")

# --- pret gpt-4o-mini (USD / 1.000.000 tokeni) ---
PRICE_IN_PER_M, PRICE_OUT_PER_M = 0.15, 0.60
PROMPT_OVERHEAD_TOKENS = 75  # partea fixa a promptului din detect_intent_llm


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 caractere/token


queries = [q for q, _ in TEST_DATA]
truth = [label for _, label in TEST_DATA]


def normalize(out: str) -> str:
    if "search" in out:
        return "search"
    if "analyze" in out:
        return "analyze"
    return out.strip()


# ---------- SKLEARN (instant -> repetam pt medie stabila) ----------
REPEATS = 50
t0 = time.perf_counter()
for _ in range(REPEATS):
    sk_preds = [detect_intent(q)[0] for q in queries]
sk_latency_ms = (time.perf_counter() - t0) / (REPEATS * len(queries)) * 1000
sk_acc = sum(p == t for p, t in zip(sk_preds, truth)) / len(truth)

# ---------- LLM (un apel real per intrebare) ----------
llm_preds, in_tok, out_tok, times = [], 0, 0, []
for q in queries:
    t0 = time.perf_counter()
    out = detect_intent_llm(q, llm)
    times.append(time.perf_counter() - t0)
    llm_preds.append(normalize(out))
    in_tok += PROMPT_OVERHEAD_TOKENS + est_tokens(q)
    out_tok += est_tokens(out)
llm_latency_ms = sum(times) / len(times) * 1000
llm_acc = sum(p == t for p, t in zip(llm_preds, truth)) / len(truth)
llm_cost = (in_tok * PRICE_IN_PER_M + out_tok * PRICE_OUT_PER_M) / 1_000_000

# ---------- RAPORT ----------
print("\n" + "=" * 56)
print(f"COMPARATIE pe {len(queries)} intrebari de test (held-out)")
print("=" * 56)
print(f"{'':16}{'sklearn':>13}{'LLM':>16}")
print(f"{'accuracy':16}{sk_acc:>12.0%}{llm_acc:>16.0%}")
print(f"{'latenta/apel':16}{sk_latency_ms:>10.3f}ms{llm_latency_ms:>13.0f}ms")
print(f"{'cost (set)':16}{'$0.00':>13}{'$'+format(llm_cost, '.5f'):>16}")
print("-" * 56)
speedup = llm_latency_ms / sk_latency_ms if sk_latency_ms else 0
print(f"sklearn ~{speedup:,.0f}x mai rapid, $0 vs LLM.")
print(
    f"La 10.000 apeluri/zi: LLM ~${llm_cost/len(queries)*10000:.2f}/zi vs sklearn $0."
)
