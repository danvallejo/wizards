"""Fill an empty database with demo events: `.venv/bin/python seed.py`.

Goes through the same validation and registration code as the web app, so seeded
data obeys every rule (capacity, formats, duplicates). Dates are relative to today.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from flask import Flask

from app import create_app
from app.db import get_db
from app.events import create_event, validate_event
from app.registrations import register

# (days from today, time, name, game, format, capacity, players to register)
DEMO = [
    (-7, "18:00", "Modern Monthly", "mtg", "Modern", 16, 0),
    (2, "19:00", "Commander Night", "mtg", "Commander", 4, 4),
    (3, "12:00", "Pokémon League Challenge", "pokemon", "Standard", 30, 2),
    (5, "18:00", "Lorcana Sealed", "lorcana", "Sealed", 4, 3),
    (6, "18:30", "Magic Draft Night", "mtg", "Draft", 8, 5),
]
PLAYERS = ["Alex", "Sam", "Jordan", "Riley", "Casey"]


def seed(app: Flask) -> None:
    clock = app.config["NOW"]
    tz = app.config["STORE_TZ"]
    today = clock().astimezone(ZoneInfo(tz)).date()
    with app.app_context():
        db = get_db()
        if db.execute("SELECT count(*) FROM events").fetchone()[0]:
            raise SystemExit("Database already has events; delete it first (see README).")
        # validate everything first, so a bad entry can't leave a half-seeded database
        planned = []
        for days, time, name, game, fmt, capacity, players in DEMO:
            form = {
                "name": name,
                "game": game,
                "format": fmt,
                "date": (today + timedelta(days=days)).isoformat(),
                "time": time,
                "timezone": tz,
                "capacity": str(capacity),
                "location": app.config["STORE_LOCATION"],
            }
            event, errors = validate_event(form, app.config["GAMES"])
            if event is None:
                raise SystemExit(f"Seed event {name!r} is invalid: {errors}")
            planned.append((event, players))
        for event, players in planned:
            event_id = create_event(db, event)
            for player in PLAYERS[:players]:
                register(db, event_id, player, clock)
            print(f"  {event.name}: {players}/{event.capacity} registered")


if __name__ == "__main__":
    seed(create_app())
