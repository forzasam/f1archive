from datetime import date

from services.archive_challenge import (
    RECENT_START_YEAR,
    _difficulty_tier,
    _tiers_for_streak,
    choose_daily_question,
)


def test_tier_one_is_recent_and_prominent():
    assert _difficulty_tier(
        season=RECENT_START_YEAR,
        final_position=1,
        wins=8,
        starts=20,
        season_rounds=20,
    ) == 1

    assert _difficulty_tier(
        season=2004,
        final_position=1,
        wins=13,
        starts=18,
        season_rounds=18,
    ) == 2

    assert _difficulty_tier(
        season=1969,
        final_position=1,
        wins=6,
        starts=11,
        season_rounds=11,
    ) == 3


def test_endless_mode_stays_easy_for_longer():
    assert _tiers_for_streak(0) == (1,)
    assert _tiers_for_streak(4) == (1,)
    assert _tiers_for_streak(8) == (1, 2)
    assert _tiers_for_streak(15) == (2,)
    assert _tiers_for_streak(31) == (3, 4)


def test_daily_never_uses_the_hardest_tiers():
    for day in range(1, 29):
        question = choose_daily_question(date(2026, 7, day))
        assert question["tier"] <= 3
