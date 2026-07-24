from types import SimpleNamespace
from unittest.mock import patch

from services.archive_service import get_filtered_seasons


def _index(**overrides):
    values = {
        "seasons": (2026, 2025, 2024),
        "driver_seasons": {"raikkonen": frozenset({2014, 2013})},
        "constructor_seasons": {"ferrari": frozenset({2014, 2013})},
        "relationship_seasons": {
            ("raikkonen", "ferrari"): frozenset({2014, 2013}),
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_combined_filters_use_local_driver_constructor_relationship():
    with patch(
        "services.archive_service.get_archive_index",
        return_value=_index(),
    ):
        seasons = get_filtered_seasons("raikkonen", "ferrari")

    assert seasons == [2014, 2013]


def test_impossible_pair_returns_no_seasons():
    with patch(
        "services.archive_service.get_archive_index",
        return_value=_index(),
    ):
        assert get_filtered_seasons("hamilton", "ferrari") == []


def test_unfiltered_seasons_come_from_local_index():
    with patch(
        "services.archive_service.get_archive_index",
        return_value=_index(),
    ):
        assert get_filtered_seasons() == [2026, 2025, 2024]
