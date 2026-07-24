from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from services.errors import F1DataError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = PROJECT_ROOT / "data" / "archive"
SEASONS_ROOT = ARCHIVE_ROOT / "seasons"


def current_season() -> int:
    """Return the season treated as live without a yearly code change."""
    return datetime.now(timezone.utc).year


def is_historical_season(season: int) -> bool:
    return season < current_season()


def season_archive_root(season: int) -> Path:
    return SEASONS_ROOT / str(season)


def has_complete_season_archive(season: int) -> bool:
    root = season_archive_root(season)
    return root.is_dir() and (root / "manifest.json").is_file()


def read_archive_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError as exc:
        raise F1DataError(
            f"Local historical archive file is missing: {path}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise F1DataError(
            f"Local historical archive file could not be read: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise F1DataError(f"Local historical archive file is invalid: {path}")
    return payload


def archived_path_for_api_request(path: str) -> Path | None:
    """Map an existing Jolpica request path to the committed local snapshot.

    Only endpoint shapes collected by ``download_season_archive.py`` are
    mapped. Current-season requests deliberately remain live.
    """
    clean_path = urlsplit(path).path.strip("/")

    match = re.fullmatch(r"(?P<season>\d{4})\.json", clean_path)
    if match:
        season = int(match.group("season"))
        if is_historical_season(season):
            return season_archive_root(season) / "schedule.json"
        return None

    patterns: tuple[tuple[str, str], ...] = (
        (
            r"(?P<season>\d{4})/driverstandings\.json",
            "driver_standings.json",
        ),
        (
            r"(?P<season>\d{4})/constructorstandings\.json",
            "constructor_standings.json",
        ),
    )
    for pattern, filename in patterns:
        match = re.fullmatch(pattern, clean_path)
        if match:
            season = int(match.group("season"))
            if is_historical_season(season):
                return season_archive_root(season) / filename
            return None

    match = re.fullmatch(
        r"(?P<season>\d{4})/(?P<round>\d+)/"
        r"(?P<dataset>results|driverstandings)\.json",
        clean_path,
    )
    if match:
        season = int(match.group("season"))
        if not is_historical_season(season):
            return None

        round_number = int(match.group("round"))
        filename = (
            "results.json"
            if match.group("dataset") == "results"
            else "driver_standings.json"
        )
        return (
            season_archive_root(season)
            / "races"
            / f"{round_number:02d}"
            / filename
        )

    return None
