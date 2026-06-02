# QA Agent cu ReAct Pattern

Agent conversațional care rezolvă task-uri pas cu pas folosind tools și pattern-ul ReAct (Think → Act → Observe). Suportă mai mulți provideri LLM schimbabili dintr-o singură variabilă în `.env`.

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

## Provideri suportați

| Provider      | Variabilă `.env`           | Model implicit              |
| ------------- | -------------------------- | --------------------------- |
| `ollama`      | `OLLAMA_MODEL`             | `llama3.2:3b` (local)       |
| `gemini`      | `GEMINI_API_KEY`           | `gemini-2.5-flash`          |
| `openrouter`  | `OPENROUTER_API_KEY`       | `openai/gpt-oss-120b:free`  |
| `anthropic`   | `ANTHROPIC_API_KEY`        | `claude-sonnet-4-5`         |

Schimbă providerul activ în `.env`:

```
LLM_PROVIDER=openrouter
```

## Rulare

```bash
python agent.py
```

## Tools disponibile

| Tool           | Descriere                                               |
| -------------- | ------------------------------------------------------- |
| `calculator`   | Calculează expresii matematice                          |
| `get_datetime` | Returnează data și ora curentă                          |
| `web_search`   | Caută informații pe web (simulat)                       |
| `currency`     | Convertește sume între valute (EUR, USD, RON, GBP, CHF) |
| `random_fact`  | Returnează un fapt interesant aleatoriu                 |

## Structura proiectului

```
.
├── agent.py              # Clasa QAAgent — factory, chat, stream, ReAct loop
├── tools/
│   ├── basic_tools.py    # Implementarea tool-urilor (@register_tool + Pydantic)
│   ├── params_models.py  # Modele Pydantic pentru validare parametri
│   ├── registry.py       # Decorator @register_tool + TOOL_REGISTRY
│   ├── tool_wrapper.py   # ToolWrapper: catalog() și catalog_langchain()
│   └── __init__.py
├── prompts/
│   ├── registry.py       # PromptRegistry — încarcă și randează YAML cu Jinja2
│   └── planner.yaml      # System prompt pentru agentul ReAct
├── .env.example          # Template pentru .env
└── requirements.txt      # Dependențe Python
```
