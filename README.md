# Multi-Agent System + Optimizări

Sistem multi-agent cu două sub-sisteme, optimizat cu memorie conversațională, prompt caching și un intent classifier care rutează între ele.

1. **Orchestrator + RAG** — caută în documente (facturi, contracte, clienți)
2. **Analyst + NL2SQL** — query-uri SQL pe datele SEAP (achiziții, anunțuri)
3. **Intent Router** — decide automat care sub-sistem răspunde

## Arhitectură

### 1. Orchestrator + RAG (Hierarchical Multi-Agent)

```
┌──────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                               │
│                        (Supervizor)                               │
│                                                                   │
│    ┌──────────┐      ┌──────────┐      ┌────────┐                │
│    │ call_rag │ ───► │ evaluate │ ───► │ answer │ ───► END       │
│    └──────────┘      └──────────┘      └────────┘                │
│         ▲                  │                                      │
│         │                  │ can_answer=false                     │
│         │                  │ + feedback                           │
│         └──────────────────┘                                      │
│                                                                   │
│    max 3 iterații                                                 │
└──────────────────────────────────────────────────────────────────┘
         │                   ▲
         │ query +           │ RAGSearchResult
         │ feedback          │
         ▼                   │
┌──────────────────────────────────────────────────────────────────┐
│                         RAG AGENT                                 │
│                         (Worker)                                  │
│                                                                   │
│    ┌────────┐      ┌────────┐                                    │
│    │ refine │ ───► │ search │ ───► END                           │
│    └────────┘      └────────┘                                    │
│                                                                   │
│    refine: dacă are feedback, rafinează query-ul                 │
│    search: caută în pgvector, returnează chunks                  │
└──────────────────────────────────────────────────────────────────┘
```

**Flow:**
1. Orchestrator apelează RAG Agent cu query
2. RAG Agent caută și returnează chunks
3. Orchestrator evaluează: "Pot răspunde?"
4. Dacă NU → trimite feedback, RAG Agent rafinează și caută din nou
5. Dacă DA → generează răspuns final

**Prompturi:** `rag_evaluate.yaml`, `rag_answer.yaml`, `rag_refine.yaml`

### 2. Analyst + NL2SQL (Hierarchical Multi-Agent)

```
┌──────────────────────────────────────────────────────────────────┐
│                      ANALYST AGENT                                │
│                      (Supervizor)                                 │
│                                                                   │
│    ┌───────────┐      ┌──────────────┐      ┌─────────────┐      │
│    │ make_plan │ ───► │ execute_step │ ───► │ synthesize  │──►END │
│    └───────────┘      └──────────────┘      └─────────────┘      │
│                              │  ▲                                 │
│                              └──┘ loop                            │
│                                                                   │
│    Plan: [QueryStep, QueryStep, ToolStep, ...]                    │
│    Slices: {"q1": DataFrame, "q2": DataFrame, "joined": DataFrame}│
└──────────────────────────────────────────────────────────────────┘
           │                              │
           │ QueryStep                    │ ToolStep
           ▼                              ▼
┌──────────────────────────────┐    ┌─────────────────────────┐
│        NL2SQL AGENT          │    │      TOOL REGISTRY      │
│         (Worker)             │    │                         │
│                              │    │  join_data(dfs, keys)   │
│  get_context                 │    │  filter_data(df, cond)  │
│      │                       │    │                         │
│      ▼                       │    └─────────────────────────┘
│  generate_sql                │
│      │                       │
│      ▼                       │
│  validate_sql ───┬───► execute_sql ───┬───► END (success)
│                  │           │        │
│                  │ invalid   │ error  │
│                  ▼           ▼        │
│             handle_error ◄────────────┘
│                  │
│            retry < max?
│             yes │ no
│                 ▼  ▼
│         generate_sql  END (failed)
└──────────────────────────────┘
```

**Flow Analyst:** `make_plan` (LLM generează plan cu QueryStep/ToolStep) → `execute_step` (rulează fiecare pas: query → NL2SQL, tool → join/filter, rezultat în `slices[id]`) → `synthesize` (răspuns final din rezultate).

**Flow NL2SQL:** `get_context` (schema tabelului) → `generate_sql` → `validate_sql` (sqlparse) → `execute_sql` (DataFrame) → la eroare `handle_error` corectează SQL-ul și reîncearcă (retry < max).

