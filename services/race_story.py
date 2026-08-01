from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.author_utils import get_author_identity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RACE_STORY_ROOT = PROJECT_ROOT / "data" / "editorial" / "races"


def race_story_path(season: int, round_number: int) -> Path:
    return RACE_STORY_ROOT / str(season) / f"{round_number}.json"


def has_race_story(season: int, round_number: int) -> bool:
    """Return True only when a valid, non-empty race story exists."""
    return get_race_story(season, round_number) is not None


def get_race_story(season: int, round_number: int) -> dict[str, Any] | None:
    """Load editorial context for one race.

    Files live at data/editorial/races/<season>/<round>.json and mirror the
    season-story schema: kicker, title, slug and paragraphs.
    """
    path = race_story_path(season, round_number)
    if not path.is_file():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    paragraphs = [
        str(paragraph).strip()
        for paragraph in payload.get("paragraphs", [])
        if str(paragraph).strip()
    ]
    if not paragraphs:
        return None

    author_identity = get_author_identity(payload.get("slug", ""))

    return {
        "title": str(payload.get("title", "The race in context")).strip()
        or "The race in context",
        "kicker": str(payload.get("kicker", "The race in context")).strip()
        or "The race in context",
        "author": author_identity["name"] if author_identity else None,
        "author_slug": author_identity["slug"] if author_identity else None,
        "paragraphs": paragraphs,
        "preview_paragraphs": paragraphs[:2],
        "has_more": len(paragraphs) > 2,
    }
