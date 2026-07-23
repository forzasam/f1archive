from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CIRCUIT_DIRECTORY = PROJECT_ROOT / "data" / "circuits"
SVG_DIRECTORY = PROJECT_ROOT / "templates" / "circuits"


def _slug_for_circuit_id(circuit_id: str) -> str | None:
    """Resolve archive circuit IDs from the locally authored packages.

    The optional ``circuit_ids`` array in each circuit JSON lets a new package
    advertise which Jolpica/archive IDs it supports without editing Python.
    """
    import json

    for path in CIRCUIT_DIRECTORY.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as file:
                package = json.load(file)
        except (OSError, ValueError):
            continue

        if circuit_id in package.get("circuit_ids", []):
            return path.stem

    return None


def get_current_circuit_geometry(circuit_id: str) -> dict | None:
    """Return metadata only for a locally authored circuit package."""
    slug = _slug_for_circuit_id(circuit_id)
    if not slug:
        return None

    return {
        "layout_id": slug,
        "display_name": slug.replace("-", " ").title(),
        "svg_template": f"circuits/{slug}.svg",
        "source_name": "Local authored circuit package",
        "interactive": True,
        "segments_authored": True,
    }


def get_inline_circuit_geometry(layout_id: str) -> dict | None:
    """Legacy compatibility wrapper for callers using the old service API."""
    json_path = CIRCUIT_DIRECTORY / f"{layout_id}.json"
    svg_path = SVG_DIRECTORY / f"{layout_id}.svg"
    if not json_path.is_file() or not svg_path.is_file():
        return None

    return {
        "layout_id": layout_id,
        "svg_template": f"circuits/{layout_id}.svg",
        "interactive": True,
        "segments_authored": True,
    }
