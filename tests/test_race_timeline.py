import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_australia_timeline_has_explicit_race_distance():
    data = json.loads(
        (ROOT / "data" / "editorial" / "2026-australia.json").read_text(
            encoding="utf-8"
        )
    )

    assert data["race"]["laps"] == 58


def test_timeline_events_have_ids_laps_and_valid_segments():
    data = json.loads(
        (ROOT / "data" / "editorial" / "2026-australia.json").read_text(
            encoding="utf-8"
        )
    )
    segment_ids = {segment["id"] for segment in data["segments"]}
    event_ids = set()

    for event in data["events"]:
        assert event["id"] not in event_ids
        assert 1 <= event["lap"] <= data["race"]["laps"]
        assert event["segment_id"] in segment_ids
        assert event["type_label"]
        event_ids.add(event["id"])


def test_timeline_interface_is_present():
    template = (
        ROOT / "templates" / "_race_map.html"
    ).read_text(encoding="utf-8")
    script = (
        ROOT / "static" / "race_map.js"
    ).read_text(encoding="utf-8")

    assert 'id="timeline-rail"' in template
    assert 'id="timeline-list"' in template
    assert "selectEvent(event.id)" in script


def test_editorial_story_playback_interface_is_present():
    template = (ROOT / "templates" / "_race_map.html").read_text(encoding="utf-8")
    script = (ROOT / "static" / "race_map.js").read_text(encoding="utf-8")

    assert 'id="story-event-overlay"' in template
    assert 'id="story-continue"' in template
    assert "function playStoryFrames(event)" in script
    assert "storyPausedAtEvent" in script
    assert "event.frames" in script
    assert "editorial reconstructions" in template
