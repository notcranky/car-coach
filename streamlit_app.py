"""
Streamlit web UI for Car Coach.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from model_loader import chat
from profiles.loader import load_car_profile, format_car_context
from memory.build_memory import BuildMemory
from search.web_search import WebSearch

# Page config
st.set_page_config(
    page_title="Car Coach",
    page_icon="🚗",
    layout="wide"
)

# Paths
PROJECT_ROOT = Path(__file__).parent
MEMORY_FILE = PROJECT_ROOT / "memory" / "build_memory.json"
PROFILE_FILE = PROJECT_ROOT / "profiles" / "my_car.json"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    st.session_state.memory = BuildMemory(str(MEMORY_FILE))

# =====================
# Sidebar — Car Profile
# =====================
with st.sidebar:
    st.title("🚗 Car Coach")
    st.divider()

    car = load_car_profile()
    if car:
        st.success(f"Loaded: {car.get('year')} {car.get('make')} {car.get('model')}")
        with st.expander("View car details"):
            for key, value in car.items():
                if key != "notes":
                    st.text(f"{key}: {value}")
    else:
        st.warning("No car profile loaded")
        st.caption("Create profiles/my_car.json to get started")

    st.divider()

    # Web search toggle
    st.subheader("Settings")
    web_search_enabled = st.toggle("Enable web search", value=False)
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("v1.0 — Car Build Assistant")

# =====================
# System prompt setup
# =====================
SYSTEM_PROMPT = """You are Car Coach, a knowledgeable and experienced car friend who knows builds inside and out.

Your personality:
- Direct, practical, no-nonsense advice
- You think in build order — you know what has to come before what
- You respect the user's goals (daily driver, track car, show car, etc.)
- You're honest about risks and limitations
- You speak like a car guy, not a textbook

Keep responses conversational but substantive. Use bullet points for part recommendations. When giving advice, always consider the user's current mods, goals, and budget.

Be concise — don't write essays. 3-5 sentences for most answers, more only when needed.
"""

def build_messages(car_context: str):
    """Build the messages list for the API."""
    system = SYSTEM_PROMPT.replace("{{CAR_CONTEXT}}", car_context)
    messages = [{"role": "system", "content": system}]

    # Add memory context
    memory_text = st.session_state.memory.format_memory()
    if memory_text != "No build history yet.":
        messages.append({
            "role": "system",
            "content": f"Build history:\n{memory_text}"
        })

    # Add conversation history
    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "user"
        messages.append({"role": role, "content": msg["content"]})

    return messages

# =====================
# Chat UI
# =====================
st.title("Car Coach")

# Show welcome message if empty
if not st.session_state.messages:
    car = load_car_profile()
    if car:
        welcome = f"Loaded your {car.get('year')} {car.get('make')} {car.get('model')} {car.get('trim', '')}. What do you want to work on today?"
        st.session_state.messages.append({"role": "assistant", "content": welcome})
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hey! I'm Car Coach. Create a `profiles/my_car.json` file to tell me about your ride, then let's get building."
        })

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# =====================
# Chat input
# =====================
user_input = st.chat_input("What do you want to know about your build?")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build context
    car = load_car_profile()
    car_context = format_car_context(car)
    messages = build_messages(car_context)

    # Add search context if enabled
    if web_search_enabled:
        search_terms = ["price", "best", "compare", "review", "compatible",
                       "fitment", "upgrade", "recommend", "should i", "worth it"]
        needs_search = any(term in user_input.lower() for term in search_terms)

        if needs_search:
            with st.spinner("Searching the web..."):
                web_search = WebSearch()
                results = web_search.search(user_input, car or {})
                if results:
                    messages[-1]["content"] += f"\n\nWeb search results:\n{results}\n\nUse these to inform your response."

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = chat(messages)
                # Clean up thinking tags if model added them
                response = response.replace("<think>", "").replace("</think>", "").strip()
            except Exception as e:
                response = f"Error: {e}"

        st.markdown(response)

    # Save to history
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Update memory
    st.session_state.memory.update_from_text(response)

    st.rerun()