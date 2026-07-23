import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_australia_segments_have_svg_paths():
    data = json.loads(
        (ROOT / "data" / "editorial" / "2026-australia.json").read_text(
            encoding="utf-8"
        )
    )
    template = (ROOT / "templates" / "_race_map.html").read_text(
        encoding="utf-8"
    )

    for segment in data["segments"]:
        assert f'data-segment="{segment["id"]}"' in template


def test_all_events_reference_known_segments():
    data = json.loads(
        (ROOT / "data" / "editorial" / "2026-australia.json").read_text(
            encoding="utf-8"
        )
    )
    segment_ids = {segment["id"] for segment in data["segments"]}

    assert all(
        event["segment_id"] in segment_ids
        for event in data["events"]
    )
