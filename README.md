# FitZone Chatbot

Scoped fitness & nutrition AI agent with RAG over training PDFs, live food data, and Groq LLM.

## Features

- **Intent router** — blocks non-fitness questions
- **Safety layer** — crisis escalation + medical boundary guardrails
- **RAG** — Jeff Nippard programs, Research Hub, `gym_calculations.txt`
- **Open Food Facts** — live nutrition lookups
- **Conversation memory** — multi-turn chat context
- **Streaming UI** — Streamlit test app with rate limiting
- **Structured logging** — `logs/fitzone.log`

## Quick start

```powershell
cd "FitZone Chatbot"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set GROQ_API_KEY
```

### Build knowledge index (first time or after adding PDFs)

```powershell
python scripts/rebuild_knowledge.py
```

### Health check

```powershell
python healthcheck.py
```

### Run test UI

```powershell
streamlit run streamlit_app.py
```

### Run tests

```powershell
pytest tests/ -v
```

## Project structure

```
FitZone Chatbot/
├── config.py              # Central settings
├── fitness_agent.py       # Main agent (router + RAG + Groq)
├── safety.py              # Crisis & medical guardrails
├── input_validation.py    # Input limits & injection filter
├── knowledge_retriever.py # PDF + calculations index
├── open_food_facts.py     # Nutrition API client
├── streamlit_app.py       # Local test UI
├── healthcheck.py         # Startup verification
├── scripts/
│   └── rebuild_knowledge.py
├── tests/
├── Knowledge_db/          # PDF books + gym_calculations.txt
├── .cache/                # Indexed knowledge (auto-generated)
└── logs/                  # Request logs
```

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Required. Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Main coach model |
| `GROQ_FAST_MODEL` | `llama-3.1-8b-instant` | Intent classifier |
| `LLM_TEMPERATURE` | `0.4` | Response creativity |
| `RETRIEVAL_TOP_K` | `5` | RAG chunks per query |
| `MAX_MESSAGE_LENGTH` | `2000` | Input char limit |
| `MAX_HISTORY_TURNS` | `10` | Chat memory depth |
| `RATE_LIMIT_PER_SESSION` | `30` | Streamlit session cap |

## Adding knowledge

1. Drop PDF files into `Knowledge_db/`
2. Run `python scripts/rebuild_knowledge.py`
3. Restart the app

## Python API (for your frontend / future Render API)

```python
from fitness_agent import ChatTurn, run_agent_full, stream_agent

# Simple
answer = run_agent("What is my BMR if I'm 85kg, 180cm, 30 years old?")

# With memory
history = [
    ChatTurn("user", "I'm cutting on 2200 calories"),
    ChatTurn("assistant", "Solid deficit — let's make sure protein is high enough."),
]
response = run_agent_full("How much protein should I aim for?", history=history)
print(response.text, response.latency_ms)

# Streaming
for token in stream_agent("Best back exercises?", history=history):
    print(token, end="")
```

## Render.com API deployment

The FastAPI service lives in `api.py` and is ready for Render:

1. `POST /v1/chat` accepts a message plus optional conversation history and returns a JSON response.
2. `POST /v1/chat/stream` streams plain-text output for clients that want incremental tokens.
3. `GET /health` reports readiness after startup warmup.
4. Requests must include `X-API-Key` matching `FITZONE_API_KEY`.

Render settings are already captured in `render.yaml`:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: uvicorn api:app --host 0.0.0.0 --port $PORT
healthCheckPath: /health
```

Required Render env vars:

- `GROQ_API_KEY`
- `FITZONE_API_KEY`
- Optional model tuning vars like `GROQ_MODEL`, `GROQ_FAST_MODEL`, and `LLM_TEMPERATURE`

For local API testing:

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Disclaimer

FitZone provides general fitness and nutrition education — not medical advice. Always consult a qualified healthcare professional for medical decisions.
