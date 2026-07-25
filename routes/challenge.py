from __future__ import annotations

from datetime import date

from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeSerializer

from services.archive_challenge import (
    build_challenge_pool,
    choose_daily_question,
    choose_endless_question,
    driver_options,
    evaluate_guess,
    public_question,
    season_options,
)


challenge_bp = Blueprint("challenge", __name__)


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(
        current_app.config["SECRET_KEY"],
        salt="f1-archive-challenge-v1",
    )


def _sign_question(question_id: str, mode: str) -> str:
    return _serializer().dumps({"question_id": question_id, "mode": mode})


def _resolve_question(token: str) -> tuple[dict, str]:
    try:
        payload = _serializer().loads(token)
    except BadSignature as exc:
        raise ValueError("Invalid challenge token") from exc

    question_id = payload.get("question_id")
    mode = payload.get("mode", "endless")
    question = next(
        (item for item in build_challenge_pool() if item["id"] == question_id),
        None,
    )
    if not question:
        raise ValueError("Challenge question no longer exists")
    return question, mode


@challenge_bp.get("/archive-challenge")
def challenge_page():
    return render_template(
        "challenge.html",
        driver_options=driver_options(),
        season_options=season_options(),
        daily_key=date.today().isoformat(),
    )


@challenge_bp.get("/api/archive-challenge/question")
def challenge_question():
    mode = request.args.get("mode", "endless")
    if mode == "daily":
        question = choose_daily_question()
    else:
        try:
            streak = max(0, int(request.args.get("streak", 0)))
        except ValueError:
            streak = 0
        excluded_ids = {
            item for item in request.args.get("exclude", "").split(",") if item
        }
        question = choose_endless_question(streak, excluded_ids)
        mode = "endless"

    token = _sign_question(question["id"], mode)
    payload = public_question(question, token, mode)
    payload["question_id"] = question["id"]
    response = jsonify(payload)
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@challenge_bp.post("/api/archive-challenge/hint")
def challenge_hint():
    body = request.get_json(silent=True) or {}
    try:
        question, _ = _resolve_question(str(body.get("token", "")))
        index = int(body.get("index", 0))
        hint = question["hints"][index]
    except (ValueError, IndexError):
        return jsonify({"error": "That hint could not be loaded."}), 400
    return jsonify({"hint": hint})


@challenge_bp.post("/api/archive-challenge/guess")
def challenge_guess():
    body = request.get_json(silent=True) or {}
    try:
        question, mode = _resolve_question(str(body.get("token", "")))
    except ValueError:
        return jsonify({"error": "This challenge has expired. Please load another."}), 400

    correct, driver_correct, season_correct = evaluate_guess(
        question,
        str(body.get("driver", "")),
        body.get("season"),
    )
    try:
        hints_used = max(0, min(4, int(body.get("hints_used", 0))))
    except (TypeError, ValueError):
        hints_used = 0
    points = max(1, 5 - hints_used) if correct else 0

    return jsonify({
        "correct": correct,
        "driver_correct": driver_correct,
        "season_correct": season_correct,
        "points": points,
        "mode": mode,
        "answer": {
            "driver": question["driver_name"],
            "season": question["season"],
            "constructors": question["constructors"],
            "final_position": question["final_position"],
            "wins": question["wins"],
            "podiums": question["podiums"],
            "starts": question["starts"],
            "points": question["points"],
            "season_url": url_for(
                "seasons.season_page",
                season=question["season"],
            ),
        },
    })
