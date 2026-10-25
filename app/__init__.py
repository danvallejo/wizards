import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Flask

from app import db, views
from app.events import local_day, local_time
from app.games import load_games
from app.qr import detect_lan_ip, host_addresses

ROOT = Path(__file__).resolve().parent.parent


def create_app(overrides: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE", str(ROOT / "instance" / "events.db")),
        GAMES_FILE=os.environ.get("GAMES_FILE", str(ROOT / "games.toml")),
        STORE_TZ=os.environ.get("STORE_TZ", "America/Los_Angeles"),
        STORE_LOCATION=os.environ.get("STORE_LOCATION", "Your Game Store, 123 Main St"),
        NOW=lambda: datetime.now(UTC),
        BASE_URL=os.environ.get("BASE_URL", ""),
        DETECT_IP=detect_lan_ip,
        LIST_IPS=host_addresses,
    )
    app.config.update(overrides or {})
    others: list[str] = []
    if not app.config["BASE_URL"]:
        detected = app.config["DETECT_IP"]()
        app.config["BASE_URL"] = f"http://{detected}:8000"
        others = [
            f"http://{ip}:8000"
            for ip in sorted(set(app.config["LIST_IPS"]()))
            if ip != detected and not ip.startswith("127.")
        ]
    # Detection can pick a VPN/Docker address phones can't reach; say what we chose.
    print(
        f"QR codes will point to {app.config['BASE_URL']}. If phones can't open that"
        " address, set BASE_URL (see README).",
        file=sys.stderr,
    )
    if others:
        print(
            f"Other addresses for this machine: {', '.join(others)}. If phones can't open"
            " the QR link, restart with BASE_URL set to one that phones can open.",
            file=sys.stderr,
        )
    app.config["GAMES"] = load_games(Path(app.config["GAMES_FILE"]))
    db.init_app(app)
    app.register_blueprint(views.bp)
    app.add_template_filter(local_day)
    app.add_template_filter(local_time)
    return app
