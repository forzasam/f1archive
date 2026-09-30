from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORY_ROOT = PROJECT_ROOT / "data" / "editorial" / "race_maps"


def get_race_story_map(season: int, round_number: int) -> dict[str, Any] | None:
    """Load optional map-story choreography for a race.

    This data is deliberately separate from circuit geometry: the same circuit
    package can be explored normally or used by any number of race stories.
    """
    path = STORY_ROOT / str(season) / f"{round_number}.json"
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        return None
    return payload
