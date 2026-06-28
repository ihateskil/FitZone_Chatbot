---
title: FitZone Chatbot
emoji: 💪
colorFrom: green
colorTo: gray
sdk: docker
app_file: src/api.py
pinned: false
---

<p align="center">
  <img src="https://img.shields.io/badge/tests-120%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/LLM-Groq%20LLaMA%203.3%2070B-orange" alt="LLM">
  <img src="https://img.shields.io/badge/API-FastAPI-teal" alt="FastAPI">
  <img src="https://img.shields.io/badge/knowledge-43%20files-8A2BE2" alt="Knowledge Base">
  <img src="https://img.shields.io/badge/graph-742%20nodes%20%7C%201628%20edges-blueviolet" alt="Knowledge Graph">
</p>

<h1 align="center">🏋️ FitZone AI — Elite Fitness & Nutrition Coach</h1>

<p align="center">
  <em>A production-grade AI coach that knows you better than you know yourself — persistent user profiles, weekly trend analysis, adaptive nutrition & training recommendations, and a 742-node knowledge graph connecting 43 source files.</em>
</p>

---

## Anatomy of the System

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  Streamlit UI / cURL / React / Any HTTP client                      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ POST /v1/chat | X-API-Key
┌───────────────────────────▼─────────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ /v1/chat │ │ /v1/lift │ │ /v1/rec  │ │ /v1/per- │ │ /health  │  │
│  │ /stream  │ │ /history │ │ -overy   │ │ -onalities│ │ /ready   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────┘  │
└───────┼────────────┼────────────┼────────────┼──────────────────────┘
        │            │            │            │
┌───────▼────────────▼────────────▼────────────▼──────────────────────┐
│                     INTELLIGENCE LAYER                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   FITNESS AGENT (LLM Orchestrator)          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │    │
│  │  │ Intent   │  │  Safety  │  │  Input   │  │ Person-  │   │    │
│  │  │  Router  │  │Guardrails│  │Validation│  │  ality   │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              CONTEXT BUILDERS (ThreadPoolExecutor)           │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │    │
│  │  │Knowledge │ │  Pubmed  │ │  Open    │ │  Weekly  │       │    │
│  │  │Retriever │ │  Client  │ │Food Facts│ │  Trends  │       │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │    │
│  │  │  User    │ │ Adaptive │ │ Exercise │                   │    │
│  │  │ Profile  │ │ Planner  │ │Nutrition │                   │    │
│  │  └──────────┘ └──────────┘ └──────────┘                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   LLM (Groq LLaMA 3.3 70B)                  │    │
│  │                     + LangChain Bridge                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │             KNOWLEDGE GRAPH (742 nodes · 1628 edges)        │    │
│  │  40 communities: Adaptive Planning · API · Exercise ·       │    │
│  │  Nutrition · Progression · PubMed · Anatomy · Training      │    │
│  │  Programs · Recovery · Safety · Personality · Formulas      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Features

### 🧠 Elite Coaching AI
Powered by LLaMA 3.3 70B Versatile via Groq, delivering structured, markdown-formatted responses with workout tables, macro breakdowns, RPE targets, and evidence-based reasoning — all in a natural conversational tone.

### 📚 RAG Knowledge Base
43 curated source files (17 text guides, 20 PDFs, 3 JSON indices, 3 blueprints) covering:
- **Training**: Periodization, biomechanics, hypertrophy programs (Jeff Nippard), powerbuilding, sport-specific training
- **Nutrition**: Advanced nutrition, supplements guide, ISSN position stands (creatine, caffeine, beta-alanine, protein, nutrient timing, diets)
- **Science**: Anatomy & Physiology textbooks, research hub with 775 concept nodes
- **Calculations**: Gym formulas, BMR/TDEE, 1RM estimation, body fat formulas

### 🔬 Live PubMed Research
Real-time biomedical literature search via the PubMed API. The agent seamlessly integrates recent research findings into coaching advice — no stale knowledge.

### 🥗 Nutrition Intelligence
- **Static DB**: 673 USDA foods curated with macronutrient profiles
- **Live Lookup**: Open Food Facts API for real-world packaged food data
- **Smart Filters**: High-protein, low-carb, low-fat categorization

