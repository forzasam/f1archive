from flask import Blueprint, abort, render_template

from services.archive_service import get_race_page
from services.circuit_service import get_inline_circuit_geometry
from services.race_service import get_curated_race_events


races_bp = Blueprint("races", __name__, url_prefix="/season")


@races_bp.route("/<int:season>/race/<int:round_number>")
def race_page(season: int, round_number: int):
    race = get_race_page(season, round_number)
    race_map = get_curated_race_events(season, round_number)

    if race_map and race_map.get("map_mode") != "inline":
        layout_id = race_map["race"].get("layout_id")
        race_map["geometry"] = get_inline_circuit_geometry(layout_id)
        race_map["map_mode"] = "inline_generated"

    return render_template(
        "race.html",
        race=race,
        race_map=race_map,
    )
