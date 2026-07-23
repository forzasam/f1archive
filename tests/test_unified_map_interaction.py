from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_map_template_has_playback_controls():
    content = (ROOT / "templates" / "_race_map.html").read_text(
        encoding="utf-8"
    )
    assert 'id="timeline-play"' in content
    assert 'id="timeline-current-lap"' in content
    assert 'id="timeline-speed"' in content


def test_shared_renderer_contains_no_circuit_geometry():
    template = (ROOT / "templates" / "_race_map.html").read_text(
        encoding="utf-8"
    )
    javascript = (ROOT / "static" / "race_map.js").read_text(
        encoding="utf-8"
    )
    assert "M790 492" not in template
    assert "pit-entry\": [" not in javascript
    assert "mapData.marker_positions" in javascript


def test_australia_has_timeline_animation():
    content = (ROOT / "static" / "race_map.js").read_text(encoding="utf-8")
    assert "authoredAdvance" in content
    assert "map-marker-pulse" in content