**Prompturi:** `analyst_plan.yaml`, `analyst_synthesize.yaml`, `nl2sql_generate.yaml`, `nl2sql_error.yaml`

---

## Optimizări (Tema 4)

Trei optimizări peste sistemul multi-agent.

### 1. Conversation Memory (persistată în Postgres)

Context conversațional persistent între request-uri, salvat în Postgres (supraviețuiește restart-ului).

- Tabel `chat_messages` (`session_id`, `role`, `content`, `created_at`) — migrația `alembic/versions/004_create_chat_messages.py`.
- `src/memory.py`: `ChatMessageRepository` (add / latest) + `PersistentMemory` (load → invoke → save, fereastră de 10 mesaje).
- Integrat în ambii agenți prin `chat(session_id, query)`; promptul de răspuns randează istoricul.
- **Demo:** `test_memory()` în `main.py` — două ture cu același `session_id`, a doua referindu-se la prima.

### 2. Prompt Caching (Anthropic)

Prefixul static mare (system + documente reale din `data/documents/`) e marcat `cache_control: ephemeral`. Primul apel scrie cache-ul, următoarele îl citesc la 0.1x.

- **Livrabil:** `scripts/prompt_caching.py` — măsoară economia reală (nu o afirmă).
- Apel 1 (MISS): `cache_creation > 0`. Apel 2 (HIT): `cache_read > 0` → ~90% reducere pe inputul cache-uit.
- Necesită `ANTHROPIC_API_KEY` în `.env`. Prag minim de cache: 2048 tokeni (familia Claude 4.x).

### 3. Intent Classifier (scikit-learn) ca router

Router local `search` (→ Orchestrator/RAG) / `analyze` (→ Analyst/NL2SQL). Înlocuiește un apel LLM de routing cu un clasificator TF-IDF + LogisticRegression; cade pe LLM doar când confidence < 0.6.

- `src/intent_data.py`: date de antrenare + test (held-out).
- `scripts/train_intent.py`: antrenează și salvează `models/intent_classifier.joblib`.
- `src/intent.py`: `detect_intent` (local) + `route` (cu fallback LLM).
- **Demo:** `test_router()` în `main.py`.
- **Comparație:** `scripts/compare_intent.py` — LLM vs sklearn pe accuracy, latență, cost.

---

## MCP & Guardrails (Tema 5)

Cei doi agenți sunt expuși ca **tool-uri MCP** într-un singur server, protejat de guardrails la intrare.

### Server MCP cu două tool-uri

`src/mcp_server.py` (FastMCP) expune:

| Tool | Apelează | Input → Output |
|------|----------|----------------|
| `data_analyst(question)` | `AnalystAgent` (NL2SQL + plan) | `question` → `{status, answer}` |
| `orchestrator(query)` | `Orchestrator` (RAG supervizat) | `query` → `{status, answer, sources}` |

Agenții se construiesc **lazy** (la primul apel), ca pornirea serverului și `tools/list` să meargă chiar fără DB pornit. Tool-urile sunt `async` și împing munca blocantă a agentului pe un thread (`asyncio.to_thread`), ca să nu intre în conflict cu event-loop-ul serverului (agenții folosesc `generate_sync` cu loop propriu).

```bash
python src/mcp_server.py            # HTTP pe http://127.0.0.1:8000/mcp (recomandat)
python src/mcp_server.py stdio      # STDIO (vezi nota de mai jos)
```

> **Notă transport:** pe Windows, stdio se blochează cu acest workload (deadlock în pipe-urile asyncio subprocess + loop-urile imbricate din `generate_sync`). **Folosește HTTP** — e și transportul recomandat în materialul L10.

### Guardrails (la granița serverului, înainte de agent)

`src/guardrails.py` — fiecare input trece prin două filtre, **fail-closed**:

1. **Input validation** (Pydantic): tip + dimensiune (3–2000 caractere) + câmpuri permise (`extra="forbid"` respinge orice câmp necunoscut).
2. **Prompt-injection guard** (denylist regex): blochează „ignore previous instructions", roluri false (`system:`), exfiltrare de secrete, jailbreak (DAN), SQL injection etc.

La orice violare se întoarce `{status: "blocked", error: ...}` — agentul nu mai e apelat (nu se cheltuie LLM/DB).

### Testare din Claude Code (HTTP)

`.mcp.json` (project-scoped, HTTP) e deja configurat. Pașii:

