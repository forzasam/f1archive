def is_classified(position_text: str) -> bool:
    return str(position_text).strip().isdigit()


def test_lapped_classified_drivers_are_finishers():
    # Status may be "+1 Lap", but the numeric classification is decisive.
    assert is_classified("7")
    assert is_classified("16")


def test_retired_and_non_starting_drivers_are_non_finishers():
    assert not is_classified("R")
    assert not is_classified("W")
    assert not is_classified("D")
    assert not is_classified("E")
    assert not is_classified("")


def test_australia_summary_counts():
    positions = [
        *[str(position) for position in range(1, 17)],
        "R", "R", "R", "R", "W", "W",
    ]

    finishers = [value for value in positions if is_classified(value)]
    non_finishers = [value for value in positions if not is_classified(value)]

    assert len(finishers) == 16
    assert len(non_finishers) == 6
