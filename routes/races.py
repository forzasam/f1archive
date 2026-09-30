from flask import Blueprint, render_template

from services.archive_service import get_race_page, get_season_page
from services.race_service import get_curated_race_events
from services.race_story_map import get_race_story_map
from routes.seasons import season_sequence, neighbours

races_bp = Blueprint("races", __name__, url_prefix="/season")


@races_bp.route("/<int:season>/race/<int:round_number>")
def race_page(season: int, round_number: int):
    race = get_race_page(season, round_number)
    page_data = get_season_page(season)
    sequence_nav = neighbours(season_sequence(season, page_data), "race", round_number)
    if race.get("is_upcoming"):
        return render_template("upcoming_race.html", race=race, sequence_nav=sequence_nav)

    race_map = get_curated_race_events(season, round_number)
    race_story_map = get_race_story_map(season, round_number)
    return render_template(
        "race.html", race=race, race_map=race_map,
        race_story_map=race_story_map, sequence_nav=sequence_nav,
    )
