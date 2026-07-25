from unittest.mock import patch

from services.archive_service import get_race_page


def _schedule_payload(season=2099, round_number=7):
    return {
        "MRData": {
            "RaceTable": {
                "season": str(season),
                "Races": [
                    {
                        "season": str(season),
                        "round": str(round_number),
                        "raceName": "Example Grand Prix",
                        "date": "2099-07-26",
                        "time": "13:00:00Z",
                        "Circuit": {
                            "circuitId": "example",
                            "circuitName": "Example Circuit",
                            "Location": {
                                "locality": "Example City",
                                "country": "Example Country",
                            },
                        },
                    }
                ],
            }
        }
    }


def _empty_results_payload(season=2099, round_number=7):
    return {
        "MRData": {
            "RaceTable": {
                "season": str(season),
                "round": str(round_number),
                "Races": [],
            }
        }
    }


def test_scheduled_current_round_returns_upcoming_page_data():
    def fake_get_json(path):
        if "results.json" in path:
            return _empty_results_payload()
        return _schedule_payload()

    with (
        patch("services.archive_service.get_json", side_effect=fake_get_json),
        patch("services.archive_service.live_current_season", return_value=2099),
        patch("services.archive_service.get_live_archive_metadata", return_value=None),
    ):
        race = get_race_page(2099, 7)

    assert race["is_upcoming"] is True
    assert race["is_future"] is True
    assert race["name"] == "Example Grand Prix"
    assert race["scheduled_display"] == "26 July 2099 at 14:00 BST"
    assert race["circuit"] == "Example Circuit"
