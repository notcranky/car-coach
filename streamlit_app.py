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

# =====================
# Correction keywords
# =====================
CORRECTION_KEYWORDS = [
    "redo", "wrong", "not it", "nope",
    "no that's not", "that's not right", "not what I wanted",
]

def is_correction(text: str) -> bool:
    """Check if input is a correction trigger word."""
    t = text.lower().strip()
    return any(kw in t for kw in CORRECTION_KEYWORDS)

# =====================
# Sidebar
# =====================
with st.sidebar:
    st.title("🚗 Car Coach")
    st.divider()

    # Load car
    car = load_car_profile()
    if car:
        st.success(f"Loaded: {car.get('year')} {car.get('make')} {car.get('model')}")
        with st.expander("View car details"):
            for key, value in car.items():
                if key not in ["notes", "currentMods"]:
                    st.text(f"{key}: {value}")
            if car.get("currentMods"):
                st.markdown("**Current Mods:**")
                for mod in car["currentMods"]:
                    st.markdown(f"  • {mod}")
    else:
        st.warning("No car profile loaded")
        st.caption("Create profiles/my_car.json")

    st.divider()

    # Correction mode toggle
    st.subheader("Correction Mode")
    correction_mode = st.toggle("Enable correction mode", value=True)
    if correction_mode:
        st.caption("Say 'wrong', 'redo', 'cheaper', etc. to refine answers")

    st.divider()

    # Web search toggle
    st.subheader("Settings")
    web_search_enabled = st.toggle("Enable web search", value=False)

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("v1.2 — Car Build Assistant")

# =====================
# Session state
# =====================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    st.session_state.memory = BuildMemory(str(MEMORY_FILE))

if "awaiting_correction" not in st.session_state:
    st.session_state.awaiting_correction = False

# =====================
# System prompt
# =====================
SYSTEM_PROMPT = """You are Car Coach, a knowledgeable and experienced car friend who knows builds inside and out.

Your personality:
- Direct, practical, no-nonsense advice
- You think in build order — you know what has to come before what
- You respect the user's goals (daily driver, track car, show car, etc.)
- You're honest about risks and limitations
- You speak like a car guy, not a textbook

What you know about the user's car:
{{CAR_CONTEXT}}

Your job:
- Answer questions about the user's car and what they're working on
- Suggest the logical next upgrade based on their goals, current mods, and budget
- Explain why something makes sense (or doesn't) for their specific build
- Know when something pairs well with existing mods — and when it conflicts
- Flag dangerous combinations
- Remember what they've already done so you never duplicate suggestions

Build order basics:
1. Safety first (brakes, tires)
2. Supporting mods before power (suspension, cooling, fuel system)
3. Power mods last (turbo, supercharger, engine work)

Keep responses conversational. 3-5 sentences for most answers, more only when needed. Use bullet points for part lists.
"""

def build_messages(car_context: str, correction: str = ""):
    """Build messages for the AI."""
    system = SYSTEM_PROMPT.replace("{{CAR_CONTEXT}}", car_context)
    messages = [{"role": "system", "content": system}]

    # Add memory context
    memory_text = st.session_state.memory.format_memory()
    if memory_text != "No build history yet.":
        messages.append({
            "role": "system",
            "content": f"Build history:\n{memory_text}"
        })

    # Add correction instruction
    if correction:
        messages.append({
            "role": "system",
            "content": f"IMPORTANT — The user said my last answer wasn't what they wanted. Their feedback was: '{correction}'. Apply this feedback and give a better answer. Do NOT repeat the same approach."
        })

    # Add conversation history
    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "user"
        messages.append({"role": role, "content": msg["content"]})

    return messages

def get_response(messages: list) -> str:
    """Call the model and clean up output."""
    try:
        response = chat(messages)
        response = response.replace("<think>", "").replace("[/think]", "").strip()
        return response
    except Exception as e:
        return f"Error: {e}"

# =====================
# Chat UI
# =====================
st.title("Car Coach")

# Welcome message
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
user_input = st.chat_input("Ask about your build...")

if user_input:
    car = load_car_profile()
    car_context = format_car_context(car)

    # Check if this is a correction / follow-up
    is_corr = is_correction(user_input) and correction_mode

    if st.session_state.awaiting_correction:
        # User previously said something was wrong — this is their feedback
        correction = user_input
        st.session_state.awaiting_correction = False

        # Remove the wrong response from history
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()

        # Add correction context and retry
        messages = build_messages(car_context, correction)

        with st.chat_message("user"):
            st.markdown(f"[Applying correction: {correction}]")

        with st.chat_message("assistant"):
            with st.spinner("Retrying..."):
                response = get_response(messages)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.memory.update_from_text(response)
        st.rerun()

    elif is_corr:
        # User triggered correction — ask what was wrong
        st.session_state.awaiting_correction = True
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            st.markdown("Sorry about that! What was wrong with it? What did you actually want?")

        st.rerun()

    else:
        # Normal message
        st.session_state.awaiting_correction = False
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        messages = build_messages(car_context)

        # Web search if enabled
        if web_search_enabled:
            search_terms = ["price", "best", "compare", "review", "compatible",
                           "fitment", "upgrade", "recommend", "should i", "worth it",
                           "current", "newest", "latest", "available", "what's the"]
            needs_search = any(term in user_input.lower() for term in search_terms)

            if needs_search:
                with st.spinner("Searching the web..."):
                    web_search = WebSearch()
                    results = web_search.search(user_input, car or {})
                    if results:
                        messages[-1]["content"] += f"\n\nWeb search results:\n{results}\n\nUse these to inform your response."

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_response(messages)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.memory.update_from_text(response)
        st.rerun()