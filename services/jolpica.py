from __future__ import annotations

from functools import lru_cache
from typing import Any

import requests
from flask import current_app

from services.errors import F1DataError
from services.live_archive import (
    ensure_live_archive_current,
    live_path_for_api_request,
    read_json as read_live_json,
)
from services.local_archive import archived_path_for_api_request, read_archive_json


@lru_cache(maxsize=512)
def _cached_request(url: str, timeout: int) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise F1DataError(f"Could not load Formula 1 data from {url}") from exc


def get_json(path: str) -> dict[str, Any]:
    archived_path = archived_path_for_api_request(path)
    if archived_path is not None:
        return read_archive_json(archived_path)

    live_mapping = live_path_for_api_request(path)
    if live_mapping is not None:
        season, live_path = live_mapping
        ensure_live_archive_current(
            season,
            ttl_seconds=current_app.config["LIVE_ARCHIVE_TTL_SECONDS"],
            api_base=current_app.config["JOLPICA_API_BASE"],
            timeout_seconds=current_app.config["REQUEST_TIMEOUT_SECONDS"],
        )
        if live_path.is_file():
            return read_live_json(live_path)

        # Future rounds do not have result or post-race standings files yet.
        # Preserve Jolpica's empty-response shape so race routes return 404
        # rather than turning an expected absence into a 503.
        clean_path = path.split("?", 1)[0].strip("/")
        if clean_path.endswith("/results.json"):
            season_text, round_text, _ = clean_path.split("/", 2)
            return {
                "MRData": {
                    "RaceTable": {
                        "season": season_text,
                        "round": round_text,
                        "Races": [],
                    }
                }
            }
        if clean_path.endswith("/driverstandings.json") and clean_path.count("/") == 2:
            season_text, round_text, _ = clean_path.split("/", 2)
            return {
                "MRData": {
                    "StandingsTable": {
                        "season": season_text,
                        "round": round_text,
                        "StandingsLists": [],
                    }
                }
            }
        return read_live_json(live_path)

    base = current_app.config["JOLPICA_API_BASE"].rstrip("/")
    timeout = current_app.config["REQUEST_TIMEOUT_SECONDS"]
    url = f"{base}/{path.lstrip('/')}"
    return _cached_request(url, timeout)
