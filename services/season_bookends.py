from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.author_utils import get_author_identity

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOKEND_ROOT = PROJECT_ROOT / "data" / "editorial" / "season_bookends"
VALID_KINDS = {"setting_the_stakes", "aftermath"}


def bookend_path(season: int, kind: str) -> Path:
    return BOOKEND_ROOT / str(season) / f"{kind}.json"


def get_season_bookend(season: int, kind: str) -> dict[str, Any] | None:
    if kind not in VALID_KINDS:
        return None
    path = bookend_path(season, kind)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    paragraphs = [str(p).strip() for p in payload.get("paragraphs", []) if str(p).strip()]
    if not paragraphs:
        return None
    author = get_author_identity(payload.get("slug", ""))
    defaults = {
        "setting_the_stakes": ("Setting the stakes", "Before the lights go out"),
        "aftermath": ("Aftermath", "After the chequered flag"),
    }
    title, kicker = defaults[kind]
    return {
        "kind": kind,
        "title": str(payload.get("title", title)).strip() or title,
        "kicker": str(payload.get("kicker", kicker)).strip() or kicker,
        "paragraphs": paragraphs,
        "author": author["name"] if author else None,
        "author_slug": author["slug"] if author else None,
    }
