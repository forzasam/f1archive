from services.race_story_map import get_race_story_map
from services.circuit_service import get_current_circuit_geometry


def test_abu_dhabi_2021_story_is_separate_from_circuit_geometry():
    story = get_race_story_map(2021, 22)
    circuit = get_current_circuit_geometry("yas_marina", season=2021)
    assert story is not None
    assert circuit is not None
    assert len(story["events"]) == 8
    segment_ids = {segment["id"] for segment in circuit["segments"]}
    for event in story["events"]:
        assert 0 <= event["position"] <= 1
        assert set(event.get("segments", [])) <= segment_ids


def test_other_abu_dhabi_races_do_not_inherit_2021_story():
    assert get_race_story_map(2022, 22) is None
