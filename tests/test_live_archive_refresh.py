from __future__ import annotations

import json
from pathlib import Path

import services.live_archive as live_archive


def race_payload(season: int, round_number: int) -> dict:
    return {
        "MRData": {
            "RaceTable": {
                "season": str(season),
                "round": str(round_number),
                "Races": [
                    {
                        "season": str(season),
                        "round": str(round_number),
                        "raceName": f"Round {round_number}",
                        "Results": [{"position": "1"}],
                    }
                ],
            }
        }
    }


def standings_payload(season: int, round_number: int) -> dict:
    return {
        "MRData": {
            "StandingsTable": {
                "season": str(season),
                "round": str(round_number),
                "StandingsLists": [{"round": str(round_number)}],
            }
        }
    }


def schedule_payload(season: int, rounds: int) -> dict:
    return {
        "MRData": {
            "RaceTable": {
                "season": str(season),
                "Races": [
                    {"season": str(season), "round": str(round_number)}
                    for round_number in range(1, rounds + 1)
                ],
            }
        }
    }


def test_refresh_backfills_rounds_missing_from_local_cache(monkeypatch, tmp_path: Path):
    season = 2026
    monkeypatch.setenv("LIVE_ARCHIVE_ROOT", str(tmp_path))
    monkeypatch.setattr(live_archive, "current_season", lambda: season)

    season_root = tmp_path / "seasons" / str(season)
    for round_number in (1, 2):
        round_root = season_root / "races" / f"{round_number:02d}"
        live_archive.write_json_atomic(round_root / "results.json", race_payload(season, round_number))
        live_archive.write_json_atomic(
            round_root / "driver_standings.json",
            standings_payload(season, round_number),
        )

    responses = {
        f"{season}.json?limit=100": schedule_payload(season, 6),
        "current/last/results.json": race_payload(season, 4),
        f"{season}/4/driverstandings.json?limit=100": standings_payload(season, 4),
        f"{season}/4/constructorstandings.json?limit=100": standings_payload(season, 4),
        f"{season}/3/results.json?limit=100": race_payload(season, 3),
        f"{season}/3/driverstandings.json?limit=100": standings_payload(season, 3),
    }
    requested: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_json(self, path: str) -> dict:
            requested.append(path)
            return responses[path]

        def close(self) -> None:
            pass

    monkeypatch.setattr(live_archive, "LiveArchiveClient", FakeClient)

    metadata = live_archive.refresh_live_archive(season)

    assert metadata["schema_version"] == 2
    assert metadata["status"] == "healthy"
    assert metadata["completed_rounds"] == [1, 2, 3, 4]
    assert metadata["latest_completed_round"] == 4
    assert (season_root / "races" / "03" / "results.json").is_file()
    assert (season_root / "races" / "04" / "results.json").is_file()
    assert f"{season}/1/results.json?limit=100" not in requested
    assert f"{season}/2/results.json?limit=100" not in requested
    assert f"{season}/results.json?limit=2000" not in requested

    stored_latest = json.loads(
        (season_root / "races" / "04" / "results.json").read_text(encoding="utf-8")
    )
    assert stored_latest["MRData"]["RaceTable"]["round"] == "4"


def test_old_metadata_schema_forces_immediate_refresh(monkeypatch, tmp_path: Path):
    season = 2026
    monkeypatch.setenv("LIVE_ARCHIVE_ROOT", str(tmp_path))
    monkeypatch.setattr(live_archive, "current_season", lambda: season)
    live_archive.write_json_atomic(
        live_archive.metadata_path(season),
        {
            "schema_version": 1,
            "season": season,
            "last_successful_update": live_archive.utc_now_iso(),
        },
    )

    assert live_archive.live_archive_is_stale(season, ttl_seconds=3600) is True
