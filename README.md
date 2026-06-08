# Document Analyst — RAG Agent

Agent conversațional care răspunde la întrebări despre documente (facturi, contracte, CSV-uri) folosind RAG (Retrieval-Augmented Generation) cu pgvector și pattern-ul ReAct. Construit peste Tema 1 (QA Agent).

## Cerințe

- Python 3.10+
- Docker (pentru baza de date PostgreSQL cu pgvector)

## Instalare

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copiază `.env.example` în `.env` și completează cheile necesare:

```bash
copy .env.example .env
```

## Configurare bază de date

Pornește containerul PostgreSQL cu pgvector:

```bash
docker-compose up -d
```

Rulează migrațiile (creează tabelele):

```bash
alembic upgrade head
```

## Pornire

Preîncarcă documentele sample în baza de date și pornește interfața:

```bash
python app.py
```

La prima pornire, `seed.py` rulează automat și încarcă documentele din `data-samples-for-chunking/`. Aplicația se deschide la `http://127.0.0.1:7860`.

Pentru a reseta baza de date și reîncărca documentele de la zero:

```bash
python seed.py --fresh
```

## Provideri LLM suportați

| Provider     | Variabilă `.env`     | Model implicit             |
| ------------ | -------------------- | -------------------------- |
| `gemini`     | `GEMINI_API_KEY`     | `gemini-2.5-flash`         |
| `anthropic`  | `ANTHROPIC_API_KEY`  | `claude-sonnet-4-5`        |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-oss-120b:free` |
| `ollama`     | `OLLAMA_MODEL`       | `llama3.2:3b` (local)      |

Schimbă providerul în `.env`:

```
LLM_PROVIDER=gemini
```

> **Notă:** pentru extracția structurată (facturi, contracte) sunt recomandate `gemini` sau `anthropic`. Modelele gratuite de pe OpenRouter pot returna erori la structured output.

## Tipuri de documente suportate

| Tip        | Extensii          | Extracție structurată |
| ---------- | ----------------- | --------------------- |
| `factura`  | TXT, PDF, DOCX    | Da (schema Invoice)   |
| `contract` | TXT, PDF, DOCX    | Da (schema Contract)  |
| `csv`      | CSV               | Nu (doar RAG)         |

## Structura proiectului

```
.
├── app.py                    # Interfață Gradio
├── agent.py                  # QAAgent — ReAct loop cu tool calling
├── pipeline.py               # ExtractionPipeline — load → chunk → extract → embed → store
├── seed.py                   # Preîncărcare documente sample în DB
├── rag_service.py            # RAGService — embeddings + similarity search
├── llm_factory.py            # Factory pentru provideri LLM
├── database.py               # SQLAlchemy engine, sesiuni, context manager tranzacții
├── models.py                 # ORM: Document, DocumentChunk (cu Vector(384))
├── loaders.py                # Loadere documente (PDF, DOCX, TXT, CSV)
├── schemas.py                # Scheme Pydantic pentru extracție (Invoice, Contract)
├── repositories/
│   ├── document_repo.py      # CRUD pentru documente
│   └── chunk_repo.py         # CRUD + similarity search pentru chunk-uri
├── tools/
│   ├── basic_tools.py        # Tool-uri de bază (calculator, datetime, etc.)
│   ├── rag_tools.py          # Tool search_documents pentru RAG
│   ├── params_models.py      # Modele Pydantic pentru parametri tool-uri
│   ├── registry.py           # Decorator @register_tool
│   └── tool_wrapper.py       # ToolWrapper pentru LangChain
├── prompts/
│   ├── planner.yaml          # System prompt agent ReAct
│   └── analyst.yaml          # System prompt analist documente
├── alembic/                  # Migrații bază de date
├── data-samples-for-chunking/ # Documente sample pentru testare
└── .env.example              # Template configurare
```
