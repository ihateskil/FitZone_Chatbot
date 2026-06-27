---
title: FitZone Chatbot
emoji: 💪
colorFrom: green
colorTo: gray
sdk: docker
app_file: src/api.py
pinned: false
---

# FitZone AI — Elite Fitness & Nutrition Coach

FitZone is a production-grade AI fitness coach and nutrition assistant, powered by LLaMA 3.3 70B via Groq. It combines RAG-based knowledge retrieval, lift tracking, formula calculations, and safety guardrails into a single conversational API.

## Features

- **Elite Coaching AI** — Structured, markdown-formatted responses with workout tables, macro breakdowns, and RPE targets
- **RAG Knowledge Base** — Retrieves from curated fitness/nutrition PDFs using TF-IDF similarity
- **Nutrition Lookup** — Live Open Food Facts API integration for real food data
- **Lift Logging & Progression** — Detects natural-language lift logs (`bench 185x8 185x6`) and recommends next session
- **Formula Engine** — BMR, TDEE, 1RM (Brzycki/Epley), body fat %, and more
- **Recovery Tracking** — ACWR-based fatigue monitoring and deload recommendations
- **Personality Modes** — coach, drill_sergeant, science_professor, zen_guide
- **Safety Guardrails** — Crisis detection, medical boundary responses, input validation
- **Streaming** — Real-time token streaming via `/v1/chat/stream`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/chat` | Full chat response |
| `POST` | `/v1/chat/stream` | Streaming chat response |
| `POST` | `/v1/lift/log` | Log a workout entry |
| `GET`  | `/v1/lift/history/{exercise}` | Get lift history |
| `GET`  | `/v1/lift/recommend/{exercise}` | Get progression recommendation |
| `GET`  | `/v1/recovery` | Get recovery/fatigue assessment |
| `GET`  | `/v1/personalities` | List personality modes |
| `GET`  | `/health` | Health check |

## Authentication

All endpoints require an `X-API-Key` header.

## Tech Stack

- **LLM**: LLaMA 3.3 70B Versatile (Groq)
- **Framework**: FastAPI + Uvicorn
- **Retrieval**: TF-IDF (scikit-learn) over PDF knowledge base
- **Deployment**: Docker on HuggingFace Spaces

## Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
