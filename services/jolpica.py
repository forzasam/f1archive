from __future__ import annotations

from functools import lru_cache
from typing import Any

import requests
from flask import current_app

from services.errors import F1DataError


@lru_cache(maxsize=512)
def _cached_request(url: str, timeout: int) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise F1DataError(f"Could not load Formula 1 data from {url}") from exc


def get_json(path: str) -> dict[str, Any]:
    base = current_app.config["JOLPICA_API_BASE"].rstrip("/")
    timeout = current_app.config["REQUEST_TIMEOUT_SECONDS"]
    url = f"{base}/{path.lstrip('/')}"
    return _cached_request(url, timeout)
