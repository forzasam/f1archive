#!/usr/bin/env python3
"""Audit archived driver championship points against race-by-race data.

The audit deliberately separates eras where a simple points delta comparison is
valid from eras with dropped-score rules/shared drives and modern sprint points.
It also contains explicit regressions for the two archive seasons whose source
standings snapshots were found to be internally wrong (1976 and 1977).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "archive" / "seasons"


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def standings(path: Path) -> dict[str, float]:
    rows = load(path)["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    return {r["Driver"]["driverId"]: float(r["points"]) for r in rows}


def race_points(path: Path) -> dict[str, float]:
    rows = load(path)["MRData"]["RaceTable"]["Races"][0]["Results"]
    return {r["Driver"]["driverId"]: float(r.get("points", 0)) for r in rows}


def race_rounds(races_dir: Path) -> list[Path]:
    """Return numeric race-round directories only, ignoring files such as .DS_Store."""
    return sorted(
        (p for p in races_dir.iterdir() if p.is_dir() and p.name.isdigit()),
        key=lambda p: int(p.name),
    )


def audit_delta_season(year: int) -> list[str]:
    """Exact check for seasons without dropped scores or sprint points."""
    season = ROOT / str(year)
    previous: dict[str, float] = {}
    errors: list[str] = []

    for race in race_rounds(season / "races"):
        current = standings(race / "driver_standings.json")
        awarded = race_points(race / "results.json")
        for driver, points in awarded.items():
            delta = current.get(driver, 0.0) - previous.get(driver, 0.0)
            if abs(delta - points) > 1e-9:
                errors.append(
                    f"{year} R{int(race.name)} {driver}: "
                    f"race={points:g}, standings delta={delta:g}"
                )
        previous = current

    return errors


def main() -> int:
    errors: list[str] = []
    seasons = sorted(int(p.name) for p in ROOT.iterdir() if p.is_dir() and p.name.isdigit())

    # Every season-level snapshot must agree with its final round snapshot.
    for year in seasons:
        season = ROOT / str(year)
        races = season / "races"
        if not races.exists():
            continue

        rounds = race_rounds(races)
        if not rounds:
            continue

        if standings(season / "driver_standings.json") != standings(
            rounds[-1] / "driver_standings.json"
        ):
            errors.append(
                f"{year}: final season standings differ from final round snapshot"
            )

    # 1991-2020: every race point must flow directly into the standings. Before
    # 1991, dropped-score/shared-drive rules make that comparison invalid; from
    # 2021 onward, sprint points are absent from results.json and also invalidate it.
    for year in range(1991, 2021):
        if (ROOT / str(year)).exists():
            errors.extend(audit_delta_season(year))

    # Confirmed historical-source regressions. These are intentionally explicit:
    # they catch the exact failures that triggered this audit without pretending
    # pre-1991 championships all used simple cumulative scoring.
    checkpoints = {
        (1976, 7): {"lauda": 52},
        (1976, 15): {"lauda": 68, "scheckter": 49, "hunt": 65},
        (1976, 16): {"lauda": 68, "scheckter": 49, "hunt": 69},
        (1977, 15): {"lauda": 72, "reutemann": 36},
        (1977, 17): {
            "lauda": 72,
            "scheckter": 55,
            "reutemann": 42,
            "hunt": 40,
        },
    }

    for (year, rnd), expected in checkpoints.items():
        got = standings(
            ROOT / str(year) / "races" / f"{rnd:02d}" / "driver_standings.json"
        )
        for driver, points in expected.items():
            if got.get(driver) != points:
                errors.append(
                    f"{year} R{rnd} {driver}: expected {points}, got {got.get(driver)}"
                )

    if errors:
        print(f"FAILED: {len(errors)} championship-point issue(s)")
        for error in errors:
            print(" -", error)
        return 1

    print(
        f"PASS: audited {len(seasons)} archived seasons "
        f"({seasons[0]}-{seasons[-1]})."
    )
    print(" - final season snapshots match final-round snapshots")
    print(" - all 1991-2020 race-point deltas are internally consistent")
    print(" - corrected 1976/1977 historical checkpoints pass")
    print(
        " - pre-1991 dropped-score/shared-drive eras and 2021+ sprint eras "
        "are excluded from naive delta checks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
