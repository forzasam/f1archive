from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.live_archive import current_season, refresh_live_archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the persistent live archive for the current F1 season."
    )
    parser.add_argument("season", nargs="?", type=int, default=current_season())
    parser.add_argument(
        "--api-base",
        default=os.environ.get(
            "JOLPICA_API_BASE",
            "https://api.jolpi.ca/ergast/f1",
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "20")),
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args()
    metadata = refresh_live_archive(
        args.season,
        api_base=args.api_base,
        timeout_seconds=args.timeout,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
