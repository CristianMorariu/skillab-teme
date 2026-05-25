# QA Agent cu ReAct Pattern

Agent conversațional care rezolvă task-uri pas cu pas folosind tools și pattern-ul ReAct (Think → Act → Observe).

## Instalare

> **Important:** Deschide VS Code direct în folderul `tema-1-qa-agent/` (nu în folderul părinte), altfel VS Code nu va detecta automat interpretorul din venv.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Creează un fișier `.env` în folderul principal:

```
GEMINI_API_KEY=cheia_ta_aici
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
qa-agent/
├── agent.py              # Agentul principal cu bucla ReAct
├── tools/
│   ├── basic_tools.py    # Implementarea tool-urilor
│   ├── params_models.py  # Modele Pydantic pentru validare
│   ├── registry.py       # Decorator @register_tool + ToolWrapper
│   └── __init__.py
├── prompts/
│   ├── registry.py       # PromptTemplate + PromptRegistry
│   ├── planner.yaml      # Prompt principal pentru agentul ReAct
│   ├── analyst.yaml      # Prompt pentru analiza întrebării
│   ├── extract.yaml      # Prompt pentru extragere JSON
│   └── summary.yaml      # Prompt pentru răspuns final
└── .env                  # API key
```
