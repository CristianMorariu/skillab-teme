import os
import time
from pathlib import Path

import anthropic
import docx
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path(__file__).parent.parent / "data" / "documents"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def load_documents() -> str:
    """Concatenează documentele reale → prefix static mare (>2048 tokeni)."""
    parts = []
    for f in sorted(DOCS_DIR.glob("*.docx")):
        d = docx.Document(f)
        text = "\n".join(p.text for p in d.paragraphs)
        parts.append(f"=== {f.name} ===\n{text}")
    return "\n\n".join(parts)


client = anthropic.Anthropic()
DOCUMENT = load_documents()

SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": "Ești un analist de documente. Răspunzi pe baza documentelor furnizate.",
    },
    {
        "type": "text",
        "text": DOCUMENT,
        "cache_control": {"type": "ephemeral"},
    },
]


def ask(question: str):
    t0 = time.perf_counter()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_BLOCKS,
        messages=[{"role": "user", "content": question}],
    )
    return resp.usage, time.perf_counter() - t0


def main():
    print("=" * 60)
    print(f"PROMPT CACHING (Anthropic) · model={MODEL}")
    print(f"Prefix static: {len(DOCUMENT)} chars (~{len(DOCUMENT)//4} tokeni)")
    print("=" * 60)

    print("\n→ Apel 1 (MISS — scrie cache-ul):")
    u1, l1 = ask("Care sunt termenii principali din contracte?")
    print(
        f"   creation={u1.cache_creation_input_tokens}  "
        f"read={u1.cache_read_input_tokens}  "
        f"fresh={u1.input_tokens}  latență={l1*1000:.0f}ms"
    )

    print("\n→ Apel 2 (HIT — citește cache-ul):")
    u2, l2 = ask("Există clauze de penalizare în contracte?")
    print(
        f"   creation={u2.cache_creation_input_tokens}  "
        f"read={u2.cache_read_input_tokens}  "
        f"fresh={u2.input_tokens}  latență={l2*1000:.0f}ms"
    )

    cached = u2.cache_read_input_tokens
    if cached:
        print(
            f"\n {cached} tokeni serviți din cache la 0.1x → ~90% reducere pe inputul cache-uit."
        )
        if l2 < l1:
            print(
                f" Latență: {l1*1000:.0f}ms → {l2*1000:.0f}ms ({(1-l2/l1)*100:.0f}% mai rapid)."
            )
    else:
        print("\n cache_read=0 — prefix sub prag sau cache expirat (TTL 5 min).")


if __name__ == "__main__":
    main()
