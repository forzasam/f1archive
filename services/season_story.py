from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.author_utils import get_author_identity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEASON_STORY_ROOT = PROJECT_ROOT / "data" / "editorial" / "seasons"


def get_season_story(season: int) -> dict[str, Any] | None:
    path = SEASON_STORY_ROOT / f"{season}.json"
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
        "title": str(payload.get("title", "The season story")).strip() or "The season story",
        "kicker": str(payload.get("kicker", "Season story")).strip() or "Season story",
        "author": author_identity["name"] if author_identity else None,
        "author_slug": author_identity["slug"] if author_identity else None,
        "paragraphs": paragraphs,
        "preview_paragraphs": paragraphs[:2],
        "has_more": len(paragraphs) > 2,
    }
