from flask import Blueprint, abort, current_app, redirect, render_template, request
from werkzeug.wrappers import Response

from app.db import get_db
from app.events import agenda, create_event, get_event, list_events, validate_event

bp = Blueprint("events", __name__)


def _new_event_form(
    game_id: str, values: dict[str, str], errors: list[str], status: int
) -> tuple[str, int]:
    games = current_app.config["GAMES"]
    if game_id not in games:
        return render_template("new_event_pick.html", games=games.values(), errors=errors), status
    game = games[game_id]
    defaults = {
        "capacity": str(game.max_capacity),
        "duration_min": str(game.default_duration_min),
        "timezone": current_app.config["STORE_TZ"],
        "location": current_app.config["STORE_LOCATION"],
    }
    return render_template(
        "new_event.html", game=game, values={**defaults, **values}, errors=errors
    ), status


@bp.get("/")
def calendar() -> str:
    return render_template("calendar.html", days=agenda(list_events(get_db())))


@bp.get("/events/new")
def new_event() -> tuple[str, int]:
    game_id = request.args.get("game")
    if game_id is not None and game_id not in current_app.config["GAMES"]:
        abort(400, "Unknown game")
    return _new_event_form(game_id or "", {}, [], 200)


@bp.post("/events")
def post_event() -> Response | tuple[str, int]:
    form = request.form.to_dict()
    event, errors = validate_event(form, current_app.config["GAMES"])
    if event is None:
        return _new_event_form(form.get("game", ""), form, errors, 400)
    event_id = create_event(get_db(), event)
    return redirect(f"/events/{event_id}")


@bp.get("/events/<int:event_id>")
def show_event(event_id: int) -> str:
    event = get_event(get_db(), event_id)
    if event is None:
        abort(404)
    return render_template("event.html", event=event)
