"""
Model loader — abstracts the chat model.
Supports:
1. Ollama (local, free)
2. OpenAI compatible API (OpenRouter, Groq, etc.)
3. Claude via Anthropic API

Edit the CONFIG below to switch models.
"""

import os
import json
import urllib.request
import urllib.parse

# =======================
# CONFIG — Edit this
# =======================
CONFIG = {
    # Provider: "ollama" | "openai" | "anthropic"
    "provider": "ollama",

    # Ollama settings
    "ollama_url": "http://localhost:11434/v1",
    "ollama_model": "qwen2.5-coder:7b",

    # OpenAI-compatible (OpenRouter, Groq, etc.)
    "openai_url": "https://openrouter.ai/api/v1",
    "openai_model": "moonshotai/kimi-k2.5",
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),

    # Anthropic settings
    "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
    "anthropic_model": "claude-sonnet-4-20250514",
}

# =======================

def chat(messages: list) -> str:
    """Send messages to the configured model and return the response."""
    provider = CONFIG["provider"]

    if provider == "ollama":
        return _chat_ollama(messages)
    elif provider == "openai":
        return _chat_openai(messages)
    elif provider == "anthropic":
        return _chat_anthropic(messages)
    else:
        return f"Unknown provider: {provider}"


def _chat_ollama(messages: list) -> str:
    """Call local Ollama instance."""
    url = f"{CONFIG['ollama_url']}/chat/completions"

    payload = json.dumps({
        "model": CONFIG["ollama_model"],
        "messages": messages,
        "stream": False
    })

    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Ollama error: {e}] Make sure Ollama is running at {CONFIG['ollama_url']}"


def _chat_openai(messages: list) -> str:
    """Call OpenAI-compatible API (OpenRouter, Groq, etc.)."""
    url = f"{CONFIG['openai_url']}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CONFIG['openai_api_key']}"
    }

    # OpenRouter requires extra headers
    if "openrouter" in CONFIG["openai_url"]:
        headers["HTTP-Referer"] = "https://car-coach.local"
        headers["X-Title"] = "Car Coach"

    payload = json.dumps({
        "model": CONFIG["openai_model"],
        "messages": messages
    })

    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[OpenAI API error: {e}]"


def _chat_anthropic(messages: list) -> str:
    """Call Anthropic Claude."""
    # Convert messages format for Anthropic
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "system":
            continue  # Anthropic uses system prompt separately
        anthropic_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": CONFIG["anthropic_api_key"],
        "anthropic-version": "2023-06-01"
    }

    # Extract system prompt
    system_prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
            break

    payload = json.dumps({
        "model": CONFIG["anthropic_model"],
        "messages": anthropic_messages,
        "system": system_prompt,
        "max_tokens": 1024
    })

    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["content"][0]["text"]
    except Exception as e:
        return f"[Anthropic error: {e}]"


# CLI test
if __name__ == "__main__":
    test_messages = [
        {"role": "user", "content": "Hi, what can you do?"}
    ]
    print("Testing model connection...")
    response = chat(test_messages)
    print(f"Response: {response}")