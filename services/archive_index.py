from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from models.archive import ConstructorOption, DriverOption
from services.live_archive import current_season, live_season_root
from services.local_archive import SEASONS_ROOT, read_archive_json


@dataclass(frozen=True)
class DriverSeasonResult:
    position: int
    position_text: str
    points: str
    wins: int
    constructors: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveIndex:
    seasons: tuple[int, ...]
    drivers: tuple[DriverOption, ...]
    constructors: tuple[ConstructorOption, ...]
    driver_seasons: dict[str, frozenset[int]]
    constructor_seasons: dict[str, frozenset[int]]
    relationship_seasons: dict[tuple[str, str], frozenset[int]]
    driver_results: dict[tuple[str, int], DriverSeasonResult]
    driver_constructors: dict[str, frozenset[str]]
    constructor_drivers: dict[str, frozenset[str]]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _standings_rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    lists = (
        payload.get("MRData", {})
        .get("StandingsTable", {})
        .get("StandingsLists", [])
    )
    if not lists:
        return []
    rows = lists[0].get(key, [])
    return rows if isinstance(rows, list) else []


def _available_season_roots() -> list[tuple[int, Path]]:
    roots: dict[int, Path] = {}
    if SEASONS_ROOT.is_dir():
        for child in SEASONS_ROOT.iterdir():
            if child.is_dir() and child.name.isdigit():
                season = int(child.name)
                if (child / "driver_standings.json").is_file():
                    roots[season] = child

    live_season = current_season()
    live_root = live_season_root(live_season)
    if (live_root / "driver_standings.json").is_file():
        roots[live_season] = live_root

    return sorted(roots.items(), reverse=True)


@lru_cache(maxsize=1)
def get_archive_index() -> ArchiveIndex:
    driver_meta: dict[str, DriverOption] = {}
    constructor_meta: dict[str, ConstructorOption] = {}
    driver_seasons: dict[str, set[int]] = {}
    constructor_seasons: dict[str, set[int]] = {}
    relationship_seasons: dict[tuple[str, str], set[int]] = {}
    driver_results: dict[tuple[str, int], DriverSeasonResult] = {}
    driver_constructors: dict[str, set[str]] = {}
    constructor_drivers: dict[str, set[str]] = {}
    seasons: list[int] = []

    for season, root in _available_season_roots():
        seasons.append(season)
        payload = read_archive_json(root / "driver_standings.json")
        for row in _standings_rows(payload, "DriverStandings"):
            driver = row.get("Driver", {})
            driver_id = str(driver.get("driverId", "")).strip()
            if not driver_id:
                continue

            name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip()
            driver_meta[driver_id] = DriverOption(
                driver_id=driver_id,
                name=name or driver_id,
                nationality=str(driver.get("nationality", "")),
            )
            driver_seasons.setdefault(driver_id, set()).add(season)

            constructor_names: list[str] = []
            for constructor in row.get("Constructors", []) or []:
                constructor_id = str(constructor.get("constructorId", "")).strip()
                if not constructor_id:
                    continue
                constructor_name = str(constructor.get("name", constructor_id))
                constructor_names.append(constructor_name)
                constructor_meta[constructor_id] = ConstructorOption(
                    constructor_id=constructor_id,
                    name=constructor_name,
                    nationality=str(constructor.get("nationality", "")),
                )
                constructor_seasons.setdefault(constructor_id, set()).add(season)
                relationship_seasons.setdefault((driver_id, constructor_id), set()).add(season)
                driver_constructors.setdefault(driver_id, set()).add(constructor_id)
                constructor_drivers.setdefault(constructor_id, set()).add(driver_id)

            driver_results[(driver_id, season)] = DriverSeasonResult(
                position=_safe_int(row.get("position"), 999),
                position_text=str(row.get("positionText", "—")),
                points=str(row.get("points", "0")),
                wins=_safe_int(row.get("wins")),
                constructors=tuple(constructor_names),
            )

        constructor_path = root / "constructor_standings.json"
        if constructor_path.is_file():
            constructor_payload = read_archive_json(constructor_path)
            for row in _standings_rows(constructor_payload, "ConstructorStandings"):
                constructor = row.get("Constructor", {})
                constructor_id = str(constructor.get("constructorId", "")).strip()
                if not constructor_id:
                    continue
                constructor_meta[constructor_id] = ConstructorOption(
                    constructor_id=constructor_id,
                    name=str(constructor.get("name", constructor_id)),
                    nationality=str(constructor.get("nationality", "")),
                )
                constructor_seasons.setdefault(constructor_id, set()).add(season)

    return ArchiveIndex(
        seasons=tuple(sorted(set(seasons), reverse=True)),
        drivers=tuple(sorted(driver_meta.values(), key=lambda item: item.name)),
        constructors=tuple(sorted(constructor_meta.values(), key=lambda item: item.name)),
        driver_seasons={key: frozenset(value) for key, value in driver_seasons.items()},
        constructor_seasons={key: frozenset(value) for key, value in constructor_seasons.items()},
        relationship_seasons={key: frozenset(value) for key, value in relationship_seasons.items()},
        driver_results=driver_results,
        driver_constructors={key: frozenset(value) for key, value in driver_constructors.items()},
        constructor_drivers={key: frozenset(value) for key, value in constructor_drivers.items()},
    )


def clear_archive_index_cache() -> None:
    """Allow the live archive refresher or tests to rebuild the local index."""
    get_archive_index.cache_clear()
