import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITORIAL = ROOT / "data" / "editorial"

def test_all_completed_2026_rounds_have_maps():
    files = sorted(EDITORIAL.glob("2026-*.json"))
    rounds = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        rounds.add(data["race"]["round"])
    assert rounds == set(range(1, 11))

def test_svg_maps_have_valid_segment_event_links():
    for path in EDITORIAL.glob("2026-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = {s["id"] for s in data["segments"]}
        for event in data["events"]:
            assert event["segment_id"] in ids
            assert 1 <= int(event["lap"]) <= data["race"]["laps"]
            assert event["title"]
