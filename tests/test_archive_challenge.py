from services.archive_challenge import (
    build_challenge_pool,
    choose_daily_question,
    evaluate_guess,
)


def test_challenge_pool_uses_modern_and_notable_historic_seasons():
    pool = build_challenge_pool()
    assert pool
    assert any(item["season"] >= 2000 for item in pool)
    assert all(
        item["season"] >= 2000 or item["wins"] >= 1 or item["final_position"] <= 3
        for item in pool
    )


def test_daily_question_is_deterministic():
    first = choose_daily_question()
    second = choose_daily_question()
    assert first["id"] == second["id"]


def test_guess_requires_driver_and_season():
    question = build_challenge_pool()[0]
    correct, driver_correct, season_correct = evaluate_guess(
        question,
        question["driver_name"],
        question["season"],
    )
    assert correct and driver_correct and season_correct
    correct, driver_correct, season_correct = evaluate_guess(
        question,
        question["driver_name"],
        question["season"] + 1,
    )
    assert not correct and driver_correct and not season_correct
