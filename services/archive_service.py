from __future__ import annotations

from collections import Counter
from datetime import datetime
from hashlib import sha1
import re
from typing import Any

from flask import abort

from models.archive import ConstructorOption, DriverOption
from services.jolpica import get_json
from services.archive_index import get_archive_index
from services.season_story import get_season_story
from services.circuit_service import get_current_circuit_geometry
from services.live_archive import (
    current_season as live_current_season,
    get_live_archive_metadata,
    live_season_root,
)
from services.local_archive import (
    has_complete_season_archive,
    read_archive_json,
    season_archive_root,
)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default




def is_classified_result(position_text: Any, status: Any) -> bool:
    """Return whether a result belongs in the official classification.

    Jolpica normally uses a numeric ``positionText`` for classified cars, but
    recent provisional result feeds have occasionally paired a retirement-like
    position marker with a finishing status. Treat explicit finishing and
    lapped statuses as classified as well, while leaving genuine retirements
    untouched.
    """
    if str(position_text).strip().isdigit():
        return True

    normalised_status = str(status or "").strip()
    if normalised_status.casefold() in {"finished", "lapped"}:
        return True

    return bool(
        re.fullmatch(
            r"\+?\d+\s+laps?",
            normalised_status,
            flags=re.IGNORECASE,
        )
    )


def format_result_time(
    time_value: Any,
    status: Any,
    lap_deficit: int = 0,
) -> str:
    """Choose an unambiguous final-race time/status label.

    Same-lap finishers keep their time gap. Classified drivers behind by one
    or more complete laps are shown as ``1L``, ``2L`` and so on, because the
    API's residual time delta resets when the leader starts another lap.
    """
    normalised_status = str(status or "").strip()
    status_laps = re.fullmatch(
        r"\+?(\d+)\s+laps?",
        normalised_status,
        flags=re.IGNORECASE,
    )
    if status_laps:
        return f"{int(status_laps.group(1))}L"

    if normalised_status.casefold() == "lapped":
        return f"{max(lap_deficit, 1)}L"

    if lap_deficit > 0:
        return f"{lap_deficit}L"

    normalised_time = str(time_value or "").strip()
    return normalised_time or normalised_status or "—"


def format_date(value: str) -> str:
    # Portable across Windows, macOS and Linux.
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def get_all_seasons() -> list[int]:
    return list(get_archive_index().seasons)


def get_driver_options() -> list[DriverOption]:
    return list(get_archive_index().drivers)


def get_constructor_options() -> list[ConstructorOption]:
    return list(get_archive_index().constructors)


def get_constructor_options_for_driver(driver_id: str) -> list[ConstructorOption]:
    index = get_archive_index()
    constructor_ids = index.driver_constructors.get(driver_id, frozenset())
    return [
        constructor
        for constructor in index.constructors
        if constructor.constructor_id in constructor_ids
    ]


def get_driver_options_for_constructor(constructor_id: str) -> list[DriverOption]:
    index = get_archive_index()
    driver_ids = index.constructor_drivers.get(constructor_id, frozenset())
    return [
        driver
        for driver in index.drivers
        if driver.driver_id in driver_ids
    ]


TEAM_COLOURS = {
    "ferrari": "#e80020",
    "mercedes": "#00a19c",
    "mclaren": "#ff8700",
    "red_bull": "#3671c6",
    "red_bull_racing": "#3671c6",
    "williams": "#64c4ff",
    "aston_martin": "#229971",
    "alpine": "#ff87bc",
    "renault": "#fff500",
    "lotus_f1": "#d8b600",
    "lotus-climax": "#f1d317",
    "sauber": "#52e252",
    "bmw_sauber": "#6c88c4",
    "rb": "#6692ff",
    "toro_rosso": "#2446a8",
    "alphatauri": "#5e8faa",
    "haas": "#b6babd",
    "force_india": "#f596c8",
    "racing_point": "#f596c8",
    "toyota": "#eb0a1e",
    "honda": "#d7d7d7",
    "brawn": "#b8e600",
    "benetton": "#43a047",
    "brabham": "#1d4f91",
    "tyrrell": "#174ea6",
    "minardi": "#f0c808",
    "jordan": "#ffd900",
    "ligier": "#2554c7",
}


