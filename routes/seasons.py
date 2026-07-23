from flask import Blueprint, abort, render_template

from services.archive_service import get_season_page

seasons_bp = Blueprint("seasons", __name__, url_prefix="/season")


@seasons_bp.route("/<int:season>")
def season_page(season: int):
    page_data = get_season_page(season)
    if not page_data["races"]:
        abort(404)

    return render_template("season.html", **page_data)
