import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITORIAL = ROOT / "data" / "editorial"


def test_only_australia_editorial_map_is_retained():
    files = sorted(path.name for path in EDITORIAL.glob("2026-*.json"))
    assert files == ["2026-australia.json"]


def test_australia_events_have_valid_segment_links():
    data = json.loads(
        (EDITORIAL / "2026-australia.json").read_text(encoding="utf-8")
    )
    ids = {segment["id"] for segment in data["segments"]}
    for event in data["events"]:
        assert event["segment_id"] in ids
        assert 1 <= int(event["lap"]) <= data["race"]["laps"]
        assert event["title"]
