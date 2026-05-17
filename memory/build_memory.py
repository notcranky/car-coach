"""
Build memory — remembers the user's car, mods, and milestones.
Persists across sessions.
"""

import json
from pathlib import Path
from datetime import datetime

class BuildMemory:
    def __init__(self, memory_file: str):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if self.memory_file.exists():
            with open(self.memory_file, "r") as f:
                return json.load(f)
        return {
            "completed_mods": [],
            "milestones": [],
            "goals": {},
            "budget": "",
            "focus": "",
            "notes": [],
            "last_updated": None
        }

    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.memory_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_mod(self, mod: str):
        """Record a completed mod."""
        mod = mod.lower().strip()
        if mod not in self.data["completed_mods"]:
            self.data["completed_mods"].append(mod)
            self.save()

    def add_milestone(self, milestone: str):
        """Record a build milestone."""
        self.data["milestones"].append({
            "text": milestone,
            "date": datetime.now().isoformat()
        })
        self.save()

    def set_goals(self, goals: str):
        self.data["goals"] = {"text": goals, "date": datetime.now().isoformat()}
        self.save()

    def set_budget(self, budget: str):
        self.data["budget"] = budget
        self.save()

    def set_focus(self, focus: str):
        self.data["focus"] = focus
        self.save()

    def add_note(self, note: str):
        self.data["notes"].append({
            "text": note,
            "date": datetime.now().isoformat()
        })
        self.save()

    def get_mods(self) -> list:
        return self.data.get("completed_mods", [])

    def has_mod(self, mod: str) -> bool:
        return mod.lower().strip() in self.data.get("completed_mods", [])

    def update_from_text(self, text: str):
        """Parse text for mod mentions and update memory."""
        # Look for common patterns
        mod_keywords = [
            "installed", "added", "upgraded", "built", "completed",
            "just did", "finished", "purchased", "put in"
        ]

        text_lower = text.lower()

        # Simple keyword detection — could be improved with NLP
        common_mods = [
            "tune", "tuning", "ecu tune", "flashed", "ap", "accessport",
            "coilovers", "coilover", "suspension", "springs",
            "intake", "cold air intake", "cai",
            "exhaust", "catback", "axleback", "headers",
            "intercooler", "front mount", "fmic",
            "turbo", "bigger turbo", "upgrade",
            "wtb", "wideband", "afr gauge",
            "wheels", "rims", "tires", "rubber",
            "brakes", "brake kit", "rotors", "pads",
            "wing", "spoiler", "body kit", "splitter",
        ]

        for mod in common_mods:
            if mod in text_lower:
                self.add_mod(mod)

    def format_memory(self) -> str:
        """Format memory as readable text for the AI."""
        lines = []

        mods = self.data.get("completed_mods", [])
        if mods:
            lines.append(f"Completed mods ({len(mods)}): {', '.join(mods)}")

        milestones = self.data.get("milestones", [])
        if milestones:
            recent = milestones[-3:]
            lines.append(f"Recent milestones: {', '.join(m['text'] for m in recent)}")

        goals = self.data.get("goals", {}).get("text")
        if goals:
            lines.append(f"Goals: {goals}")

        budget = self.data.get("budget")
        if budget:
            lines.append(f"Budget: {budget}")

        focus = self.data.get("focus")
        if focus:
            lines.append(f"Focus: {focus}")

        return "\n".join(lines) if lines else "No build history yet."