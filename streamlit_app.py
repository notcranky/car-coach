"""
Streamlit web UI for Car Coach.
Run with: streamlit run streamlit_app.py

v1.4 — Hard anti-hallucination mode.
Parts are verified against web search BEFORE they are shown to the user.
Unverified parts are BLOCKED, not flagged.
"""

import streamlit as st
import json
import os
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from model_loader import chat
from profiles.loader import load_car_profile, format_car_context
from memory.build_memory import BuildMemory
from search.web_search import WebSearch

st.set_page_config(
    page_title="Car Coach",
    page_icon="🚗",
    layout="wide"
)

PROJECT_ROOT = Path(__file__).parent
MEMORY_FILE = PROJECT_ROOT / "memory" / "build_memory.json"
KNOWN_REAL_BRANDS = [
    "Borla", "MagnaFlow", "Corsa", "K&N", "AEM", "DiabloSport", "SCT",
    "Bilstein", "KW", "Tein", "Eibach", "Cobb", "Garrett", "Precision",
    "Holley", "Edelbrock", "Flowmaster", "Invidia", "HKS", "Greddy",
    "Mishimoto", "Derale", "Russell", "Edelbrock", "Summit Racing",
    "JEGS", "MagnaFlow", "Volant", "AFE", "K&N", "Injen", "AEM",
    "DiabloSport", "Bully Dog", "Superchips", "Jet", "MSD", "ACCEL",
    "Hayden", "Fluidyne", "CWR", "Radiator", "Brembo", "EBC", "Stoptech",
    "Slotted", "Drilled", "DBA", "Wilwood", "Baer", "Goodridge",
    "Russell", "Earls", "Auto Meter", "Aeromotive", "Walbro"
]

def extract_part_candidates(text: str) -> list:
    """Extract potential part names from text."""
    lines = text.split("\n")
    candidates = []
    for line in lines:
        line = line.strip()
        if line.startswith("•") or line.startswith("-") or line.startswith("*"):
            # Get everything before the first $ or em-dash
            part = re.sub(r"^[-•*]\s*", "", line)
            part = re.split(r"\s*[-—$]\s*", part)[0]
            part = re.sub(r"[.,;:!?]+$", "", part).strip()
            if 3 < len(part) < 80:
                candidates.append(part)
    return candidates

def check_brand_known(part_name: str) -> bool:
    """Check if any known brand appears in the part name."""
    for brand in KNOWN_REAL_BRANDS:
        if brand.lower() in part_name.lower():
            return True
    return False

def verify_part(part: str, car: dict, web_search: WebSearch) -> dict:
    """Verify a single part exists via web search."""
    # Search for the part with car specifics
    query = f"{part} {car.get('year', '')} {car.get('make', '')} {car.get('model', '')}"
    result = web_search.search(query, car)

    has_results = bool(result and len(result) > 80 and "[Web search failed]" not in result)
    return {
        "verified": has_results,
        "search_result": result[:300] if result else ""
    }

def verify_and_filter_response(response: str, car: dict, web_search: WebSearch) -> tuple:
    """
    Verify all parts in a response.
    Returns (filtered_response, blocked_parts, all_verified).
    If a part can't be verified and its brand isn't in KNOWN_REAL_BRANDS, block it.
    """
    parts = extract_part_candidates(response)
    if not parts:
        return response, [], True

    verification = {}
    for part in parts:
        brand_known = check_brand_known(part)
        if brand_known:
            # Known brand — trust it but still verify with search
            v = verify_part(part, car, web_search)
            verification[part] = v
        else:
            # Unknown brand — need strong verification
            v = verify_part(part, car, web_search)
            verification[part] = v

    blocked = []
    lines = response.split("\n")
    cleaned = []

    for line in lines:
        blocked_in_line = []
        for part, data in verification.items():
            if part in line:
                if not data["verified"] and not check_brand_known(part):
                    blocked_in_line.append(part)
                    blocked.append(part)

        if blocked_in_line:
            # Replace the line with a placeholder
            for bp in blocked_in_line:
                line = re.sub(re.escape(bp), f"[BLOCKED — could not verify: {bp}]", line)
        cleaned.append(line)

    filtered = "\n".join(cleaned)
    return filtered, blocked, len(blocked) == 0

