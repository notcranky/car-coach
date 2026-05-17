"""
Streamlit web UI for Car Coach.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import json
import os
import sys
import re
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
# Part verifier — verify parts actually exist
# =====================
def extract_parts_from_response(response: str, car: dict) -> list:
    """
    Look for part names in the AI response.
    Returns a list of (part_name, verified: bool) tuples.
    """
    # Simple part extraction — look for lines that look like parts
    # Pattern: "• Part Name — $XX" or "- Part Name: $XX"
    lines = response.split("\n")
    parts = []

    for line in lines:
        # Look for bullet points or dashes that might be parts
        cleaned = line.strip()
        if cleaned.startswith("•") or cleaned.startswith("-") or cleaned.startswith("*"):
            # Try to extract the part name (before the $ sign or em dash)
            part_match = re.search(r"[•\-*]\s*(.+?)(?:\s*[-—]\s*\$|\s*[-—]\s*\w)", cleaned)
            if part_match:
                part_name = part_match.group(1).strip()
                # Clean up any trailing punctuation
                part_name = re.sub(r"[.,;:!?]+$", "", part_name).strip()
                if len(part_name) > 3 and len(part_name) < 100:
                    parts.append(part_name)

    return parts

def verify_parts(parts: list, car: dict, web_search: WebSearch) -> dict:
    """
    Check each part against web search to see if it exists.
    Returns dict: { part_name: verified: bool, search_result: str }
    """
    results = {}

    for part in parts:
        # Search for the part with car specifics
        query = f"{part} {car.get('year', '')} {car.get('make', '')} {car.get('model', '')} fitment"
        search_result = web_search.search(query, car)

        # Part is verified if we got meaningful search results
        # (not the mock "no api key" message)
        is_verified = bool(search_result and len(search_result) > 50 and "[Web search failed]" not in search_result)

        results[part] = {
            "verified": is_verified,
            "search_result": search_result[:200] if search_result else ""
        }

    return results

# =====================
# Cleaner response builder
# =====================
def build_clean_response(response: str, verification: dict, car: dict) -> str:
    """
    Rebuild the response, flagging unverified parts.
    """
    if not verification:
        return response

    lines = response.split("\n")
    cleaned_lines = []
    has_unverified = False

    for line in lines:
        # Check if this line contains an unverified part
        for part, data in verification.items():
            if part in line and not data["verified"]:
                has_unverified = True
                # Add warning flag to the part
                line = line.replace(part, f"⚠️ {part} [UNVERIFIED — may not exist]")
                break
        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)

    if has_unverified:
        result += "\n\n⚠️ **Some parts couldn't be verified — I may have hallucinated them.** Check the flagged items above or try a more specific question."

    return result

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

    # Settings
    st.subheader("Settings")
    web_search_enabled = st.toggle("Enable web search", value=True)
    verify_parts_toggle = st.toggle("Auto-verify parts", value=True)
    if verify_parts_toggle:
        st.caption("Checks if parts actually exist before showing")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("v1.3 — Car Build Assistant")

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
# System prompt — ANTI-HALLUCINATION
# =====================
SYSTEM_PROMPT = """You are Car Coach, an experienced mechanic and car build specialist.

ABSOLUTE RULES — These are non-negotiable:
1. NEVER invent a part name. If you don't know the exact real part, say "I don't know the exact part name for that — I need to search for it."
2. NEVER say a part fits if you're not 100% sure. If unsure, say "I need to verify fitment for your specific year/engine."
3. Only recommend parts you are confident exist and fit the user's car. When in doubt, ask if they want you to search for options.
4. NEVER invent part numbers, brand names you don't recognize, or prices that are obviously wrong.
5. For any part recommendation, if you're not 100% certain it exists, prefix it with "I need to look this up:" and describe what you're searching for.
6. ALWAYS check the user's car profile: year, make, model, engine, mileage. Use those exact specs for fitment.
7. For cars over 100k miles, be conservative — flag any mod that could stress a tired engine.
8. If the user asks for something you don't have real knowledge of, say "I don't have that in my knowledge — let me search for it" rather than making something up.

RESPONSE RULES:
- Only list parts that you are confident exist in real life
- Use common known brands: Borla, Magnaflow, Corsa, K&N, AEM, DiabloSport, SCT, Bavin, Bilstein, KW, Tein, Eibach, Cobb, etc.
- If you're not sure about a brand, say "I'm not certain this brand exists — I should search for this"
- Never make up a part that starts with something generic like "Stage 2 turbo kit for [engine]" if you don't know the real product name

Your tone: direct, practical, like a mechanic friend. No fluff. But always honest about what you don't know.

If you're unsure: "I don't have that in my knowledge base. Want me to search for real options that fit your [year] [make] [model] [engine]?"
"""

def build_messages(car_context: str, correction: str = ""):
    """Build messages for the AI."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add car context
    messages.append({"role": "system", "content": f"User's car:\n{car_context}"})

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
            "content": f"IMPORTANT — The user's last answer wasn't what they wanted. Their feedback was: '{correction}'. Apply this feedback and give a better answer. Do NOT repeat the same approach."
        })

    # Add conversation history
    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "user"
        messages.append({"role": role, "content": msg["content"]})

    return messages

def get_response(messages: list, attempt: int = 1) -> str:
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

    # Check if this is a correction
    is_corr = is_correction(user_input) and correction_mode

    if st.session_state.awaiting_correction:
        # User previously said something was wrong — this is their feedback
        correction = user_input
        st.session_state.awaiting_correction = False

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()

        with st.chat_message("user"):
            st.markdown(f"[Applying correction: {correction}]")

        messages = build_messages(car_context, correction)
        response = get_response(messages)

        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    elif is_corr:
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
                           "current", "newest", "latest", "available", "what's the",
                           "parts", "mod", "install", "kit"]
            needs_search = any(term in user_input.lower() for term in search_terms)

            if needs_search:
                with st.spinner("Searching the web..."):
                    web_search = WebSearch()
                    results = web_search.search(user_input, car or {})
                    if results and "[Web search failed]" not in results:
                        messages[-1]["content"] += f"\n\nWeb search results:\n{results}\n\nUse these real results to inform your response."

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_response(messages)

            # Part verification — check if parts actually exist
            if verify_parts_toggle and web_search_enabled:
                with st.spinner("Verifying parts..."):
                    web_search = WebSearch()
                    parts = extract_parts_from_response(response, car or {})
                    if parts:
                        verification = verify_parts(parts, car or {}, web_search)
                        response = build_clean_response(response, verification, car or {})

            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.memory.update_from_text(response)
        st.rerun()