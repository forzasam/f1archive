from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from services.race_story import get_race_story
from services.season_story import get_season_story


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTHOR_ROOT = PROJECT_ROOT / "data" / "editorial" / "authors"
SEASON_STORY_ROOT = PROJECT_ROOT / "data" / "editorial" / "seasons"
RACE_STORY_ROOT = PROJECT_ROOT / "data" / "editorial" / "races"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _valid_social_links(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    links: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        url = str(item.get("url", "")).strip()
        parsed = urlparse(url)
        if label and parsed.scheme in {"http", "https"} and parsed.netloc:
            links.append({"label": label, "url": url})
    return links


def _discover_story_contributions() -> dict[str, dict[str, Any]]:
    authors: dict[str, dict[str, Any]] = {}

    for path in sorted(SEASON_STORY_ROOT.glob("*.json")):
        if not path.stem.isdigit():
            continue
        season = int(path.stem)
        story = get_season_story(season)
        if not story or not story.get("author_slug") or not story.get("author"):
            continue
        slug = story["author_slug"]
        entry = authors.setdefault(
            slug,
            {"name": story["author"], "season_stories": [], "race_stories": []},
        )
        entry["season_stories"].append(
            {
                "type": "season",
                "title": story["title"],
                "season": season,
                "label": f"{season} Formula One season",
                "url": f"/season/{season}",
            }
        )

    for path in sorted(RACE_STORY_ROOT.glob("*/*.json")):
        if not path.parent.name.isdigit() or not path.stem.isdigit():
            continue
        season = int(path.parent.name)
        round_number = int(path.stem)
        story = get_race_story(season, round_number)
        if not story or not story.get("author_slug") or not story.get("author"):
            continue
        slug = story["author_slug"]
        entry = authors.setdefault(
            slug,
            {"name": story["author"], "season_stories": [], "race_stories": []},
        )
        entry["race_stories"].append(
            {
                "type": "race",
                "title": story["title"],
                "season": season,
                "round": round_number,
                "label": f"{season} Formula One season · Round {round_number}",
                "url": f"/season/{season}/race/{round_number}",
            }
        )

    for entry in authors.values():
        entry["season_stories"].sort(key=lambda item: item["season"], reverse=True)
        entry["race_stories"].sort(
            key=lambda item: (item["season"], item["round"]), reverse=True
        )

    return authors


def _load_profiles() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if not AUTHOR_ROOT.exists():
        return profiles

    for path in sorted(AUTHOR_ROOT.glob("*.json")):
        payload = _read_json(path)
        if not payload:
            continue
        slug = str(payload.get("slug", "")).strip()
        name = str(payload.get("name", "")).strip()
        if not slug or slug != path.stem or not name:
            continue
        profiles[slug] = {
            "slug": slug,
            "name": name,
            "description": str(payload.get("description", "")).strip(),
            "social_links": _valid_social_links(payload.get("social_links")),
            "featured_stories": payload.get("featured_stories", []),
        }
    return profiles


def _resolve_featured_story(reference: Any, expected_author_slug: str) -> dict[str, Any] | None:
    if not isinstance(reference, dict):
        return None

    story_type = str(reference.get("type", "")).strip().lower()
    try:
        season = int(reference.get("season"))
    except (TypeError, ValueError):
        return None

    if story_type == "season":
        story = get_season_story(season)
        if not story or story.get("author_slug") != expected_author_slug:
            return None
        return {
            "type": "season",
            "title": story["title"],
            "label": f"{season} Formula One season",
            "url": f"/season/{season}",
        }

    if story_type == "race":
        try:
            round_number = int(reference.get("round"))
        except (TypeError, ValueError):
            return None
        story = get_race_story(season, round_number)
        if not story or story.get("author_slug") != expected_author_slug:
            return None
        return {
            "type": "race",
            "title": story["title"],
            "label": f"{season} Formula One season · Round {round_number}",
            "url": f"/season/{season}/race/{round_number}",
        }

    return None


def get_authors() -> list[dict[str, Any]]:
    contributions = _discover_story_contributions()
    profiles = _load_profiles()
    authors: list[dict[str, Any]] = []

    for slug, profile in profiles.items():
        contribution = contributions.get(
            slug,
            {"name": profile["name"], "season_stories": [], "race_stories": []},
        )
        season_stories = contribution["season_stories"]
        race_stories = contribution["race_stories"]
        featured = [
            resolved
            for reference in profile.get("featured_stories", [])[:3]
            if (resolved := _resolve_featured_story(reference, slug)) is not None
        ]

        authors.append(
            {
                "slug": slug,
                "name": profile["name"],
                "description": profile.get("description", ""),
                "social_links": profile.get("social_links", []),
                "season_stories": season_stories,
                "race_stories": race_stories,
                "article_count": len(season_stories) + len(race_stories),
                "season_article_count": len(season_stories),
                "race_article_count": len(race_stories),
                "featured_stories": featured,
                "all_stories": season_stories + race_stories,
            }
        )

    return sorted(authors, key=lambda author: (-author["article_count"], author["name"].lower()))


def get_author(slug: str) -> dict[str, Any] | None:
    """Return an author profile by its exact profile slug."""
    requested_slug = str(slug).strip()
    if not requested_slug:
        return None
    return next(
        (author for author in get_authors() if author["slug"] == requested_slug),
        None,
    )
