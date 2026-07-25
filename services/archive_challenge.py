from __future__ import annotations

from collections import defaultdict
from datetime import date
from functools import lru_cache
from hashlib import sha256
import random
import re
from typing import Any

from services.archive_service import get_driver_championship_position_progression
from services.local_archive import read_archive_json, season_archive_root


MODERN_START_YEAR = 2000
RECENT_START_YEAR = 2017
MIN_ROUNDS = 4


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _standings_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    lists = (
        payload.get("MRData", {})
        .get("StandingsTable", {})
        .get("StandingsLists", [])
    )
    if not lists:
        return []
    return lists[0].get("DriverStandings", [])


def _race_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return []
    return races[0].get("Results", [])


def _season_years() -> list[int]:
    root = season_archive_root(MODERN_START_YEAR).parent
    if not root.exists():
        return []
    return sorted(
        int(child.name)
        for child in root.iterdir()
        if child.is_dir() and child.name.isdigit()
    )


def _difficulty_tier(
    *,
    season: int,
    final_position: int,
    wins: int,
    starts: int,
    season_rounds: int,
) -> int:
    """Assign recognisability-first difficulty tiers.

    Tier 1 is intentionally narrow: only recent, prominent campaigns.
    Older champions are held back for later tiers even when their season
    was dominant, because recognising a line depends on historical recall
    as much as the shape of the graph.
    """
    participation = starts / max(season_rounds, 1)
    is_recent = season >= RECENT_START_YEAR
    is_modern = season >= MODERN_START_YEAR
    is_champion = final_position == 1
    title_contender = final_position <= 3
    prominent_winner = wins >= 2
    race_winner = wins >= 1
    full_season = participation >= 0.72

    # Very recognisable modern campaigns from roughly the last decade.
    if is_recent and (
        is_champion
        or title_contender
        or prominent_winner
    ):
        return 1

    # Earlier post-2000 champions belong here, alongside recent race
    # winners and strong recent full-season campaigns.
    if (
        (is_modern and is_champion)
        or (
            is_recent
            and (
                race_winner
                or final_position <= 8
                or (full_season and final_position <= 12)
            )
        )
    ):
        return 2

    # Familiar post-2000 names, plus comparatively recent midfield
    # campaigns. Pre-2000 champions begin appearing only from this tier.
    if (
        (is_modern and (title_contender or race_winner or final_position <= 6))
        or (
            season >= 2010
            and full_season
            and final_position <= 14
        )
        or (
            season < MODERN_START_YEAR
            and is_champion
        )
    ):
        return 3

    # Less obvious modern campaigns and notable historic race winners.
    if (
        (is_modern and full_season and final_position <= 18)
        or (
            season < MODERN_START_YEAR
            and (
                title_contender
                or race_winner
            )
        )
    ):
        return 4

    return 5


def _eligible_pre_2000(final_position: int, wins: int) -> bool:
    return final_position <= 3 or wins >= 1



@lru_cache(maxsize=1)
def _career_wins_before_season() -> dict[tuple[str, int], int]:
    """Return cumulative GP wins before each season for every driver."""
    cumulative: dict[str,int] = defaultdict(int)
    lookup: dict[tuple[str,int],int] = {}
    for season in _season_years():
        root = season_archive_root(season)
        standings = read_archive_json(root / "driver_standings.json")
        ids = [r.get("Driver",{}).get("driverId","") for r in _standings_rows(standings)]
        for did in ids:
            if did:
                lookup[(did,season)] = cumulative.get(did,0)
        for rnd in (get_driver_championship_position_progression(season) or {}).get("rounds",[]):
            rp=root/"races"/f"{int(rnd['round']):02d}"/"results.json"
            if not rp.exists():
                continue
            for res in _race_rows(read_archive_json(rp)):
                if str(res.get("position"))=="1":
                    did=res.get("Driver",{}).get("driverId","")
                    if did:
                        cumulative[did]=cumulative.get(did,0)+1
    return lookup

