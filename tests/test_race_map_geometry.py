import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_australia_segments_have_dedicated_svg_paths():
    data = json.loads(
        (ROOT / "data" / "editorial" / "2026-australia.json").read_text(
            encoding="utf-8"
        )
    )
    svg = (ROOT / "templates" / "circuits" / "australia.svg").read_text(
        encoding="utf-8"
    )

    for segment in data["segments"]:
        assert f'data-segment="{segment["id"]}"' in svg


def test_australia_layout_defines_every_marker_position():
    editorial = json.loads(
        (ROOT / "data" / "editorial" / "2026-australia.json").read_text(
            encoding="utf-8"
        )
    )
    layout = json.loads(
        (ROOT / "data" / "circuits" / "australia.json").read_text(
            encoding="utf-8"
        )
    )
    assert {segment["id"] for segment in editorial["segments"]} <= set(
        layout["marker_positions"]
    )


def test_pit_entry_is_authored_at_turn_13():
    svg = (ROOT / "templates" / "circuits" / "australia.svg").read_text(
        encoding="utf-8"
    )
    assert 'data-segment="pit-entry"' in svg
    assert 'd="M798 430 C820 437 840 448 859 458"' in svg
