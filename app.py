from flask import Flask, render_template

from config import Config
from routes.home import home_bp
from routes.races import races_bp
from routes.seasons import seasons_bp
from services.errors import F1DataError
from services.logging_config import configure_logging


def create_app() -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(home_bp)
    app.register_blueprint(seasons_bp)
    app.register_blueprint(races_bp)

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "error.html",
            code="404",
            title="Page Not Found",
            heading="Yellow flag!",
            message="The page you're looking for has gone off the circuit.",
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled application error")

        return render_template(
            "error.html",
            code="500",
            title="Internal Server Error",
            heading="Red flag!",
            message="Something has stopped the session. Please try again shortly.",
        ), 500

    @app.errorhandler(F1DataError)
    def handle_data_error(error: F1DataError):
        app.logger.warning("F1 data unavailable: %s", error)

        return render_template(
            "error.html",
            code="503",
            title="Data Unavailable",
            heading="Safety Car",
            message="Formula 1 data is temporarily unavailable. Please try again shortly.",
        ), 503

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)