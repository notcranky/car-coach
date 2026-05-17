"""
Profile loader — loads the user's car from various sources.
Can read from:
1. A local JSON file (profiles/my_car.json)
2. Modvora garage data (if mounted)
3. Manual entry
"""

import json
import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent

def load_car_profile() -> Optional[dict]:
    """
    Try to load car profile from known locations.
    Returns dict with car specs or None if not found.
    """
    # Try local profile first
    local = PROJECT_ROOT / "profiles" / "my_car.json"
    if local.exists():
        with open(local, "r") as f:
            return json.load(f)

    # Try Modvora workspace (if mounted)
    modvora_path = os.environ.get("MODVORA_PATH")
    if modvora_path:
        garage_file = Path(modvora_path) / "lib" / "garage.ts"
        if garage_file.exists():
            car = _parse_garage_ts(garage_file)
            if car:
                return car

    # Try Syncthing path
    syncthing_path = os.environ.get("SYNCTHING_PATH")
    if syncthing_path:
        for subpath in ["garage.json", "my_car.json", "car_profile.json"]:
            p = Path(syncthing_path) / subpath
            if p.exists():
                with open(p, "r") as f:
                    return json.load(f)

    return None

def _parse_garage_ts(garage_file: Path) -> Optional[dict]:
    """
    Parse garage.ts to extract vehicle data.
    Crude but effective — reads the file and extracts JSON-like data.
    """
    try:
        content = garage_file.read_text()

        # Look for SavedVehicle type entries
        # This is a simplified parser — could be improved
        lines = content.split("\n")
        vehicles = []

        # Try to find year/make/model patterns
        import re
        year_match = re.search(r"year:\s*['\"](\d{4})['\"]", content)
        make_match = re.search(r"make:\s*['\"](\w+)['\"]", content)
        model_match = re.search(r"model:\s*['\"](\w+)['\"]", content)
        trim_match = re.search(r"trim:\s*['\"]([^'\"]+)['\"]", content)
        engine_match = re.search(r"engine:\s*['\"]([^'\"]+)['\"]", content)

        if year_match and make_match and model_match:
            return {
                "year": year_match.group(1),
                "make": make_match.group(1),
                "model": model_match.group(1),
                "trim": trim_match.group(1) if trim_match else "",
                "engine": engine_match.group(1) if engine_match else "",
            }

    except Exception:
        pass

    return None

def format_car_context(car: Optional[dict]) -> str:
    """Format car info into a string for the system prompt."""
    if not car:
        return "No car profile loaded. Ask the user about their car."

    lines = [
        f"Year/Make/Model: {car.get('year', '?')} {car.get('make', '?')} {car.get('model', '?')}",
    ]

    if car.get("trim"):
        lines.append(f"Trim: {car['trim']}")

    if car.get("engine"):
        lines.append(f"Engine: {car['engine']}")

    if car.get("drivetrain"):
        lines.append(f"Drivetrain: {car['drivetrain']}")

    if car.get("transmission"):
        lines.append(f"Transmission: {car['transmission']}")

    if car.get("mileage"):
        lines.append(f"Mileage: {car['mileage']}")

    if car.get("currentMods"):
        lines.append(f"Current mods: {', '.join(car['currentMods'])}")

    if car.get("goals"):
        lines.append(f"Build goals: {car['goals']}")

    if car.get("budget"):
        lines.append(f"Budget: {car['budget']}")

    if car.get("focus"):
        lines.append(f"Build focus: {car['focus']}")

    return "\n".join(lines)