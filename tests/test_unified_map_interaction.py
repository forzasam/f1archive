from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_both_map_templates_have_playback_controls():
    for filename in ("_race_map.html", "_race_map_svg.html"):
        content = (ROOT / "templates" / filename).read_text(encoding="utf-8")
        assert 'id="timeline-play"' in content
        assert 'id="timeline-current-lap"' in content
        assert 'id="timeline-speed"' in content

def test_generic_map_has_hover_labels_and_animation():
    content = (ROOT / "static" / "race_map_svg.js").read_text(encoding="utf-8")
    assert "segmentLabels" in content
    assert "showTooltip" in content
    assert "setBaseOpacity" in content
    assert "advanceLap" in content
    assert "repeatCount" in content

def test_australia_has_timeline_animation():
    content = (ROOT / "static" / "race_map.js").read_text(encoding="utf-8")
    assert "authoredAdvance" in content
    assert "map-marker-pulse" in content