### 📊 Lift Logging & Progression
Natural-language parsing of workout entries (`"benched 185x8, 185x6, 190x5"`) with:
- **1RM Estimation**: Brzycki (≤10 reps), Epley (11-20 reps), automatic formula selection
- **IRV Tracking**: Intensity Relative Volume for hypertrophy zone monitoring (target: 20-30)
- **Auto-Progression**: Next-session weight/reps/sets recommendations with reasoning
- **Cross-Session History**: Full progression context across all logged sessions

### 📈 Weekly Trend Analysis
Automatic aggregation of all logged sessions into weekly summaries:
- **Volume Trends**: 3-week rolling trend analysis (increasing / stable / declining)
- **Strength Trends**: Per-exercise 1RM tracking week-over-week
- **ACWR Monitoring**: Acute:Chronic Workload Ratio with risk classification (undertrained → optimal → danger zone)
- **Deload Detection**: Automatic identification of when recovery is needed

### 👤 Persistent User Profiles
Every user gets a persistent profile (JSON-backed, survives across conversations):
- Physical metrics: weight, height, age, gender, body fat %
- Goals & preferences: primary goal, diet type, training frequency
- Context: experience level, injuries, equipment, sleep, stress
- Auto-extracted from natural conversation — no forms needed

### 🎯 Adaptive Recommendations
The `AdaptivePlanner` cross-references user profile + weekly trends to generate:
- **Nutrition Adjustments**: Calorie targets, macro splits, meal timing based on goal
- **Training Adjustments**: Volume, intensity, frequency modifications
- **Deload Recommendations**: When ACWR signals accumulated fatigue
- All injected naturally into the agent's context

### 🧮 Formula Engine
| Formula | Purpose | Method |
|---------|---------|--------|
| BMR | Basal Metabolic Rate | Mifflin-St Jeor, Katch-McArdle, Harris-Benedict |
| TDEE | Total Daily Energy Expenditure | BMR × activity multiplier |
| 1RM | One-Rep Max | Brzycki, Epley, Lombardi, O'Conner |
| Body Fat % | Body Composition | Navy body fat (men & women) |
| Protein Targets | Daily Intake | 0.8-2.4 g/kg by goal |
| ACWR | Recovery | Acute:Chronic ratio |

### 🛡️ Safety & Guardrails
- **Crisis Detection**: Medical emergency escalation
- **Scope Control**: Two-layer intent routing (heuristic + LLM)
- **Input Validation**: Length checks, injection filtering
- **Medical Boundaries**: Clear disclaimers, refuses to diagnose

### 🎭 Personality Modes
Choose your coaching style: `coach`, `drill_sergeant`, `science_professor`, or `zen_guide` — each with distinct tone and methodology.

### 🔄 Real-Time Streaming
Server-Sent Events (SSE) streaming via `/v1/chat/stream` for token-by-token responses.

---

## Knowledge Graph Insights

The project's codebase and knowledge corpus form a **742-node, 1628-edge knowledge graph** with **40 communities** discovered via graph clustering:

### God Nodes (Highest Betweenness Centrality)
| Node | Edges | Role |
|------|-------|------|
| `SessionStore` | 51 | Bridges 9 communities — the central data backbone |
| `ChatTurn` | 35 | Core interaction unit connecting agent ↔ storage |
| `UserProfile` | 34 | Persistent identity across all coaching interactions |
| `FitnessAgent` | 26 | The orchestrator binding all subsystems |
| `LiftParser` | 25 | Natural-language entry point to the tracking system |
| `PubMedClient` | 24 | Live research bridge to external knowledge |
| `KnowledgeRetriever` | 21 | RAG hub connecting PDF corpus to LLM context |

### Community Map
```
Adaptive Planning ─── SessionStore ─── API & Request Handling
       │                   │                    │
       │            Progression & 1RM      Intent Routing
       │                   │                    │
       │            Recovery Analysis ──── Agent Core
       │                                        │
       └──────── User Profile ────────── Context Building
                          │
                 PubMed · Open Food Facts · Knowledge Pipeline
                          │
                 Lift Parsing · Exercise · Nutrition Retrieval
                          │
              Safety · Personality · Formula Engine
```

