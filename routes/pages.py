from flask import Blueprint, render_template


pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/about")
def about():
    return render_template("about.html")


@pages_bp.get("/contact")
def contact():
    return render_template("contact.html")
