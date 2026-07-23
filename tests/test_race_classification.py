from services.archive_service import format_result_time, is_classified_result


def test_numeric_positions_are_classified():
    assert is_classified_result("7", "+1 Lap")
    assert is_classified_result("16", "+2 Laps")


def test_finishing_status_recovers_bad_position_marker():
    # Some provisional feeds have supplied a retirement-style positionText
    # despite the driver being officially classified at a lap deficit.
    assert is_classified_result("R", "+1 Lap")
    assert is_classified_result("R", "+2 Laps")
    assert is_classified_result("R", "Finished")
    assert is_classified_result("R", "Lapped")


def test_retired_and_non_starting_drivers_are_non_finishers():
    assert not is_classified_result("R", "Accident")
    assert not is_classified_result("W", "Withdrew")
    assert not is_classified_result("D", "Disqualified")
    assert not is_classified_result("E", "Excluded")
    assert not is_classified_result("", "Engine")


def test_lap_deficit_takes_precedence_over_residual_time_delta():
    assert format_result_time("+4.218", "+1 Lap") == "1L"
    assert format_result_time("+2.011", "+2 Laps") == "2L"
    assert format_result_time("+4.218", "Lapped", 1) == "1L"
    assert format_result_time("+4.218", "Lapped", 3) == "3L"
    assert format_result_time("+4.218", "Finished", 2) == "2L"


def test_normal_finishers_keep_their_time_delta():
    assert format_result_time("+55.103", "Finished") == "+55.103"
    assert format_result_time("1:31:42.117", "Finished") == "1:31:42.117"


def test_status_is_fallback_when_no_time_exists():
    assert format_result_time(None, "Collision") == "Collision"
