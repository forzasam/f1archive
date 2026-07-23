from unittest.mock import patch

from services.archive_service import get_race_championship_progression


def standings_payload(round_number):
    points = {
        1: [25, 18, 15],
        2: [43, 40, 27],
    }[round_number]

    drivers = [
        ("driver_a", "Alice", "Alpha", "AAA"),
        ("driver_b", "Ben", "Beta", "BBB"),
        ("driver_c", "Cara", "Gamma", "CCC"),
    ]

    rows = []
    for position, ((driver_id, given, family, code), score) in enumerate(
        zip(drivers, points),
        start=1,
    ):
        rows.append({
            "position": str(position),
            "positionText": str(position),
            "points": str(score),
            "wins": "0",
            "Driver": {
                "driverId": driver_id,
                "givenName": given,
                "familyName": family,
                "code": code,
            },
            "Constructors": [{
                "constructorId": "test_team",
                "name": "Test Team",
            }],
        })

    return {
        "MRData": {
            "StandingsTable": {
                "StandingsLists": [{
                    "DriverStandings": rows,
                }]
            }
        }
    }


def test_round_two_compares_with_round_one():
    def fake_get_json(path):
        round_number = int(path.split("/")[1])
        return standings_payload(round_number)

    with patch(
        "services.archive_service.get_json",
        side_effect=fake_get_json,
    ):
        result = get_race_championship_progression(2026, 2)

    assert len(result["before"]) == 3
    assert result["after"][0]["points_before"] == 25
    assert result["after"][0]["points_gained"] == 18


def test_season_opener_has_no_invented_pre_race_order():
    with patch(
        "services.archive_service.get_json",
        return_value=standings_payload(1),
    ) as mocked_get:
        result = get_race_championship_progression(2026, 1)

    assert result["before"] == []
    assert result["is_season_opener"] is True
    mocked_get.assert_called_once_with(
        "2026/1/driverstandings.json?limit=100"
    )