### Hyperedges (Group Relationships)
- **Jeff Nippard Training Ecosystem** — 5 programs across powerbuilding, hypertrophy, specialization — INFERRED 0.95
- **Fitness & Physiology Knowledge Base** — anatomy textbooks + hypertrophy guides — INFERRED 0.90
- **ISSN Sports Nutrition Guidelines** — 6 position stands (creatine, caffeine, protein, etc.) — EXTRACTED 1.00
- **Hypertrophy Training Protocols** — Full Body HF + Fundamentals programs — EXTRACTED 0.90

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | LLaMA 3.3 70B Versatile via [Groq](https://groq.com) |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| **LLM Bridge** | [LangChain](https://www.langchain.com/) (`langchain-groq`) |
| **Retrieval** | TF-IDF (scikit-learn) over multi-source knowledge base |
| **Auth** | API key header validation |
| **Streaming** | Server-Sent Events (SSE) |
| **Knowledge Graph** | [graphify](https://github.com/safishamsi/graphify) — AST + semantic extraction, Louvain clustering |
| **UI (dev)** | [Streamlit](https://streamlit.io/) test interface |
| **Testing** | [pytest](https://docs.pytest.org/) — 120 tests |
| **Deployment** | Docker · HuggingFace Spaces |
| **Persistence** | JSON-backed stores (atomic writes via `os.replace`) |

---

## Quick Start

### Prerequisites
- Python 3.11+
- A [Groq API key](https://console.groq.com) (free tier available)

### 1. Clone & Setup
```bash
git clone https://github.com/your-org/fitzone-chatbot.git
cd fitzone-chatbot
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# or: .venv\Scripts\activate  # Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=gsk_your_key_here
FITZONE_API_KEY=a_secure_key_at_least_16_chars

# Optional
NCBI_API_KEY=your_ncbi_key      # Higher PubMed rate limits
GEMINI_API_KEY=your_gemini_key   # For semantic graph extraction
```

### 4. Start the API Server
```bash
uvicorn src.api:app --reload --port 8000
```

### 5. Test It
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_fitzone_api_key" \
  -d '{"message": "What is my BMR if I am 30, 180 cm, 85 kg, male?"}'
```

### 6. Run the Streamlit UI (optional)
```bash
streamlit run src/streamlit_app.py
```

---

## Configuration Reference

All environment variables with defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required.** Groq API key |
| `FITZONE_API_KEY` | — | **Required.** API auth key (min 16 chars) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Primary LLM model |
| `GROQ_FAST_MODEL` | `llama-3.1-8b-instant` | Fast model for routing/classification |
| `LLM_TEMPERATURE` | `0.4` | Generation temperature |
| `KNOWLEDGE_MATCH_THRESHOLD` | `0.12` | Minimum TF-IDF score for context injection |
| `RETRIEVAL_TOP_K` | `5` | Max knowledge chunks per query |
| `MAX_CONTEXT_CHARS` | `8000` | Max characters in LLM context window |
| `MAX_MESSAGE_LENGTH` | `2000` | Max user message length |
| `MAX_HISTORY_TURNS` | `10` | Conversation turns kept in context |
| `RATE_LIMIT_PER_SESSION` | `30` | Messages per session limit |
| `LLM_RETRY_ATTEMPTS` | `3` | Retry count for LLM calls |
| `LLM_RETRY_DELAY_SEC` | `1.0` | Delay between retries |
| `API_TIMEOUT_SEC` | `12.0` | External API timeout |
| `NCBI_API_KEY` | — | PubMed API key (higher rate limits) |

---

## API Reference

### Authentication
All endpoints require `X-API-Key` header:
```bash
-H "X-API-Key: your_fitzone_api_key"
```

### `POST /v1/chat`
Full chat response.

**Body:**
```json
{
  "message": "What are the best back hypertrophy exercises?",
  "history": [],
  "session_id": "user-123",
  "science_mode": false,
  "personality": "coach"
}
```

**Response:**
```json
{
  "response": "For back hypertrophy, focus on...",
  "latency_ms": 1842.35,
  "blocked": false,
  "block_reason": null,
  "in_scope": true,
  "lift_logged": false,
  "progression_hint": null,
  "science_mode": false
}
```

### `POST /v1/chat/stream`
SSE streaming variant. Same body, yields `text/event-stream`.

### `POST /v1/lift/log`
Log a natural-language workout entry.

### `GET /v1/lift/history/{exercise}`
Get all logged entries for an exercise across all sessions.

### `GET /v1/lift/recommend/{exercise}`
Get next-session progression recommendation with 1RM, IRV, suggested weight/reps/sets.

### `GET /v1/recovery`
ACWR-based recovery assessment with deload recommendation.

### `GET /v1/personalities`
List all available personality modes.

### `GET /health`
Liveness check.

### `GET /ready`
Deep readiness check — verifies LLM connection is functional.

---

## Project Structure

```
fitzone-chatbot/
├── src/                          # Core application
│   ├── api.py                    # FastAPI server & endpoints
│   ├── fitness_agent.py          # LLM agent orchestrator
│   ├── config.py                 # Central configuration
│   ├── auth.py                   # API key verification
│   │
│   ├── knowledge_retriever.py    # TF-IDF RAG over PDFs + text
│   ├── nutrition_retriever.py    # Nutrition KB search
│   ├── exercise_retriever.py     # Exercise KB search
│   ├── open_food_facts.py        # Live food API client
│   ├── pubmed_client.py          # Live research API client
│   │
│   ├── user_profile.py           # Persistent user profiles
│   ├── weekly_tracker.py         # Weekly training aggregation
│   ├── adaptive_planner.py       # Cross-ref profile + trends → recommendations
│   ├── session_store.py          # Per-session lift storage
│   ├── progressor.py             # 1RM, IRV, ACWR, auto-progression
│   ├── recovery.py               # Recovery & fatigue assessment
│   ├── lift_parser.py            # Natural-language lift log parser
│   │
│   ├── intent_router.py          # Two-layer scope + domain routing
│   ├── safety.py                 # Crisis & medical boundary checks
│   ├── input_validation.py       # Input sanitization
│   ├── personality.py            # Coaching personality modes
│   │
│   ├── formula_calculator.py     # Computation engine
│   ├── formula_registry.py       # Formula definitions & transparency
│   │
│   ├── routes_nutrition.py       # Nutrition sub-routes
│   ├── routes_exercises.py       # Exercise sub-routes
│   ├── routes_formulas.py        # Formula sub-routes
│   │
│   ├── streamlit_app.py          # Dev/test UI
│   ├── healthcheck.py            # Warmup & health scripts
│   ├── logging_utils.py          # Structured logging
│   └── retry_utils.py            # Retry with backoff
│
├── knowledge/                    # Knowledge base (43 files)
│   ├── *.txt                     # 17 training/nutrition/science guides
│   ├── *.pdf                     # 20 PDFs (textbooks, programs, ISSN)
│   ├── *.json                    # 3 indexed databases (exercises, nutrition, formulas)
│
├── tests/                        # Test suite (120 tests, 14 suites)
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_lift_parser.py
│   ├── test_progressor.py
│   ├── test_recovery.py
│   ├── test_user_tracking.py     # 39 tests for profiles + weekly + adaptive
│   ├── test_safety.py
│   ├── test_input.py
│   ├── test_personality.py
│   ├── test_formula_registry.py
│   ├── test_pubmed.py
│   └── conftest.py
│
├── scripts/                      # Data ingestion & maintenance
├── graphify-out/                 # Knowledge graph outputs
│   ├── graph.html                # Interactive visualization
│   ├── graph.json                # Raw graph data
│   └── GRAPH_REPORT.md           # Full audit report
├── .cache/                       # Runtime storage (auto-created)
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Testing

```bash
# Full suite (120 tests, 14 suites)
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific suites
pytest tests/test_user_tracking.py -v    # 39 tests
pytest tests/test_lift_parser.py -v      # Lift parsing
pytest tests/test_agent.py -v            # Agent integration
pytest tests/test_progressor.py -v       # 1RM, IRV, ACWR
```

---

## Deployment

### Docker (HuggingFace Spaces)

```bash
docker build -t fitzone-chatbot .
docker run -p 7860:7860 \
  -e GROQ_API_KEY=gsk_... \
  -e FITZONE_API_KEY=your_key \
  fitzone-chatbot
```

The HuggingFace Spaces config (`README.md` frontmatter) auto-detects `sdk: docker` and serves from `src/api.py`.

### Environment Variables (Production)
Set via HuggingFace Spaces Secrets:
- `GROQ_API_KEY`
- `FITZONE_API_KEY`
- `NCBI_API_KEY` (optional, for higher PubMed rate limits)

---

## Knowledge Graph Visualization

Open `graphify-out/graph.html` in any browser to explore the interactive 742-node knowledge graph of the entire codebase and knowledge corpus. Clustered by Louvain community detection into 40 topic areas.

Or run a query against the graph:
```bash
graphify query "How does SessionStore connect to the adaptive planning system?"
```

---

## License

MIT
