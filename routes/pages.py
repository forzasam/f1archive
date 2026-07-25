from datetime import date
from pathlib import Path

from flask import Blueprint, Response, current_app, render_template, url_for


pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/about")
def about():
    return render_template("about.html")


@pages_bp.get("/contact")
def contact():
    return render_template("contact.html")


@pages_bp.get("/privacy")
def privacy():
    return render_template("privacy.html")


@pages_bp.get("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")


@pages_bp.get("/robots.txt")
def robots():
    body = "User-agent: *\nAllow: /\nSitemap: " + url_for("pages.sitemap", _external=True) + "\n"
    return Response(body, mimetype="text/plain")


def _available_seasons() -> list[int]:
    project_root = Path(current_app.root_path)
    years: set[int] = set()
    for base in (
        project_root / "data" / "archive" / "seasons",
        project_root / "data" / "live" / "seasons",
    ):
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir() and child.name.isdigit():
                years.add(int(child.name))
    return sorted(years)


@pages_bp.get("/sitemap.xml")
def sitemap():
    urls = [
        (url_for("home.index", _external=True), "weekly", "1.0"),
        (url_for("pages.about", _external=True), "monthly", "0.6"),
        (url_for("challenge.challenge_page", _external=True), "weekly", "0.6"),
        (url_for("pages.contact", _external=True), "yearly", "0.4"),
        (url_for("pages.privacy", _external=True), "yearly", "0.3"),
        (url_for("pages.disclaimer", _external=True), "yearly", "0.3"),
    ]
    current_year = date.today().year
    for season in _available_seasons():
        frequency = "daily" if season == current_year else "monthly"
        priority = "0.9" if season == current_year else "0.7"
        urls.append((url_for("seasons.season_page", season=season, _external=True), frequency, priority))

    xml = render_template("sitemap.xml", urls=urls)
    return Response(xml, mimetype="application/xml")
