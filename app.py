from flask import Flask

from config import Config
from routes.home import home_bp
from routes.races import races_bp
from routes.seasons import seasons_bp
from services.errors import F1DataError


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(home_bp)
    app.register_blueprint(seasons_bp)
    app.register_blueprint(races_bp)

    @app.errorhandler(F1DataError)
    def handle_data_error(error: F1DataError):
        return (
            app.jinja_env.get_template("error.html").render(message=str(error)),
            503,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
