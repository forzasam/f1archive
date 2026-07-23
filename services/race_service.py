from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EDITORIAL_DIRECTORY = PROJECT_ROOT / "data" / "editorial"
CIRCUIT_DIRECTORY = PROJECT_ROOT / "data" / "circuits"
SVG_DIRECTORY = PROJECT_ROOT / "templates" / "circuits"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _find_editorial_file(season: int, round_number: int) -> Path | None:
    """Find the race editorial file by its own season/round metadata.

    This removes the old per-round Python registry. A newly prepared
    ``<season>-<slug>.json`` file is discovered automatically.
    """
    for path in sorted(EDITORIAL_DIRECTORY.glob(f"{season}-*.json")):
        try:
            race = _read_json(path).get("race", {})
        except (OSError, ValueError):
            continue

        if race.get("season") == season and race.get("round") == round_number:
            return path

    return None


def get_curated_race_events(season: int, round_number: int) -> dict | None:
    """Load one complete local map package from its three authored files.

    Required files for a slug are:
      * ``templates/circuits/<slug>.svg``
      * ``data/circuits/<slug>.json``
      * ``data/editorial/<season>-<slug>.json``
    """
    editorial_path = _find_editorial_file(season, round_number)
    if editorial_path is None:
        return None

    race_map = _read_json(editorial_path)
    slug = race_map.get("race", {}).get("slug")
    if not slug:
        return None

    circuit_path = CIRCUIT_DIRECTORY / f"{slug}.json"
    svg_path = SVG_DIRECTORY / f"{slug}.svg"
    if not circuit_path.is_file() or not svg_path.is_file():
        return None

    circuit_layout = _read_json(circuit_path)
    circuit_layout.setdefault("svg_template", f"circuits/{slug}.svg")
    race_map.update(circuit_layout)
    return race_map