@lru_cache(maxsize=1)
def build_challenge_pool() -> tuple[dict[str, Any], ...]:
    """Build the game pool entirely from the committed local archive."""
    questions: list[dict[str, Any]] = []

    for season in _season_years():
        progression = get_driver_championship_position_progression(season)
        if not progression or not progression.get("is_complete"):
            continue

        rounds = progression.get("rounds", [])
        if len(rounds) < MIN_ROUNDS:
            continue

        root = season_archive_root(season)
        final_payload = read_archive_json(root / "driver_standings.json")
        final_by_driver = {
            row.get("Driver", {}).get("driverId", ""): row
            for row in _standings_rows(final_payload)
        }

        result_summary: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "starts": 0,
                "wins": 0,
                "podiums": 0,
                "constructors": [],
                "round_results": {},
            }
        )
        result_rounds_available: set[int] = set()

        for round_info in rounds:
            round_number = int(round_info["round"])
            result_path = root / "races" / f"{round_number:02d}" / "results.json"
            if not result_path.is_file():
                continue
            result_rounds_available.add(round_number)
            for result in _race_rows(read_archive_json(result_path)):
                driver_id = result.get("Driver", {}).get("driverId", "")
                if not driver_id:
                    continue
                summary = result_summary[driver_id]
                summary["starts"] += 1
                finishing_position = int(result.get("position", 999) or 999)
                status = str(result.get("status", "") or "").strip()
                status_lower = status.casefold()
                position_text = str(
                    result.get("positionText", "") or ""
                ).strip()
                retirement_position_texts = {
                    "r",
                    "ret",
                    "d",
                    "dq",
                    "dsq",
                    "dns",
                    "dnq",
                    "nc",
                    "wd",
                }
                explicitly_retired = (
                    position_text.casefold()
                    in retirement_position_texts
                )
                did_not_finish = explicitly_retired or not (
                    status_lower == "finished"
                    or status.startswith("+")
                )

                summary["round_results"][round_number] = {
                    "position": (
                        finishing_position
                        if finishing_position < 999
                        else None
                    ),
                    "status": status or "Unknown",
                    "position_text": position_text,
                    "dnf": did_not_finish,
                }

                if finishing_position == 1:
                    summary["wins"] += 1
                if finishing_position <= 3:
                    summary["podiums"] += 1
                constructor = result.get("Constructor", {}).get("name")
                if constructor and constructor not in summary["constructors"]:
                    summary["constructors"].append(constructor)

        for driver in progression.get("drivers", []):
            driver_id = driver.get("driver_id", "")
            final_row = final_by_driver.get(driver_id, {})
            final_position = int(driver.get("final_position", 999) or 999)
            summary = result_summary[driver_id]
            starts = int(summary["starts"])
            wins = int(summary["wins"])

            if starts < MIN_ROUNDS:
                continue
            if season < MODERN_START_YEAR and not _eligible_pre_2000(final_position, wins):
                continue

            driver_data = final_row.get("Driver", {})
            constructors = summary["constructors"] or [driver.get("constructor_name", "Independent")]
            question_id = f"{season}:{driver_id}"

            chart_rounds: list[dict[str, Any]] = []
            for round_info in rounds:
                round_number = int(round_info["round"])
                key = str(round_number)
                standing = driver.get("positions", {}).get(key)
                finish = driver.get("finishes", {}).get(key)
                result_detail = summary["round_results"].get(
                    round_number,
                    {},
                )
                did_not_participate = (
                    round_number in result_rounds_available
                    and round_number not in summary["round_results"]
                )

                chart_rounds.append({
                    "round": round_number,
                    "label": round_info.get(
                        "short_name",
                        f"R{round_number}",
                    ),
                    "race_name": round_info.get("race_name", ""),
                    "standing": (
                        standing
                        if standing and standing < 999
                        else None
                    ),
                    "finish": (
                        finish
                        if finish and finish < 999
                        else result_detail.get("position")
                    ),
                    "status": result_detail.get("status"),
                    "position_text": result_detail.get("position_text"),
                    "dnf": bool(result_detail.get("dnf", False)),
                    "did_not_participate": did_not_participate,
                })

            tier = _difficulty_tier(
                season=season,
                final_position=final_position,
                wins=wins,
                starts=starts,
                season_rounds=len(rounds),
            )

            nationality = driver_data.get("nationality", "Unknown")
            driver_name = driver.get("driver_name", "Unknown driver")
            decade_start = (season // 10) * 10

            career_wins_before = _career_wins_before_season().get((driver_id, season), 0)

            if career_wins_before == 0:
                career_hint = "Entered this season without a Grand Prix victory."
            elif career_wins_before == 1:
                career_hint = "Career Grand Prix victories entering this season: 1"
            else:
                career_hint = f"Career Grand Prix victories entering this season: {career_wins_before}"

            questions.append({
                "id": question_id,
                "driver_id": driver_id,
                "driver_name": driver_name,
                "driver_name_normalised": _normalise(driver_name),
                "season": season,
                "tier": tier,
                "rounds": chart_rounds,
                "max_position": max(
                    [
                        value
                        for row in chart_rounds
                        for value in (row.get("standing"), row.get("finish"))
                        if isinstance(value, int)
                    ] or [20]
                ),
                "final_position": final_position,
                "wins": wins,
                "podiums": int(summary["podiums"]),
                "starts": starts,
                "points": float(final_row.get("points", 0) or 0),
                "constructors": constructors,
                "nationality": nationality,
                "hints": [
                    f"Constructor: {', '.join(constructors)}",
                    f"Nationality: {nationality}",
                    career_hint,
                    f"The season was between {decade_start} and {decade_start + 9}",
                ],
            })

    return tuple(questions)


def driver_options() -> list[str]:
    return sorted({question["driver_name"] for question in build_challenge_pool()})


def season_options() -> list[int]:
    return sorted({int(question["season"]) for question in build_challenge_pool()}, reverse=True)


def _tiers_for_streak(streak: int) -> tuple[int, ...]:
    """Keep the opening run approachable and introduce history slowly."""
    if streak <= 4:
        return (1,)
    if streak <= 9:
        return (1, 2)
    if streak <= 15:
        return (2,)
    if streak <= 22:
        return (2, 3)
    if streak <= 30:
        return (3,)
    if streak <= 40:
        return (3, 4)
    return (4, 5)


def choose_endless_question(streak: int, excluded_ids: set[str]) -> dict[str, Any]:
    pool = list(build_challenge_pool())
    tiers = _tiers_for_streak(max(0, streak))
    candidates = [
        question
        for question in pool
        if question["tier"] in tiers and question["id"] not in excluded_ids
    ]
    if not candidates:
        candidates = [question for question in pool if question["id"] not in excluded_ids]
    if not candidates:
        candidates = pool
    if not candidates:
        raise RuntimeError("The archive challenge pool is empty")
    return random.SystemRandom().choice(candidates)


def choose_daily_question(
    challenge_date: date | None = None,
) -> dict[str, Any]:
    """Choose a deterministic daily challenge with an easier bias.

    Most days use Tier 1, some use Tier 2, and only an occasional day
    reaches Tier 3. Historic champions therefore appear, but not as the
    default daily experience.
    """
    challenge_date = challenge_date or date.today()
    pool = list(build_challenge_pool())
    if not pool:
        raise RuntimeError("The archive challenge pool is empty")

    digest = sha256(
        f"f1-archive:{challenge_date.isoformat()}".encode()
    ).digest()

    roll = digest[0] % 10
    target_tier = 1 if roll < 6 else 2 if roll < 9 else 3

    candidates = sorted(
        (
            question
            for question in pool
            if question["tier"] == target_tier
        ),
        key=lambda item: item["id"],
    )

    if not candidates:
        candidates = sorted(
            (
                question
                for question in pool
                if question["tier"] <= 3
            ),
            key=lambda item: item["id"],
        )

    index = int.from_bytes(digest[1:9], "big") % len(candidates)
    return candidates[index]


def public_question(question: dict[str, Any], token: str, mode: str) -> dict[str, Any]:
    return {
        "token": token,
        "mode": mode,
        "rounds": question["rounds"],
        "season_round_count": len(question["rounds"]),
        "max_position": question["max_position"],
        "hint_count": len(question["hints"]),
    }


def evaluate_guess(question: dict[str, Any], driver: str, season: Any) -> tuple[bool, bool, bool]:
    driver_correct = _normalise(driver) == question["driver_name_normalised"]
    try:
        season_correct = int(season) == int(question["season"])
    except (TypeError, ValueError):
        season_correct = False
    return driver_correct and season_correct, driver_correct, season_correct