def get_team_colour(constructor_id: str) -> str:
    known = TEAM_COLOURS.get(constructor_id)
    if known:
        return known

    # Stable fallback colour for historic constructors without a curated colour.
    digest = sha1(constructor_id.encode("utf-8")).hexdigest()
    hue = int(digest[:4], 16) % 360
    return f"hsl({hue} 62% 55%)"


def _get_standings_list(payload: dict[str, Any]) -> dict[str, Any]:
    table = payload.get("MRData", {}).get("StandingsTable", {})
    lists = table.get("StandingsLists", [])
    return lists[0] if lists else {}


def get_season_driver_standings(season: int) -> list[dict[str, Any]]:
    payload = get_json(f"{season}/driverstandings.json?limit=100")
    rows = _get_standings_list(payload).get("DriverStandings", [])

    standings = []
    for row in rows:
        driver = row["Driver"]
        constructors = row.get("Constructors", [])
        primary_constructor = constructors[-1] if constructors else {}

        standings.append({
            "position": safe_int(row.get("position"), 999),
            "position_text": row.get("positionText", "—"),
            "points": row.get("points", "0"),
            "wins": safe_int(row.get("wins")),
            "driver_id": driver.get("driverId", ""),
            "driver_code": (
                driver.get("code")
                or driver.get("familyName", "")[:3].upper()
            ),
            "driver_name": f'{driver["givenName"]} {driver["familyName"]}',
            "constructor_id": primary_constructor.get("constructorId", ""),
            "constructor_name": primary_constructor.get("name", "Independent"),
            "team_colour": get_team_colour(
                primary_constructor.get("constructorId", "")
            ),
        })

    return sorted(standings, key=lambda item: item["position"])


def get_season_constructor_standings(season: int) -> list[dict[str, Any]]:
    if season < 1958:
        return []

    payload = get_json(f"{season}/constructorstandings.json?limit=100")
    rows = _get_standings_list(payload).get("ConstructorStandings", [])

    standings = []
    for row in rows:
        constructor = row["Constructor"]
        constructor_id = constructor.get("constructorId", "")
        standings.append({
            "position": safe_int(row.get("position"), 999),
            "position_text": row.get("positionText", "—"),
            "points": row.get("points", "0"),
            "wins": safe_int(row.get("wins")),
            "constructor_id": constructor_id,
            "constructor_name": constructor.get("name", "Unknown"),
            "nationality": constructor.get("nationality", ""),
            "team_colour": get_team_colour(constructor_id),
        })

    return sorted(standings, key=lambda item: item["position"])


def get_driver_positions_by_season(
    driver_id: str,
    seasons: list[int],
) -> dict[int, dict[str, Any]]:
    index = get_archive_index()
    positions: dict[int, dict[str, Any]] = {}
    for season in seasons:
        result = index.driver_results.get((driver_id, season))
        if result is None:
            continue
        positions[season] = {
            "position": result.position,
            "position_text": result.position_text,
            "points": result.points,
            "wins": result.wins,
            "constructors": list(result.constructors),
        }
    return positions


def get_filtered_seasons(
    selected_driver: str = "",
    selected_constructor: str = "",
) -> list[int]:
    """Return locally archived seasons matching the selected relationship."""
    index = get_archive_index()
    if selected_driver and selected_constructor:
        seasons = index.relationship_seasons.get(
            (selected_driver, selected_constructor),
            frozenset(),
        )
    elif selected_driver:
        seasons = index.driver_seasons.get(selected_driver, frozenset())
    elif selected_constructor:
        seasons = index.constructor_seasons.get(selected_constructor, frozenset())
    else:
        seasons = index.seasons
    return sorted(seasons, reverse=True)


