import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Flask

from app import db, views
from app.events import local_day, local_time
from app.games import load_games

ROOT = Path(__file__).resolve().parent.parent


def create_app(overrides: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE", str(ROOT / "instance" / "events.db")),
        GAMES_FILE=os.environ.get("GAMES_FILE", str(ROOT / "games.toml")),
        STORE_TZ=os.environ.get("STORE_TZ", "America/Los_Angeles"),
        STORE_LOCATION=os.environ.get("STORE_LOCATION", "Your Game Store, 123 Main St"),
        NOW=lambda: datetime.now(UTC),
    )
    app.config.update(overrides or {})
    app.config["GAMES"] = load_games(Path(app.config["GAMES_FILE"]))
    db.init_app(app)
    app.register_blueprint(views.bp)
    app.add_template_filter(local_day)
    app.add_template_filter(local_time)
    return app
