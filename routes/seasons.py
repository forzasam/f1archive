from flask import Blueprint, abort, render_template, url_for

from services.archive_service import get_season_page
from services.season_bookends import get_season_bookend

seasons_bp = Blueprint("seasons", __name__, url_prefix="/season")


def _entry(kind, label, url, eyebrow=None):
    return {"kind": kind, "label": label, "url": url, "eyebrow": eyebrow or label}


def season_sequence(season: int, page_data=None):
    data = page_data or get_season_page(season)
    entries = []
    if data.get("setting_the_stakes"):
        entries.append(_entry("setting_the_stakes", "Setting the stakes", url_for("seasons.season_bookend_page", season=season, kind="setting_the_stakes")))
    for race in data["races"]:
        entries.append(_entry("race", race["name"], url_for("races.race_page", season=season, round_number=race["round"]), f"Round {race['round']}"))
    if data.get("aftermath"):
        entries.append(_entry("aftermath", "Aftermath", url_for("seasons.season_bookend_page", season=season, kind="aftermath")))
    return entries


def neighbours(entries, current_kind, round_number=None):
    idx = next((i for i,e in enumerate(entries) if e["kind"] == current_kind and (current_kind != "race" or e["eyebrow"] == f"Round {round_number}")), None)
    if idx is None:
        return {"previous": None, "next": None}
    return {"previous": entries[idx-1] if idx > 0 else None, "next": entries[idx+1] if idx+1 < len(entries) else None}


@seasons_bp.route("/<int:season>")
def season_page(season: int):
    page_data = get_season_page(season)
    if not page_data["races"]:
        abort(404)
    return render_template("season.html", **page_data)


@seasons_bp.route("/<int:season>/<kind>")
def season_bookend_page(season: int, kind: str):
    if kind not in {"setting_the_stakes", "aftermath"}:
        abort(404)
    story = get_season_bookend(season, kind)
    if story is None:
        abort(404)
    page_data = get_season_page(season)
    nav = neighbours(season_sequence(season, page_data), kind)
    return render_template("season_bookend.html", season=season, story=story, sequence_nav=nav)
