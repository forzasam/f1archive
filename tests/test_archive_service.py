from unittest.mock import patch

from services.archive_service import get_filtered_seasons


def test_combined_filters_use_driver_constructor_relationship():
    response = {
        "MRData": {
            "SeasonTable": {
                "Seasons": [
                    {"season": "2013"},
                    {"season": "2014"},
                ]
            }
        }
    }

    with patch(
        "services.archive_service.get_json",
        return_value=response,
    ) as mocked_get:
        seasons = get_filtered_seasons("raikkonen", "ferrari")

    mocked_get.assert_called_once_with(
        "drivers/raikkonen/constructors/ferrari/seasons.json?limit=100"
    )
    assert seasons == [2014, 2013]


def test_impossible_pair_returns_no_seasons():
    response = {
        "MRData": {
            "SeasonTable": {
                "Seasons": []
            }
        }
    }

    with patch(
        "services.archive_service.get_json",
        return_value=response,
    ):
        assert get_filtered_seasons("hamilton", "ferrari") == []