def build_homepage_data(
    selected_driver: str = "",
    selected_constructor: str = "",
) -> dict[str, Any]:
    drivers = get_driver_options()
    constructors = get_constructor_options()

    selected_driver_name = next(
        (
            driver.name
            for driver in drivers
            if driver.driver_id == selected_driver
        ),
        "",
    )
    selected_constructor_name = next(
        (
            constructor.name
            for constructor in constructors
            if constructor.constructor_id == selected_constructor
        ),
        "",
    )

    seasons = get_filtered_seasons(
        selected_driver=selected_driver,
        selected_constructor=selected_constructor,
    )

    driver_positions = (
        get_driver_positions_by_season(selected_driver, seasons)
        if selected_driver
        else {}
    )
    season_cards = [
        {
            "year": season,
            "driver_result": driver_positions.get(season),
        }
        for season in seasons
    ]

    return {
        "seasons": season_cards,
        "drivers": drivers,
        "constructors": constructors,
        "selected_driver": selected_driver,
        "selected_constructor": selected_constructor,
        "selected_driver_name": selected_driver_name,
        "selected_constructor_name": selected_constructor_name,
        "filters_active": bool(selected_driver or selected_constructor),
    }


def get_season_page(season: int) -> dict[str, Any]:
    payload = get_json(f"{season}.json?limit=100")
    rows = payload["MRData"]["RaceTable"].get("Races", [])

    races = []
    for row in rows:
        circuit = row["Circuit"]
        location = circuit["Location"]
        races.append(
            {
                "round": safe_int(row["round"]),
                "name": row["raceName"],
                "formatted_date": format_date(row["date"]),
                "circuit": circuit["circuitName"],
                "locality": location["locality"],
                "country": location["country"],
            }
        )

    live_metadata = (
        get_live_archive_metadata(season)
        if season == live_current_season()
        else None
    )

    return {
        "season": season,
        "races": races,
        "driver_standings": get_season_driver_standings(season),
        "constructor_standings": get_season_constructor_standings(season),
        "position_progression": get_driver_championship_position_progression(season),
        "season_story": get_season_story(season),
        "live_archive": _format_live_archive_status(live_metadata),
    }



def get_driver_standings_after_round(
    season: int,
    round_number: int,
) -> list[dict[str, Any]]:
    """Return the Drivers' Championship classification after a race."""
    payload = get_json(
        f"{season}/{round_number}/driverstandings.json?limit=100"
    )
    rows = _get_standings_list(payload).get("DriverStandings", [])

    standings = []
    for row in rows:
        driver = row["Driver"]
        constructors = row.get("Constructors", [])
        primary_constructor = constructors[-1] if constructors else {}
        constructor_id = primary_constructor.get("constructorId", "")

        standings.append({
            "position": safe_int(row.get("position"), 999),
            "position_text": row.get("positionText", "—"),
            "points": float(row.get("points", 0)),
            "wins": safe_int(row.get("wins")),
            "driver_id": driver.get("driverId", ""),
            "driver_code": (
                driver.get("code")
                or driver.get("familyName", "")[:3].upper()
            ),
            "driver_name": f'{driver["givenName"]} {driver["familyName"]}',
            "constructor_id": constructor_id,
            "constructor_name": primary_constructor.get(
                "name",
                "Independent",
            ),
            "team_colour": get_team_colour(constructor_id),
        })

    return sorted(standings, key=lambda item: item["position"])


def get_race_championship_progression(
    season: int,
    round_number: int,
) -> dict[str, Any]:
    """
    Build the Drivers' Championship immediately before and after a race.

    The preceding round is the authoritative pre-race snapshot. A season
    opener has no prior championship classification, rather than an invented
    ordering of drivers tied on zero points.
    """
    after = get_driver_standings_after_round(season, round_number)
    before = (
        get_driver_standings_after_round(season, round_number - 1)
        if round_number > 1
        else []
    )

    before_by_driver = {
        entry["driver_id"]: entry
        for entry in before
    }

    enriched_after = []
    for entry in after:
        previous = before_by_driver.get(entry["driver_id"])
        points_before = previous["points"] if previous else 0.0

        enriched_after.append({
            **entry,
            "previous_position": previous["position"] if previous else None,
            "position_change": (
                previous["position"] - entry["position"]
                if previous
                else None
            ),
            "points_before": points_before,
            "points_gained": entry["points"] - points_before,
        })

    return {
        "before": before,
        "after": enriched_after,
        "is_season_opener": round_number == 1,
    }

