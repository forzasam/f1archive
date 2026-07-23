from flask import Blueprint, jsonify, render_template, request

from services.archive_service import (
    build_homepage_data,
    get_constructor_options_for_driver,
    get_driver_options_for_constructor,
)

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    selected_driver = request.args.get("driver", "").strip()
    selected_constructor = request.args.get("constructor", "").strip()

    page_data = build_homepage_data(
        selected_driver=selected_driver,
        selected_constructor=selected_constructor,
    )

    return render_template("home.html", **page_data)


@home_bp.get("/api/filter-options")
def filter_options():
    driver_id = request.args.get("driver", "").strip()
    constructor_id = request.args.get("constructor", "").strip()

    if driver_id:
        constructors = get_constructor_options_for_driver(driver_id)
        return jsonify({
            "constructors": [
                {
                    "id": constructor.constructor_id,
                    "name": constructor.name,
                    "nationality": constructor.nationality,
                }
                for constructor in constructors
            ]
        })

    if constructor_id:
        drivers = get_driver_options_for_constructor(constructor_id)
        return jsonify({
            "drivers": [
                {
                    "id": driver.driver_id,
                    "name": driver.name,
                    "nationality": driver.nationality,
                }
                for driver in drivers
            ]
        })

    return jsonify({"drivers": [], "constructors": []})
