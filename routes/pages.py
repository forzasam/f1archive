from datetime import date
from pathlib import Path

from services.authors import get_author, get_authors

from flask import Blueprint, Response, abort, current_app, render_template, request, url_for


pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/about")
def about():
    return render_template("about.html")


@pages_bp.get("/contact")
def contact():
    return render_template("contact.html")


@pages_bp.get("/contribute")
def contribute():
    return render_template("contribute.html")




@pages_bp.get("/authors")
def authors():
    return render_template("authors.html", authors=get_authors())


@pages_bp.get("/authors/<slug>")
def author_detail(slug: str):
    author = get_author(slug)
    if author is None:
        abort(404)

    per_page = 10
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    total_stories = len(author["all_stories"])
    total_pages = max(1, (total_stories + per_page - 1) // per_page)
    if page > total_pages and total_stories:
        abort(404)

    start = (page - 1) * per_page
    end = start + per_page
    paginated_stories = author["all_stories"][start:end]

    return render_template(
        "author.html",
        author=author,
        stories=paginated_stories,
        page=page,
        total_pages=total_pages,
    )


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
        (url_for("pages.authors", _external=True), "weekly", "0.7"),
        (url_for("pages.contribute", _external=True), "monthly", "0.7"),
        (url_for("challenge.challenge_page", _external=True), "weekly", "0.6"),
        (url_for("pages.contact", _external=True), "yearly", "0.4"),
        (url_for("pages.privacy", _external=True), "yearly", "0.3"),
        (url_for("pages.disclaimer", _external=True), "yearly", "0.3"),
    ]
    for author in get_authors():
        urls.append(
            (
                url_for("pages.author_detail", slug=author["slug"], _external=True),
                "monthly",
                "0.5",
            )
        )

    current_year = date.today().year
    for season in _available_seasons():
        frequency = "daily" if season == current_year else "monthly"
        priority = "0.9" if season == current_year else "0.7"
        urls.append((url_for("seasons.season_page", season=season, _external=True), frequency, priority))

    xml = render_template("sitemap.xml", urls=urls)
    return Response(xml, mimetype="application/xml")
