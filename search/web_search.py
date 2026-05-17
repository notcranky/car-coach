"""
Web search integration.
Uses Tavily API for car-specific searches.
Falls back to a mock if no API key is set.
"""

import os
import json
from typing import Optional

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")

class WebSearch:
    def __init__(self):
        self.tavily_available = bool(TAVILY_API_KEY)
        self.serper_available = bool(SERPER_API_KEY)

    def search(self, query: str, car_profile: dict) -> str:
        """
        Search the web for car-related info.
        Returns formatted results string, or empty string on failure.
        """
        # Enhance query with car specifics
        enhanced_query = self._enhance_query(query, car_profile)

        if self.tavily_available:
            return self._search_tavily(enhanced_query)
        elif self.serper_available:
            return self._search_serper(enhanced_query)
        else:
            return self._mock_search(query, car_profile)

    def _enhance_query(self, query: str, car: dict) -> str:
        """Add car specifics to the search query."""
        if not car:
            return query

        car_spec = f"{car.get('year', '')} {car.get('make', '')} {car.get('model', '')} {car.get('trim', '')} {car.get('engine', '')}"
        car_spec = " ".join(part for part in car_spec.split() if part)

        current_mods = car.get("currentMods", [])
        mods_str = ", ".join(current_mods) if current_mods else ""

        enhanced = f"{query} for {car_spec}"
        if mods_str:
            enhanced += f" (current mods: {mods_str})"

        return enhanced

    def _search_tavily(self, query: str) -> str:
        """Search using Tavily API."""
        import urllib.request
        import urllib.parse

        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "query": query,
            "search_depth": "basic",
            "max_results": 5
        })

        req = urllib.request.Request(
            url,
            data=payload.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "apikey": TAVILY_API_KEY
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            results = []
            for item in data.get("results", []):
                title = item.get("title", "")
                url = item.get("url", "")
                snippet = item.get("content", "")[:200]
                results.append(f"- {title}\n  {snippet}\n  Source: {url}")

            return "\n\n".join(results) if results else ""

        except Exception as e:
            return f"[Web search failed: {e}]"

    def _search_serper(self, query: str) -> str:
        """Search using SerpAPI (Google)."""
        import urllib.request
        import urllib.parse

        params = json.dumps({
            "q": query,
            "hl": "en"
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://google.serper.dev/search",
            data=params,
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": SERPER_API_KEY
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            results = []
            for item in data.get("organic", [])[:5]:
                title = item.get("title", "")
                url = item.get("link", "")
                snippet = item.get("snippet", "")[:200]
                results.append(f"- {title}\n  {snippet}\n  Source: {url}")

            return "\n\n".join(results) if results else ""

        except Exception as e:
            return f"[Web search failed: {e}]"

    def _mock_search(self, query: str, car: dict) -> str:
        """Mock search for when no API key is set — for testing."""
        return f"""[Demo search — set TAVILY_API_KEY or SERPER_API_KEY to enable real web search]

Search query: {query}
Car: {car.get('year', '')} {car.get('make', '')} {car.get('model', '')} {car.get('engine', '')}

For real search results, get a free Tavily API key at https://tavily.com
And add it: export TAVILY_API_KEY=your_key_here"""