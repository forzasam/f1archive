import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


class Config:
    JOLPICA_API_BASE = os.environ.get(
        "JOLPICA_API_BASE",
        "https://api.jolpi.ca/ergast/f1",
    )
    REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "20"))
    LIVE_ARCHIVE_TTL_SECONDS = int(os.environ.get("LIVE_ARCHIVE_TTL_SECONDS", "3600"))
    LIVE_ARCHIVE_CHECK_INTERVAL_SECONDS = int(
        os.environ.get("LIVE_ARCHIVE_CHECK_INTERVAL_SECONDS", "300")
    )
    LIVE_ARCHIVE_BACKGROUND_REFRESH = _env_bool(
        "LIVE_ARCHIVE_BACKGROUND_REFRESH",
        True,
    )
