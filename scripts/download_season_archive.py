from __future__ import annotations

import argparse
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = PROJECT_ROOT / "data" / "archive"
SEASONS_ROOT = ARCHIVE_ROOT / "seasons"
INDEX_PATH = ARCHIVE_ROOT / "index.json"

DEFAULT_API_BASE = "https://api.jolpi.ca/ergast/f1"
DEFAULT_SEASON = 1950
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 5

logger = logging.getLogger("f1archive.importer")


class ArchiveImportError(RuntimeError):
    """Raised when a season snapshot cannot be downloaded or validated."""


@dataclass(frozen=True)
class DownloadSettings:
    api_base: str
    delay_seconds: float
    timeout_seconds: int
    max_retries: int
    force: bool


class JolpicaClient:
    """Small, polite Jolpica client with retries and request pacing."""

    def __init__(self, settings: DownloadSettings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "F1Archive/1.0 (https://f1archive.net)",
            }
        )
        self._last_request_finished_at: float | None = None

    def close(self) -> None:
        self.session.close()

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_finished_at is None:
            return

        elapsed = time.monotonic() - self._last_request_finished_at
        remaining = self.settings.delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def get_json(self, path: str) -> dict[str, Any]:
        url = f"{self.settings.api_base.rstrip('/')}/{path.lstrip('/')}"
        last_error: Exception | None = None

        for attempt in range(1, self.settings.max_retries + 1):
            self._wait_for_rate_limit()
            logger.info("GET %s (attempt %s/%s)", url, attempt, self.settings.max_retries)

            try:
                response = self.session.get(
                    url,
                    timeout=(10, self.settings.timeout_seconds),
                )
                self._last_request_finished_at = time.monotonic()

                if response.status_code == 404:
                    raise requests.HTTPError(
                        f"404 Client Error for url: {url}",
                        response=response,
                    )

                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_seconds = max(float(retry_after), 0.0)
                        except ValueError:
                            wait_seconds = 0.0
                    else:
                        wait_seconds = min(2 ** (attempt - 1), 30) + random.uniform(0, 0.5)

                    logger.warning(
                        "Jolpica returned HTTP %s; retrying in %.1fs",
                        response.status_code,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Jolpica response was not a JSON object")
                return payload

            except requests.HTTPError:
                raise
            except (requests.RequestException, ValueError) as exc:
                self._last_request_finished_at = time.monotonic()
                last_error = exc
                if attempt >= self.settings.max_retries:
                    break

                wait_seconds = min(2 ** (attempt - 1), 30) + random.uniform(0, 0.5)
                logger.warning(
                    "Request failed (%s); retrying in %.1fs",
                    type(exc).__name__,
                    wait_seconds,
                )
                time.sleep(wait_seconds)

        raise ArchiveImportError(f"Could not download {url}") from last_error


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ArchiveImportError(f"Expected a JSON object in {path}")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=False)
        file.write("\n")

    temporary_path.replace(path)


