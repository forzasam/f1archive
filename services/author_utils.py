from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTHOR_ROOT = PROJECT_ROOT / "data" / "editorial" / "authors"


def get_author_identity(slug: str) -> dict[str, str] | None:
    """Load the display name for an exact author-profile slug.

    Story JSON files refer to authors by the ``slug`` field. The slug must
    exactly match both the author-profile filename and the profile's own
    ``slug`` value. Invalid or missing profiles are treated as uncredited.
    """
    requested_slug = str(slug).strip()
    if not requested_slug or Path(requested_slug).name != requested_slug:
        return None

    path = AUTHOR_ROOT / f"{requested_slug}.json"
    if not path.is_file():
        return None

    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    profile_slug = str(payload.get("slug", "")).strip()
    name = str(payload.get("name", "")).strip()
    if profile_slug != requested_slug or path.stem != requested_slug or not name:
        return None

    return {"slug": requested_slug, "name": name}
