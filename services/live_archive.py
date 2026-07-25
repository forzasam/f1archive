from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from services.errors import F1DataError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIVE_ROOT = PROJECT_ROOT / "data" / "live"
DEFAULT_API_BASE = "https://api.jolpi.ca/ergast/f1"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def current_season() -> int:
    return utc_now().year


def live_archive_root() -> Path:
    configured = os.environ.get("LIVE_ARCHIVE_ROOT", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_LIVE_ROOT


def live_season_root(season: int) -> Path:
    return live_archive_root() / "seasons" / str(season)


def metadata_path(season: int) -> Path:
    return live_season_root(season) / "metadata.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError as exc:
        raise F1DataError(f"Live archive file is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise F1DataError(f"Live archive file could not be read: {path}") from exc

    if not isinstance(payload, dict):
        raise F1DataError(f"Live archive file is invalid: {path}")
    return payload


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    try:
        return read_json(path)
    except F1DataError:
        return None


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_live_archive_metadata(season: int) -> dict[str, Any] | None:
    return _read_json_if_present(metadata_path(season))


def live_archive_is_stale(season: int, ttl_seconds: int) -> bool:
    metadata = get_live_archive_metadata(season)
    if metadata is None:
        return True
    # Schema 2 introduced reconciliation against Jolpica's latest completed
    # round. Force older snapshots to refresh immediately after deployment.
    if int(metadata.get("schema_version", 0) or 0) < 2:
        return True
    updated_at = _parse_iso_datetime(metadata.get("last_successful_update"))
    if updated_at is None:
        return True
    return utc_now() - updated_at >= timedelta(seconds=max(ttl_seconds, 60))


def _base_metadata(season: int) -> dict[str, Any]:
    existing = get_live_archive_metadata(season) or {}
    return {
        "schema_version": 2,
        "season": season,
        "source": "Jolpica-F1",
        "source_base_url": existing.get("source_base_url", DEFAULT_API_BASE),
        "last_attempt": existing.get("last_attempt"),
        "last_successful_update": existing.get("last_successful_update"),
        "status": existing.get("status", "uninitialised"),
        "consecutive_failures": int(existing.get("consecutive_failures", 0) or 0),
        "last_error": existing.get("last_error"),
        "completed_rounds": list(existing.get("completed_rounds", [])),
        "completed_round_count": int(existing.get("completed_round_count", 0) or 0),
        "scheduled_round_count": int(existing.get("scheduled_round_count", 0) or 0),
        "latest_completed_round": existing.get("latest_completed_round"),
    }


class LiveArchiveClient:
    def __init__(
        self,
        api_base: str,
        timeout_seconds: int,
        max_retries: int = 4,
        delay_seconds: float = 0.35,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "F1Archive/1.0 (https://f1archive.net)",
        })
        self._last_request_at: float | None = None

    def close(self) -> None:
        self.session.close()

    def get_json(self, path: str) -> dict[str, Any]:
        url = f"{self.api_base}/{path.lstrip('/')}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            if self._last_request_at is not None:
                remaining = self.delay_seconds - (time.monotonic() - self._last_request_at)
                if remaining > 0:
                    time.sleep(remaining)
            try:
                response = self.session.get(
                    url,
                    timeout=(10, self.timeout_seconds),
                )
                self._last_request_at = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        wait = float(retry_after) if retry_after else min(2 ** (attempt - 1), 20)
                    except ValueError:
                        wait = min(2 ** (attempt - 1), 20)
                    time.sleep(max(wait, 0) + random.uniform(0, 0.3))
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Jolpica response was not a JSON object")
                return payload
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                self._last_request_at = time.monotonic()
                if attempt < self.max_retries:
                    time.sleep(min(2 ** (attempt - 1), 20) + random.uniform(0, 0.3))

        raise F1DataError(f"Could not refresh live Formula 1 data from {url}") from last_error


def _race_table(payload: dict[str, Any]) -> dict[str, Any]:
    table = payload.get("MRData", {}).get("RaceTable", {})
    return table if isinstance(table, dict) else {}


def _standings_table(payload: dict[str, Any]) -> dict[str, Any]:
    table = payload.get("MRData", {}).get("StandingsTable", {})
    return table if isinstance(table, dict) else {}


def _validate_schedule(payload: dict[str, Any], season: int) -> list[dict[str, Any]]:
    table = _race_table(payload)
    if str(table.get("season")) != str(season):
        raise F1DataError(f"Live schedule did not match season {season}")
    races = table.get("Races", [])
    if not isinstance(races, list):
        raise F1DataError("Live schedule contained invalid race data")
    return races


def _validate_standings(payload: dict[str, Any], season: int, round_number: int | None = None) -> None:
    table = _standings_table(payload)
    if str(table.get("season")) != str(season):
        raise F1DataError(f"Live standings did not match season {season}")
    if round_number is not None and str(table.get("round")) != str(round_number):
        raise F1DataError(f"Live standings did not match round {round_number}")


def _individual_results_payload(
    combined_payload: dict[str, Any],
    season: int,
    race: dict[str, Any],
) -> dict[str, Any]:
    mr_data = dict(combined_payload.get("MRData", {}))
    table = dict(_race_table(combined_payload))
    table["season"] = str(season)
    table["round"] = str(race.get("round", ""))
    table["Races"] = [race]
    mr_data["RaceTable"] = table
    mr_data["count"] = "1"
    mr_data["offset"] = "0"
    return {"MRData": mr_data}


def _completed_races(payload: dict[str, Any], season: int) -> list[dict[str, Any]]:
    table = _race_table(payload)
    if str(table.get("season")) != str(season):
        raise F1DataError(f"Live results did not match season {season}")
    races = table.get("Races", [])
    if not isinstance(races, list):
        raise F1DataError("Live results contained invalid race data")
    return [race for race in races if isinstance(race, dict) and race.get("Results")]


def _acquire_refresh_lock(season: int, stale_after_seconds: int = 900) -> Path | None:
    lock_path = live_season_root(season) / ".refresh.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - lock_path.stat().st_mtime
            if age > stale_after_seconds:
                lock_path.unlink(missing_ok=True)
                descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                return None
        except (FileNotFoundError, FileExistsError, OSError):
            return None
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(f"pid={os.getpid()} started={utc_now_iso()}\n")
    return lock_path


def refresh_live_archive(
    season: int | None = None,
    *,
    api_base: str = DEFAULT_API_BASE,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    season = season or current_season()
    if season != current_season():
        raise F1DataError("The live archive can only refresh the current season")

    lock_path = _acquire_refresh_lock(season)
    if lock_path is None:
        metadata = get_live_archive_metadata(season)
        if metadata:
            return metadata
        raise F1DataError("A live archive refresh is already in progress")

    metadata = _base_metadata(season)
    metadata["last_attempt"] = utc_now_iso()
    metadata["source_base_url"] = api_base
    client = LiveArchiveClient(api_base, timeout_seconds)
    season_root = live_season_root(season)

    try:
        schedule = client.get_json(f"{season}.json?limit=100")
        schedule_rows = _validate_schedule(schedule, season)

        # Use Jolpica's latest completed race as the source of truth for how
        # far the season has progressed. The season-wide results endpoint can
        # occasionally lag behind otherwise-current round endpoints, which
        # previously allowed the cache to report itself as healthy while
        # several completed races were missing.
        latest_results = client.get_json("current/last/results.json")
        latest_completed = _completed_races(latest_results, season)
        latest_round = (
            max(int(race["round"]) for race in latest_completed)
            if latest_completed
            else None
        )

        scheduled_rounds = sorted({
            int(race["round"])
            for race in schedule_rows
            if isinstance(race, dict) and str(race.get("round", "")).isdigit()
        })
        completed_rounds = (
            [round_number for round_number in scheduled_rounds if round_number <= latest_round]
            if latest_round is not None
            else []
        )

        # Pin the season standings to the same latest completed round rather
        # than trusting another aggregate endpoint that may be cached at an
        # older round. Before the first race, the ordinary season endpoints
        # are still used so an empty but valid snapshot can be stored.
        if latest_round is not None:
            driver_standings = client.get_json(
                f"{season}/{latest_round}/driverstandings.json?limit=100"
            )
            _validate_standings(driver_standings, season, latest_round)
            constructor_standings = client.get_json(
                f"{season}/{latest_round}/constructorstandings.json?limit=100"
            )
            _validate_standings(constructor_standings, season, latest_round)
        else:
            driver_standings = client.get_json(
                f"{season}/driverstandings.json?limit=100"
            )
            _validate_standings(driver_standings, season)
            constructor_standings = client.get_json(
                f"{season}/constructorstandings.json?limit=100"
            )
            _validate_standings(constructor_standings, season)

        # Reconcile every completed round against the local cache. Existing
        # historical rounds are reused, while missing rounds and the latest
        # round are fetched individually. Refreshing the latest round allows
        # corrected or initially incomplete classifications to replace the
        # cached copy on the next hourly update.
        race_payloads: dict[int, dict[str, Any]] = {}
        round_standings: dict[int, dict[str, Any]] = {}
        latest_by_round = {
            int(race["round"]): race
            for race in latest_completed
            if str(race.get("round", "")).isdigit()
        }

        for round_number in completed_rounds:
            round_root = season_root / "races" / f"{round_number:02d}"
            results_path = round_root / "results.json"
            standings_path = round_root / "driver_standings.json"

            should_refresh_results = round_number == latest_round or not results_path.is_file()
            if should_refresh_results:
                if round_number in latest_by_round:
                    payload = _individual_results_payload(
                        latest_results,
                        season,
                        latest_by_round[round_number],
                    )
                else:
                    payload = client.get_json(
                        f"{season}/{round_number}/results.json?limit=100"
                    )
                races = _completed_races(payload, season)
                if len(races) != 1 or int(races[0].get("round", -1)) != round_number:
                    raise F1DataError(
                        f"Completed round {round_number} did not return a valid result"
                    )
                race_payloads[round_number] = payload

            if round_number == latest_round:
                round_standings[round_number] = driver_standings
            elif not standings_path.is_file():
                payload = client.get_json(
                    f"{season}/{round_number}/driverstandings.json?limit=100"
                )
                _validate_standings(payload, season, round_number)
                round_standings[round_number] = payload

        write_json_atomic(season_root / "schedule.json", schedule)
        write_json_atomic(season_root / "driver_standings.json", driver_standings)
        write_json_atomic(
            season_root / "constructor_standings.json",
            constructor_standings,
        )

        for round_number in completed_rounds:
            round_root = season_root / "races" / f"{round_number:02d}"
            if round_number in race_payloads:
                write_json_atomic(
                    round_root / "results.json",
                    race_payloads[round_number],
                )
            if round_number in round_standings:
                write_json_atomic(
                    round_root / "driver_standings.json",
                    round_standings[round_number],
                )

        metadata.update({
            "last_successful_update": utc_now_iso(),
            "status": "healthy",
            "consecutive_failures": 0,
            "last_error": None,
            "completed_rounds": completed_rounds,
            "completed_round_count": len(completed_rounds),
            "scheduled_round_count": len(schedule_rows),
            "latest_completed_round": latest_round,
        })
        write_json_atomic(metadata_path(season), metadata)
        # The homepage filter index is built from these local snapshots.
        # Rebuild it after a successful refresh so current-season entrants,
        # teams and standings are immediately reflected without API calls.
        from services.archive_index import clear_archive_index_cache
        clear_archive_index_cache()
        logger.info(
            "Live archive refreshed for %s (%s completed rounds)",
            season,
            len(completed_rounds),
        )
        return metadata
    except Exception as exc:
        metadata.update({
            "status": "stale" if metadata.get("last_successful_update") else "unavailable",
            "consecutive_failures": int(metadata.get("consecutive_failures", 0)) + 1,
            "last_error": f"{type(exc).__name__}: {exc}",
        })
        try:
            write_json_atomic(metadata_path(season), metadata)
        except OSError:
            logger.exception("Could not record live archive refresh failure")
        logger.exception("Live archive refresh failed for %s", season)
        if isinstance(exc, F1DataError):
            raise
        raise F1DataError("Could not refresh the live Formula 1 archive") from exc
    finally:
        client.close()
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove live archive refresh lock: %s", lock_path)


def ensure_live_archive_current(
    season: int,
    *,
    ttl_seconds: int,
    api_base: str,
    timeout_seconds: int,
) -> dict[str, Any] | None:
    if season != current_season():
        return None
    if not live_archive_is_stale(season, ttl_seconds):
        return get_live_archive_metadata(season)

    try:
        return refresh_live_archive(
            season,
            api_base=api_base,
            timeout_seconds=timeout_seconds,
        )
    except F1DataError:
        # A failed refresh must never take the existing live site down. The
        # caller can continue reading the last known-good files.
        if (live_season_root(season) / "schedule.json").is_file():
            logger.warning("Serving stale live archive data for %s", season)
            return get_live_archive_metadata(season)
        raise


def live_path_for_api_request(path: str) -> tuple[int, Path] | None:
    clean_path = urlsplit(path).path.strip("/")

    match = re.fullmatch(r"(?P<season>\d{4})\.json", clean_path)
    if match:
        season = int(match.group("season"))
        if season == current_season():
            return season, live_season_root(season) / "schedule.json"
        return None

    for pattern, filename in (
        (r"(?P<season>\d{4})/driverstandings\.json", "driver_standings.json"),
        (r"(?P<season>\d{4})/constructorstandings\.json", "constructor_standings.json"),
    ):
        match = re.fullmatch(pattern, clean_path)
        if match:
            season = int(match.group("season"))
            if season == current_season():
                return season, live_season_root(season) / filename
            return None

    match = re.fullmatch(
        r"(?P<season>\d{4})/(?P<round>\d+)/(?P<dataset>results|driverstandings)\.json",
        clean_path,
    )
    if not match:
        return None

    season = int(match.group("season"))
    if season != current_season():
        return None
    filename = "results.json" if match.group("dataset") == "results" else "driver_standings.json"
    path = (
        live_season_root(season)
        / "races"
        / f"{int(match.group('round')):02d}"
        / filename
    )
    return season, path


def start_live_archive_scheduler(app: Any) -> None:
    """Start a lightweight in-process stale-cache checker.

    The disk lock makes this safe if Gunicorn starts more than one worker.
    Each process may wake up, but only one can perform a refresh and fresh
    metadata prevents the others from repeating it.
    """
    if not app.config.get("LIVE_ARCHIVE_BACKGROUND_REFRESH", True):
        return

    import threading

    check_interval = max(
        int(app.config.get("LIVE_ARCHIVE_CHECK_INTERVAL_SECONDS", 300)),
        60,
    )

    def run() -> None:
        # Let the web process finish starting before the first network call.
        time.sleep(min(check_interval, 30))
        while True:
            try:
                with app.app_context():
                    season = current_season()
                    if live_archive_is_stale(
                        season,
                        app.config["LIVE_ARCHIVE_TTL_SECONDS"],
                    ):
                        ensure_live_archive_current(
                            season,
                            ttl_seconds=app.config["LIVE_ARCHIVE_TTL_SECONDS"],
                            api_base=app.config["JOLPICA_API_BASE"],
                            timeout_seconds=app.config["REQUEST_TIMEOUT_SECONDS"],
                        )
            except Exception:
                app.logger.exception("Background live archive check failed")
            time.sleep(check_interval)

    thread = threading.Thread(
        target=run,
        name="f1-live-archive-refresh",
        daemon=True,
    )
    thread.start()
