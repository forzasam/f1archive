from __future__ import annotations

import json
from pathlib import Path

EDITORIAL_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "editorial"

ROUND_FILES = {
    1: "2026-australia.json",
    2: "2026-china.json",
    3: "2026-japan.json",
    4: "2026-miami.json",
    5: "2026-canada.json",
    6: "2026-monaco.json",
    7: "2026-barcelona.json",
    8: "2026-austria.json",
    9: "2026-great-britain.json",
    10: "2026-belgium.json",
}

def get_curated_race_events(season: int, round_number: int) -> dict | None:
    if season != 2026:
        return None
    filename = ROUND_FILES.get(round_number)
    if not filename:
        return None
    path = EDITORIAL_DIRECTORY / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
