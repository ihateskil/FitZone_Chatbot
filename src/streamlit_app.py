"""
FitZone Fitness AI Agent — Streamlit test UI.

Run:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so src.* imports resolve
# when this file is executed directly by Streamlit.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time

import streamlit as st

from src.config import APP_NAME, DISCLAIMER, GROQ_API_KEY, RATE_LIMIT_PER_SESSION
from src.fitness_agent import ChatTurn, stream_agent, warmup_agent
from src.logging_utils import log_event, setup_logging

setup_logging()

SAMPLE_PROMPTS = [
    ("Out-of-scope", "Can you write me a Python script to scrape weather data?"),
    ("BMR calculation", "I'm a 30-year-old man, 180 cm, 85 kg. What is my BMR using Mifflin-St Jeor?"),
    ("Training program", "What are good back hypertrophy exercises from my training programs?"),
    ("Open Food Facts", "How many calories and protein are in grilled chicken breast per 100g?"),
    ("Log a workout", "benched 185x8, 185x6, 190x5"),
    ("PubMed research", "What does recent research say about optimal protein intake for muscle growth?"),
    ("Logging + recovery", "squatted 225x5 — how's my recovery looking?"),
]


@st.cache_resource(show_spinner="Loading knowledge base and agent…")
def _cached_agent():
    return warmup_agent()


def _init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "request_count" not in st.session_state:
        st.session_state.request_count = 0


def _history_from_session() -> list[ChatTurn]:
    turns: list[ChatTurn] = []
    for msg in st.session_state.messages:
        if msg["role"] in ("user", "assistant"):
            turns.append(ChatTurn(role=msg["role"], content=msg["content"]))
    return turns


def _check_rate_limit() -> str | None:
    if st.session_state.request_count >= RATE_LIMIT_PER_SESSION:
        return (
            f"Session limit reached ({RATE_LIMIT_PER_SESSION} messages). "
            "Start a new chat to continue."
        )
    return None


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} Coach",
        page_icon="💪",
        layout="centered",
    )

    _init_session()

    st.title(f"{APP_NAME} Fitness Coach")
    st.caption("Your science-based training & nutrition assistant")

    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY is not set. Add it to your `.env` file before testing.")
        st.stop()

    _cached_agent()

    with st.expander("Important disclaimer", expanded=not st.session_state.messages):
        st.info(DISCLAIMER)

    with st.sidebar:
        st.header("Quick prompts")
        for label, prompt in SAMPLE_PROMPTS:
            if st.button(label, use_container_width=True):
                st.session_state.pending_prompt = prompt

        if st.button("New chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.request_count = 0
            st.rerun()

        st.divider()
        st.caption(f"Messages this session: {st.session_state.request_count}/{RATE_LIMIT_PER_SESSION}")
        st.markdown(
            "**Powered by**\n"
            "- Training program PDFs + Research Hub\n"
            "- Gym calculation formulas\n"
            "- Open Food Facts (nutrition)\n"
            "- Groq LLM"
        )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("latency_ms"):
                st.caption(f"Responded in {message['latency_ms']:.0f} ms")

    prompt = st.chat_input("Ask about workouts, nutrition, macros, programs…")

    if "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")

    if prompt:
        limit_msg = _check_rate_limit()
        if limit_msg:
            st.warning(limit_msg)
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        history = _history_from_session()[:-1]

        with st.chat_message("assistant"):
            start = time.perf_counter()
            try:
                response = st.write_stream(stream_agent(prompt, history=history))
            except Exception as exc:
                log_event("stream_error", error=str(exc))
                response = "Something went wrong. Please try again in a moment."
                st.markdown(response)

            latency_ms = (time.perf_counter() - start) * 1000
            st.caption(f"Responded in {latency_ms:.0f} ms")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
                "latency_ms": latency_ms,
            }
        )
        st.session_state.request_count += 1
        st.rerun()


if __name__ == "__main__":
    main()