def season_from_payload(payload: dict[str, Any]) -> int | None:
    table = payload.get("MRData", {}).get("RaceTable", {})
    value = table.get("season")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def rounds_from_schedule(payload: dict[str, Any], expected_season: int) -> list[int]:
    table = payload.get("MRData", {}).get("RaceTable", {})
    payload_season = table.get("season")
    if str(payload_season) != str(expected_season):
        raise ArchiveImportError(
            f"Schedule payload season {payload_season!r} did not match {expected_season}"
        )

    races = table.get("Races", [])
    if not isinstance(races, list) or not races:
        raise ArchiveImportError(f"No races found in the {expected_season} schedule")

    rounds: list[int] = []
    for race in races:
        try:
            round_number = int(race["round"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ArchiveImportError(
                f"Invalid round in the {expected_season} schedule"
            ) from exc
        rounds.append(round_number)

    if len(rounds) != len(set(rounds)):
        raise ArchiveImportError(f"Duplicate rounds found in the {expected_season} schedule")

    return sorted(rounds)


def validate_race_payload(
    payload: dict[str, Any],
    expected_season: int,
    expected_round: int,
    *,
    require_results: bool,
) -> None:
    table = payload.get("MRData", {}).get("RaceTable", {})
    if str(table.get("season")) != str(expected_season):
        raise ArchiveImportError(
            f"Race payload did not match season {expected_season}"
        )
    if str(table.get("round")) != str(expected_round):
        raise ArchiveImportError(
            f"Race payload did not match round {expected_round}"
        )

    races = table.get("Races", [])
    if not isinstance(races, list) or not races:
        raise ArchiveImportError(
            f"No race data returned for {expected_season} round {expected_round}"
        )

    if require_results and not races[0].get("Results"):
        raise ArchiveImportError(
            f"No results returned for {expected_season} round {expected_round}"
        )


def validate_standings_payload(
    payload: dict[str, Any],
    expected_season: int,
    expected_round: int | None = None,
) -> None:
    table = payload.get("MRData", {}).get("StandingsTable", {})
    if str(table.get("season")) != str(expected_season):
        raise ArchiveImportError(
            f"Standings payload did not match season {expected_season}"
        )
    if expected_round is not None and str(table.get("round")) != str(expected_round):
        raise ArchiveImportError(
            f"Standings payload did not match round {expected_round}"
        )


def load_or_download(
    client: JolpicaClient,
    path: str,
    destination: Path,
    *,
    force: bool,
) -> dict[str, Any]:
    if destination.is_file() and not force:
        logger.info("Using existing %s", destination.relative_to(PROJECT_ROOT))
        return read_json(destination)

    payload = client.get_json(path)
    write_json_atomic(destination, payload)
    logger.info("Saved %s", destination.relative_to(PROJECT_ROOT))
    return payload


def import_season(season: int, settings: DownloadSettings) -> Path:
    season_root = SEASONS_ROOT / str(season)
    races_root = season_root / "races"
    client = JolpicaClient(settings)

    started_at = utc_now_iso()
    try:
        schedule = load_or_download(
            client,
            f"{season}.json?limit=100",
            season_root / "schedule.json",
            force=settings.force,
        )
        rounds = rounds_from_schedule(schedule, season)

        driver_standings = load_or_download(
            client,
            f"{season}/driverstandings.json?limit=100",
            season_root / "driver_standings.json",
            force=settings.force,
        )
        validate_standings_payload(driver_standings, season)

        constructor_standings_downloaded = False
        constructor_path = season_root / "constructor_standings.json"
        if season >= 1958:
            constructor_standings = load_or_download(
                client,
                f"{season}/constructorstandings.json?limit=100",
                constructor_path,
                force=settings.force,
            )
            validate_standings_payload(constructor_standings, season)
            constructor_standings_downloaded = True

        for index, round_number in enumerate(rounds, start=1):
            logger.info(
                "Downloading race %s/%s: %s round %s",
                index,
                len(rounds),
                season,
                round_number,
            )
            round_root = races_root / f"{round_number:02d}"

            results = load_or_download(
                client,
                f"{season}/{round_number}/results.json?limit=100",
                round_root / "results.json",
                force=settings.force,
            )
            validate_race_payload(
                results,
                season,
                round_number,
                require_results=True,
            )

            standings = load_or_download(
                client,
                f"{season}/{round_number}/driverstandings.json?limit=100",
                round_root / "driver_standings.json",
                force=settings.force,
            )
            validate_standings_payload(standings, season, round_number)

        manifest = {
            "schema_version": 1,
            "season": season,
            "source": "Jolpica-F1",
            "source_base_url": settings.api_base,
            "licence": "CC BY-NC-SA 4.0",
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "race_count": len(rounds),
            "rounds": rounds,
            "datasets": {
                "schedule": True,
                "driver_standings": True,
                "constructor_standings": constructor_standings_downloaded,
                "race_results": len(rounds),
                "round_driver_standings": len(rounds),
            },
        }
        manifest_path = season_root / "manifest.json"
        write_json_atomic(manifest_path, manifest)
        logger.info("Season %s archive complete", season)
        return manifest_path
    finally:
        client.close()


def iter_complete_season_roots() -> Iterable[Path]:
    if not SEASONS_ROOT.exists():
        return []
    return sorted(
        (
            path
            for path in SEASONS_ROOT.iterdir()
            if path.is_dir() and (path / "manifest.json").is_file()
        ),
        key=lambda path: int(path.name),
    )


def _driver_name(driver: dict[str, Any]) -> str:
    return f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip()


def build_archive_index() -> dict[str, Any]:
    """Rebuild the cross-season homepage/filter index from local snapshots."""
    seasons: list[int] = []
    drivers: dict[str, dict[str, Any]] = {}
    constructors: dict[str, dict[str, Any]] = {}
    driver_constructor_seasons: dict[str, dict[str, set[int]]] = {}
    driver_season_results: dict[str, dict[str, dict[str, Any]]] = {}

    for season_root in iter_complete_season_roots():
        manifest = read_json(season_root / "manifest.json")
        season = int(manifest["season"])
        seasons.append(season)

        final_standings = read_json(season_root / "driver_standings.json")
        standings_lists = (
            final_standings.get("MRData", {})
            .get("StandingsTable", {})
            .get("StandingsLists", [])
        )
        final_rows = standings_lists[0].get("DriverStandings", []) if standings_lists else []

        for row in final_rows:
            driver = row.get("Driver", {})
            driver_id = driver.get("driverId")
            if not driver_id:
                continue

            constructors_for_row = row.get("Constructors", [])
            constructor_names = [
                item.get("name", "") for item in constructors_for_row if item.get("name")
            ]
            driver_season_results.setdefault(driver_id, {})[str(season)] = {
                "position": row.get("position"),
                "position_text": row.get("positionText", "—"),
                "points": row.get("points", "0"),
                "wins": row.get("wins", "0"),
                "constructors": constructor_names,
            }

        races_root = season_root / "races"
        for results_path in sorted(races_root.glob("*/results.json")):
            payload = read_json(results_path)
            races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
            if not races:
                continue

            for result in races[0].get("Results", []):
                driver = result.get("Driver", {})
                constructor = result.get("Constructor", {})
                driver_id = driver.get("driverId")
                constructor_id = constructor.get("constructorId")
                if not driver_id or not constructor_id:
                    continue

                driver_entry = drivers.setdefault(
                    driver_id,
                    {
                        "id": driver_id,
                        "name": _driver_name(driver),
                        "given_name": driver.get("givenName", ""),
                        "family_name": driver.get("familyName", ""),
                        "code": driver.get("code", ""),
                        "nationality": driver.get("nationality", ""),
                        "permanent_number": driver.get("permanentNumber", ""),
                        "url": driver.get("url", ""),
                        "seasons": set(),
                        "constructors": set(),
                    },
                )
                driver_entry["seasons"].add(season)
                driver_entry["constructors"].add(constructor_id)

                constructor_entry = constructors.setdefault(
                    constructor_id,
                    {
                        "id": constructor_id,
                        "name": constructor.get("name", ""),
                        "nationality": constructor.get("nationality", ""),
                        "url": constructor.get("url", ""),
                        "seasons": set(),
                        "drivers": set(),
                    },
                )
                constructor_entry["seasons"].add(season)
                constructor_entry["drivers"].add(driver_id)

                driver_constructor_seasons.setdefault(driver_id, {}).setdefault(
                    constructor_id, set()
                ).add(season)

    serialised_drivers = []
    for entry in drivers.values():
        serialised_drivers.append(
            {
                **entry,
                "seasons": sorted(entry["seasons"], reverse=True),
                "constructors": sorted(entry["constructors"]),
            }
        )

    serialised_constructors = []
    for entry in constructors.values():
        serialised_constructors.append(
            {
                **entry,
                "seasons": sorted(entry["seasons"], reverse=True),
                "drivers": sorted(entry["drivers"]),
            }
        )

    serialised_relationships = {
        driver_id: {
            constructor_id: sorted(years, reverse=True)
            for constructor_id, years in sorted(constructor_map.items())
        }
        for driver_id, constructor_map in sorted(driver_constructor_seasons.items())
    }

    index = {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "source": "Locally archived Jolpica-F1 snapshots",
        "seasons": sorted(seasons, reverse=True),
        "drivers": sorted(serialised_drivers, key=lambda item: item["name"]),
        "constructors": sorted(
            serialised_constructors,
            key=lambda item: item["name"],
        ),
        "driver_constructor_seasons": serialised_relationships,
        "driver_season_results": driver_season_results,
    }
    write_json_atomic(INDEX_PATH, index)
    logger.info(
        "Rebuilt index: %s seasons, %s drivers, %s constructors",
        len(index["seasons"]),
        len(index["drivers"]),
        len(index["constructors"]),
    )
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download and index the exact Jolpica datasets used by F1 Archive "
            "for one completed season."
        )
    )
    parser.add_argument(
        "season",
        nargs="?",
        type=int,
        default=DEFAULT_SEASON,
        help=f"Season to archive (default: {DEFAULT_SEASON})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files that already exist",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Minimum delay between API requests in seconds (default: {DEFAULT_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Read timeout per request in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum attempts per request (default: {DEFAULT_MAX_RETRIES})",
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help="Override the Jolpica API base URL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.season < 1950:
        raise SystemExit("Season must be 1950 or later")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.max_retries <= 0:
        raise SystemExit("--max-retries must be positive")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    settings = DownloadSettings(
        api_base=args.api_base,
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        force=args.force,
    )

    try:
        manifest_path = import_season(args.season, settings)
        index = build_archive_index()
    except (ArchiveImportError, requests.RequestException, OSError, ValueError) as exc:
        logger.exception("Season import failed: %s", exc)
        return 1

    relative_manifest = manifest_path.relative_to(PROJECT_ROOT)
    relative_index = INDEX_PATH.relative_to(PROJECT_ROOT)
    print()
    print(f"Archived season {args.season}: {relative_manifest}")
    print(f"Updated archive index: {relative_index}")
    print(f"Indexed seasons: {', '.join(map(str, index['seasons']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