def get_race_page(season: int, round_number: int) -> dict[str, Any]:
    payload = get_json(f"{season}/{round_number}/results.json?limit=100")
    races = payload["MRData"]["RaceTable"].get("Races", [])
    if not races:
        abort(404)

    row = races[0]
    circuit = row["Circuit"]
    results = row.get("Results", [])

    entries = []
    for result in results:
        driver = result["Driver"]
        constructor = result["Constructor"]
        fastest_lap = result.get("FastestLap", {})

        entries.append(
            {
                "position": result.get("positionText", "—"),
                "position_number": safe_int(result.get("position"), 999),
                "classified": is_classified_result(
                    result.get("positionText", ""),
                    result.get("status", ""),
                ),
                "grid": safe_int(result.get("grid")),
                "driver_code": (
                    driver.get("code")
                    or driver.get("familyName", "")[:3].upper()
                ),
                "driver_name": (
                    f'{driver["givenName"]} {driver["familyName"]}'
                ),
                "constructor": constructor["name"],
                "points": result.get("points", "0"),
                "laps": safe_int(result.get("laps")),
                "status": result.get("status", "Unknown"),
                "time": result.get("Time", {}).get("time", "—"),
                "result_time": "—",
                "fastest_lap_rank": safe_int(
                    fastest_lap.get("rank"), 999
                ),
                "fastest_lap_time": fastest_lap.get("Time", {}).get("time"),
            }
        )

    winner = min(
        entries,
        key=lambda entry: entry["position_number"],
    ) if entries else None
    pole = next((entry for entry in entries if entry["grid"] == 1), None)
    fastest = next(
        (entry for entry in entries if entry["fastest_lap_rank"] == 1),
        None,
    )

    winner_laps = winner["laps"] if winner else 0
    for entry in entries:
        lap_deficit = max(winner_laps - entry["laps"], 0)
        entry["result_time"] = format_result_time(
            entry["time"],
            entry["status"],
            lap_deficit if entry["classified"] else 0,
        )

    # Jolpica's status describes how a driver's race ended, but it is not a
    # reliable finisher test. Classified lapped cars use statuses such as
    # "+1 Lap", while an unclassified car may also have completed many laps.
    # A numeric positionText is the API's classification marker.
    finishers = [entry for entry in entries if entry["classified"]]
    dnfs = [entry for entry in entries if not entry["classified"]]

    biggest_gainers = sorted(
        (
            {
                **entry,
                "places_gained": entry["grid"] - entry["position_number"],
            }
            for entry in entries
            if entry["grid"] > 0 and entry["position_number"] < 999
        ),
        key=lambda entry: entry["places_gained"],
        reverse=True,
    )

    constructor_counts = Counter(
        entry["constructor"] for entry in entries
    )

    return {
        "season": season,
        "round": round_number,
        "name": row["raceName"],
        "formatted_date": format_date(row["date"]),
        "circuit": circuit["circuitName"],
        "circuit_id": circuit.get("circuitId", ""),
        "circuit_geometry": get_current_circuit_geometry(
            circuit.get("circuitId", "")
        ),
        "locality": circuit["Location"]["locality"],
        "country": circuit["Location"]["country"],
        "results": entries,
        "winner": winner,
        "pole": pole,
        "fastest": fastest,
        "dnfs": dnfs,
        "biggest_gainers": biggest_gainers[:3],
        "starter_count": len(entries),
        "finisher_count": len(finishers),
        "constructor_count": len(constructor_counts),
        "live_archive": _format_live_archive_status(
            get_live_archive_metadata(season)
            if season == live_current_season()
            else None
        ),
        "championship": get_race_championship_progression(
            season,
            round_number,
        ),
    }