```bash
# 1. Pornește DB-ul temei (Postgres pe 5433)
docker start tema-3-orchestrator-postgres-1      # sau: docker-compose up -d

# 2. Pornește serverul MCP — lasă terminalul deschis (moare dacă îl închizi)
python src/mcp_server.py

# 3. În Claude Code: ar trebui să apară conectat
claude mcp list                                  # skillab-agents ✓ connected
# apoi întreabă în chat: "Folosește data_analyst pentru top 5 furnizori după valoare"
```

Primul apel durează ~20s (lazy-init: model embeddings + DB + LLM); următoarele sunt mai rapide.

---

## Setup (o singură dată)

```bash
# 1. Dependențe
pip install -r requirements.txt
pip install -e skillab-py

# 2. Bază de date (Postgres + pgvector pe portul 5433)
docker-compose up -d
alembic upgrade head

# 3. Restaurează datele (694k achiziții, 8k anunțuri, 135 chunks RAG)
docker exec -i skillab-teme-postgres-1 pg_restore -U demo -d rag_demo --data-only < data/rag_demo.dump

# 4. Variabile de mediu
cp .env.example .env
#   - LLM_PROVIDER + cheia aferentă (agenții rulează pe acest provider)
#   - ANTHROPIC_API_KEY  (necesar doar pentru prompt caching)
```

## Ce rulezi și în ce ordine

```bash
# 1. OBLIGATORIU ÎNTÂI — antrenează classifier-ul.
#    main.py și compare_intent.py importă modelul la pornire; fără el crapă.
python scripts/train_intent.py

# 2. Demo agenți + memorie + router (din src/)
cd src && python main.py        # rulează test_memory() + test_router()

# 3. Demo prompt caching (necesită ANTHROPIC_API_KEY)
python scripts/prompt_caching.py

# 4. Comparație intent classifier: LLM vs sklearn
python scripts/compare_intent.py
```

## Structură

```
├── .mcp.json                 # Config MCP project-scoped pt Claude Code (Tema 5)
├── alembic/                  # Migrații DB (004 = chat_messages)
├── data/
│   ├── documents/            # DOCX-uri reale (prefix pentru prompt caching)
│   └── rag_demo.dump         # Dump date SEAP + chunks
├── models/                   # intent_classifier.joblib (generat de train_intent.py)
├── prompts/                  # YAML prompts
├── scripts/
│   ├── prompt_caching.py     # Demo prompt caching (Tema 4)
│   ├── train_intent.py       # Antrenează intent classifier (Tema 4)
│   ├── compare_intent.py     # Comparație LLM vs sklearn (Tema 4)
│   └── seed_*.py             # Seed DB
├── skillab-py/               # Pachet local: LLM provider switching, prompts, tools
└── src/
    ├── database.py           # Connection + transaction
    ├── models.py             # SQLAlchemy models (+ ChatMessage)
    ├── repositories.py       # Repository pattern
    ├── rag_service.py        # pgvector search service
    ├── memory.py             # Conversation memory (Tema 4)
    ├── intent.py             # Intent inference + router (Tema 4)
    ├── intent_data.py        # Date antrenare/test classifier (Tema 4)
    ├── state.py              # Pydantic states (+ history)
    ├── rag_agent.py          # RAG worker
    ├── orchestrator.py       # Orchestrator + chat(session_id)
    ├── nl2sql_agent.py       # NL2SQL worker
    ├── analyst_agent.py      # Analyst + chat(session_id)
    ├── guardrails.py         # Input validation + anti prompt-injection (Tema 5)
    ├── mcp_server.py         # Server MCP: data_analyst + orchestrator (Tema 5)
    └── main.py               # test_memory(), test_router()
```

## Plan format (Analyst)

LLM-ul generează un plan JSON cu pași `query` (NL2SQL) și `tool` (join/filter):

```json
[
  {"id": "q1", "action": "query", "table": "achizitii", "sub_question": "..."},
  {"id": "q2", "action": "query", "table": "anunturi", "sub_question": "..."},
  {"id": "joined", "action": "tool", "tool_name": "join_data", "input_steps": ["q1", "q2"], "params": {"left_key": "cui", "right_key": "cui"}},
  {"id": "result", "action": "tool", "tool_name": "filter_data", "input_steps": ["joined"], "params": {"column": "valoare", "operator": ">", "value": "50000"}}
]
```

Rezultatele intermediare se acumulează în `state.slices["q1"]`, `state.slices["joined"]`, etc.
