from __future__ import annotations

from collections import Counter
from datetime import datetime
from hashlib import sha1
from typing import Any

from flask import abort

from models.archive import ConstructorOption, DriverOption
from services.jolpica import get_json
from services.circuit_service import get_current_circuit_geometry


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_date(value: str) -> str:
    # Portable across Windows, macOS and Linux.
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def get_all_seasons() -> list[int]:
    payload = get_json("seasons.json?limit=100")
    rows = payload["MRData"]["SeasonTable"].get("Seasons", [])
    return sorted(
        (safe_int(row["season"]) for row in rows),
        reverse=True,
    )


def get_driver_options() -> list[DriverOption]:
    # Jolpica paginates large collections. Request every page rather than
    # assuming one oversized limit will be honoured.
    rows: list[dict[str, Any]] = []
    limit = 100
    offset = 0

    while True:
        payload = get_json(f"drivers.json?limit={limit}&offset={offset}")
        mr_data = payload["MRData"]
        page = mr_data["DriverTable"].get("Drivers", [])
        rows.extend(page)

        total = safe_int(mr_data.get("total"), len(rows))
        offset += len(page)
        if not page or offset >= total:
            break

    drivers = [
        DriverOption(
            driver_id=row["driverId"],
            name=f'{row["givenName"]} {row["familyName"]}',
            nationality=row.get("nationality", ""),
        )
        for row in rows
    ]
    return sorted(drivers, key=lambda driver: driver.name)


def get_constructor_options() -> list[ConstructorOption]:
    payload = get_json("constructors.json?limit=1000")
    rows = payload["MRData"]["ConstructorTable"].get("Constructors", [])

    constructors = [
        ConstructorOption(
            constructor_id=row["constructorId"],
            name=row["name"],
            nationality=row.get("nationality", ""),
        )
        for row in rows
    ]
    return sorted(constructors, key=lambda constructor: constructor.name)



def get_constructor_options_for_driver(driver_id: str) -> list[ConstructorOption]:
    payload = get_json(f"drivers/{driver_id}/constructors.json?limit=200")
    rows = payload["MRData"]["ConstructorTable"].get("Constructors", [])
    return sorted(
        (
            ConstructorOption(
                constructor_id=row["constructorId"],
                name=row["name"],
                nationality=row.get("nationality", ""),
            )
            for row in rows
        ),
        key=lambda constructor: constructor.name,
    )


def get_driver_options_for_constructor(constructor_id: str) -> list[DriverOption]:
    rows: list[dict[str, Any]] = []
    limit = 100
    offset = 0

    while True:
        payload = get_json(
            f"constructors/{constructor_id}/drivers.json?limit={limit}&offset={offset}"
        )
        mr_data = payload["MRData"]
        page = mr_data["DriverTable"].get("Drivers", [])
        rows.extend(page)

        total = safe_int(mr_data.get("total"), len(rows))
        offset += len(page)
        if not page or offset >= total:
            break

    return sorted(
        (
            DriverOption(
                driver_id=row["driverId"],
                name=f'{row["givenName"]} {row["familyName"]}',
                nationality=row.get("nationality", ""),
            )
            for row in rows
        ),
        key=lambda driver: driver.name,
    )


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
    positions: dict[int, dict[str, Any]] = {}

    for season in seasons:
        payload = get_json(
            f"{season}/drivers/{driver_id}/driverstandings.json?limit=10"
        )
        rows = _get_standings_list(payload).get("DriverStandings", [])
        if not rows:
            continue

        row = rows[0]
        constructors = row.get("Constructors", [])
        constructor_names = [item.get("name", "") for item in constructors]
        positions[season] = {
            "position": safe_int(row.get("position"), 999),
            "position_text": row.get("positionText", "—"),
            "points": row.get("points", "0"),
            "wins": safe_int(row.get("wins")),
            "constructors": constructor_names,
        }

    return positions

def get_filtered_seasons(
    selected_driver: str = "",
    selected_constructor: str = "",
) -> list[int]:
    """
    Return seasons matching the selected archive relationship.

    When both filters are supplied, they must be applied in the same Jolpica
    query. Intersecting the driver's career seasons with the constructor's
    seasons would only prove that both competed during the same year; it would
    not prove that the driver raced for that constructor.
    """
    if selected_driver and selected_constructor:
        path = (
            f"drivers/{selected_driver}/constructors/"
            f"{selected_constructor}/seasons.json?limit=100"
        )
    elif selected_driver:
        path = f"drivers/{selected_driver}/seasons.json?limit=100"
    elif selected_constructor:
        path = f"constructors/{selected_constructor}/seasons.json?limit=100"
    else:
        return get_all_seasons()

    payload = get_json(path)
    rows = payload["MRData"]["SeasonTable"].get("Seasons", [])

    return sorted(
        {safe_int(row["season"]) for row in rows},
        reverse=True,
    )


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

    return {
        "season": season,
        "races": races,
        "driver_standings": get_season_driver_standings(season),
        "constructor_standings": get_season_constructor_standings(season),
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
                "classified": str(
                    result.get("positionText", "")
                ).strip().isdigit(),
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
        "championship": get_race_championship_progression(
            season,
            round_number,
        ),
    }