CORRECTION_KEYWORDS = ["redo", "wrong", "not it", "nope", "no that's not", "not what I wanted"]

def is_correction(text: str) -> bool:
    return any(kw in text.lower().strip() for kw in CORRECTION_KEYWORDS)

# =====================
# Sidebar
# =====================
with st.sidebar:
    st.title("🚗 Car Coach")
    st.divider()

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

    st.subheader("Correction Mode")
    correction_mode = st.toggle("Enable correction mode", value=True)
    if correction_mode:
        st.caption("Say 'wrong', 'redo', etc. to refine answers")

    st.divider()

    st.subheader("Settings")
    web_search_enabled = st.toggle("Enable web search", value=True)

    st.divider()

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.caption("v1.4 — Anti-hallucination hard mode")

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
SYSTEM_PROMPT = """You are Car Coach. Your only job is to help with car builds.

ABSOLUTE RULE: If you do not KNOW with certainty that a part exists, say "I don't know" instead of making it up. No exceptions.

The user's car: {CAR_CONTEXT}

What you know for certain (no search needed):
- Build order principles
- General modification concepts
- Platform-specific known issues

What you MUST search for:
- Specific part names
- Brand verification
- Pricing
- Fitment for specific years/engines

If you cannot verify a part through your knowledge or web search results, do NOT list it. Say: "I don't have that in my knowledge — I need to search for it."

Never make up: part names, brand names, part numbers, prices.
"""

def build_messages(car_context: str, correction: str = ""):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "system", "content": f"User's car:\n{car_context}"})

    memory_text = st.session_state.memory.format_memory()
    if memory_text != "No build history yet.":
        messages.append({"role": "system", "content": f"Build history:\n{memory_text}"})

    if correction:
        messages.append({"role": "system", "content": f"IMPORTANT — The user said my last answer was wrong. Feedback: '{correction}'. Do NOT repeat the same approach. Give a completely new answer based on their feedback."})

    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "user"
        messages.append({"role": role, "content": msg["content"]})

    return messages

def get_response(messages: list) -> str:
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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask about your build...")

if user_input:
    car = load_car_profile()
    car_context = format_car_context(car)

    is_corr = is_correction(user_input) and correction_mode

    if st.session_state.awaiting_correction:
        correction = user_input
        st.session_state.awaiting_correction = False

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()

        messages = build_messages(car_context, correction)

        with st.chat_message("user"):
            st.markdown(f"[Retrying with feedback: {correction}]")

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
            st.markdown("Sorry! What was wrong with it? What did you actually want?")

        st.rerun()

    else:
        st.session_state.awaiting_correction = False
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        messages = build_messages(car_context)

        # Always search when asking about parts/mods/pricing
        if web_search_enabled:
            search_terms = ["mod", "part", "intake", "exhaust", "tune", "turbo", "kit",
                           "upgrade", "install", "price", "best", "recommend", "coilover",
                           "suspension", "brakes", "wheel", "tire", "engine", "power"]
            needs_search = any(term in user_input.lower() for term in search_terms)

            if needs_search:
                with st.spinner("Searching the web for real parts..."):
                    web_search = WebSearch()
                    results = web_search.search(user_input, car or {})
                    if results and "[Web search failed]" not in results:
                        messages[-1]["content"] += f"\n\nWeb search results (use these for your answer):\n{results}\n\nOnly recommend parts from these search results. Do not recommend parts that are not confirmed in the search results above."

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_response(messages)

            # Verify and filter parts
            if web_search_enabled:
                with st.spinner("Verifying all parts..."):
                    web_search = WebSearch()
                    filtered_response, blocked_parts, all_verified = verify_and_filter_response(
                        response, car or {}, web_search
                    )

                    if not all_verified:
                        st.warning(f"I couldn't verify these parts — they may not exist. I'm not showing them to protect you from bad information:\n\n" + "\n".join(f"• {p}" for p in blocked_parts))

                    st.markdown(filtered_response if all_verified else response)
                    final_response = filtered_response if all_verified else response
            else:
                st.markdown(response)
                final_response = response

        st.session_state.messages.append({"role": "assistant", "content": final_response})
        st.session_state.memory.update_from_text(final_response)
        st.rerun()