from unittest.mock import patch

from services.archive_service import (
    get_driver_positions_by_season,
    get_season_driver_standings,
)


def test_driver_standings_are_parsed_with_team_colour():
    response = {
        "MRData": {
            "StandingsTable": {
                "StandingsLists": [{
                    "DriverStandings": [{
                        "position": "1",
                        "positionText": "1",
                        "points": "98",
                        "wins": "5",
                        "Driver": {
                            "driverId": "hamilton",
                            "givenName": "Lewis",
                            "familyName": "Hamilton",
                            "code": "HAM",
                        },
                        "Constructors": [{
                            "constructorId": "mclaren",
                            "name": "McLaren",
                        }],
                    }]
                }]
            }
        }
    }

    with patch("services.archive_service.get_json", return_value=response):
        result = get_season_driver_standings(2008)

    assert result[0]["driver_name"] == "Lewis Hamilton"
    assert result[0]["constructor_name"] == "McLaren"
    assert result[0]["team_colour"] == "#ff8700"


def test_driver_position_lookup_is_keyed_by_season():
    response = {
        "MRData": {
            "StandingsTable": {
                "StandingsLists": [{
                    "DriverStandings": [{
                        "position": "2",
                        "positionText": "2",
                        "points": "240",
                        "wins": "3",
                        "Constructors": [{
                            "constructorId": "mercedes",
                            "name": "Mercedes",
                        }],
                    }]
                }]
            }
        }
    }

    with patch("services.archive_service.get_json", return_value=response):
        result = get_driver_positions_by_season("hamilton", [2021])

    assert result[2021]["position"] == 2
    assert result[2021]["constructors"] == ["Mercedes"]
