#!/usr/bin/env python3
"""
Car Coach — Your personal AI build assistant.
Reads your car profile, knows what you've done, gives advice based on both.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.car_knowledge import SYSTEM_PROMPT
from profiles.loader import load_car_profile, format_car_context
from memory.build_memory import BuildMemory
from search.web_search import WebSearch

MEMORY_FILE = PROJECT_ROOT / "memory" / "build_memory.json"

def load_history():
    """Load conversation history."""
    history_file = PROJECT_ROOT / "memory" / "conversation_history.json"
    if history_file.exists():
        with open(history_file, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    """Save conversation history."""
    history_file = PROJECT_ROOT / "memory" / "conversation_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, "w") as f:
        json.dump(history[-50:], f, indent=2)  # Keep last 50 messages

def main():
    print("🚗 Car Coach — Your Build Assistant")
    print("=" * 40)
    print("Type 'exit' to quit, 'clear' to clear history\n")

    # Load car profile
    car = load_car_profile()
    if car:
        print(f"📋 Loaded: {car['year']} {car['make']} {car['model']} {car.get('trim', '')}")
        if car.get("currentMods"):
            print(f"   Mods: {', '.join(car['currentMods'][:5])}")
        print()
    else:
        print("⚠️  No car profile found. Create one at profiles/my_car.json")
        print()

    # Initialize memory
    memory = BuildMemory(str(MEMORY_FILE))
    history = load_history()

    # Initialize web search
    web_search = WebSearch()

    # Build system prompt with car context
    car_context = format_car_context(car)
    system_msg = SYSTEM_PROMPT.replace("{{CAR_CONTEXT}}", car_context)
    messages = [{"role": "system", "content": system_msg}]

    # Add history to messages
    for msg in history:
        messages.append(msg)

    # Import the model interface
    from model_loader import chat

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break

        if user_input.lower() == "clear":
            history = []
            messages = [{"role": "system", "content": system_msg}]
            print("🗑️ History cleared\n")
            continue

        # Add user message
        messages.append({"role": "user", "content": user_input})

        # Check if web search is needed
        needs_search = any(kw in user_input.lower() for kw in [
            "latest", "newest", "current price", "what's the best",
            "recommend", "compatible", "does this fit", "fitment",
            "reviews", "options", "compare"
        ])

        search_context = ""
        if needs_search:
            print("🔍 Searching the web...")
            search_results = web_search.search(user_input, car)
            if search_results:
                search_context = f"\n\nWeb search results:\n{search_results}\n\nUse these results to inform your response."
            else:
                search_context = "\n\n(No web results found — answer from car knowledge only.)"

        # Add search context to last message
        if search_context:
            messages[-1]["content"] += search_context

        # Get response
        print()
        response = chat(messages)
        print(f"Car Coach: {response}\n")

        # Save to history
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})
        save_history(history)

        # Update memory with any milestones mentioned
        memory.update_from_text(response)

if __name__ == "__main__":
    main()