def get_driver_championship_position_progression(
    season: int,
) -> dict[str, Any] | None:
    """Build the round-by-round championship-position chart from local data.

    Completed seasons intentionally use only the committed archive. The live
    season is left for the later refresh/cache implementation.
    """
    if has_complete_season_archive(season):
        season_root = season_archive_root(season)
    elif season == live_current_season():
        season_root = live_season_root(season)
        if not (season_root / "schedule.json").is_file():
            return None
    else:
        return None
    schedule_payload = read_archive_json(season_root / "schedule.json")
    schedule_rows = (
        schedule_payload.get("MRData", {})
        .get("RaceTable", {})
        .get("Races", [])
    )

    rounds: list[dict[str, Any]] = []
    drivers: dict[str, dict[str, Any]] = {}

    for race in schedule_rows:
        round_number = safe_int(race.get("round"))
        if round_number <= 0:
            continue

        standings_path = (
            season_root
            / "races"
            / f"{round_number:02d}"
            / "driver_standings.json"
        )
        if not standings_path.is_file():
            continue
        payload = read_archive_json(standings_path)
        standings_list = _get_standings_list(payload)
        rows = standings_list.get("DriverStandings", [])

        round_entry = {
            "round": round_number,
            "race_name": race.get("raceName", f"Round {round_number}"),
            "short_name": _short_race_name(
                race.get("raceName", f"R{round_number}")
            ),
        }
        rounds.append(round_entry)

        for row in rows:
            driver = row.get("Driver", {})
            driver_id = driver.get("driverId", "")
            if not driver_id:
                continue

            constructors = row.get("Constructors", [])
            constructor = constructors[-1] if constructors else {}
            entry = drivers.setdefault(
                driver_id,
                {
                    "driver_id": driver_id,
                    "driver_name": (
                        f"{driver.get('givenName', '')} "
                        f"{driver.get('familyName', '')}"
                    ).strip(),
                    "driver_code": (
                        driver.get("code")
                        or driver.get("familyName", "")[:3].upper()
                    ),
                    "constructor_name": constructor.get("name", "Independent"),
                    "team_colour": get_team_colour(
                        constructor.get("constructorId", "")
                    ),
                    "positions": {},
                    "points": {},
                    "final_position": 999,
                },
            )
            entry["positions"][str(round_number)] = safe_int(
                row.get("position"),
                999,
            )
            entry["points"][str(round_number)] = float(row.get("points", 0))

    final_path = season_root / "driver_standings.json"
    final_payload = read_archive_json(final_path) if final_path.is_file() else {}
    final_rows = _get_standings_list(final_payload).get("DriverStandings", [])
    for row in final_rows:
        driver_id = row.get("Driver", {}).get("driverId", "")
        if driver_id in drivers:
            drivers[driver_id]["final_position"] = safe_int(
                row.get("position"),
                999,
            )

    ordered_drivers = sorted(
        drivers.values(),
        key=lambda item: (item["final_position"], item["driver_name"]),
    )

    return {
        "season": season,
        "rounds": rounds,
        "drivers": ordered_drivers,
        "max_position": max(
            (
                position
                for driver in ordered_drivers
                for position in driver["positions"].values()
                if position < 999
            ),
            default=0,
        ),
        "default_driver_ids": [
            driver["driver_id"] for driver in ordered_drivers
        ],
    }


def _format_live_archive_status(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None

    value = metadata.get("last_successful_update")
    formatted = None
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            formatted = parsed.astimezone().strftime("%d %B %Y at %H:%M %Z")
        except ValueError:
            formatted = str(value)

    return {
        "status": metadata.get("status", "unknown"),
        "last_updated": value,
        "last_updated_formatted": formatted,
        "completed_round_count": safe_int(metadata.get("completed_round_count")),
        "scheduled_round_count": safe_int(metadata.get("scheduled_round_count")),
        "consecutive_failures": safe_int(metadata.get("consecutive_failures")),
    }


def _short_race_name(race_name: str) -> str:
    name = str(race_name).strip()
    for suffix in (" Grand Prix", " GP"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name
