from sqlite3 import Row

from flask import Blueprint, abort, current_app, redirect, render_template, request
from markupsafe import Markup
from werkzeug.wrappers import Response

from app.db import get_db
from app.events import agenda, create_event, get_event, list_events, validate_event
from app.invite import event_ics
from app.qr import qr_svg
from app.registrations import RegistrationRejected, register, unavailable_reason

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
    event = _event_or_404(event_id)
    url = _registration_url(event_id)
    return render_template("event.html", event=event, registration_url=url, qr=Markup(qr_svg(url)))


@bp.get("/events/<int:event_id>/invite.ics")
def invite(event_id: int) -> Response:
    event = _event_or_404(event_id)
    body = event_ics(event, _registration_url(event_id), current_app.config["NOW"]())
    return Response(
        body,
        mimetype="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="event-{event_id}.ics"'},
    )


def _registration_url(event_id: int) -> str:
    base: str = current_app.config["BASE_URL"].rstrip("/")
    return f"{base}/events/{event_id}/register"


def _event_or_404(event_id: int) -> Row:
    event = get_event(get_db(), event_id)
    if event is None:
        abort(404)
    return event


@bp.get("/events/<int:event_id>/register")
def register_form(event_id: int) -> str:
    event = _event_or_404(event_id)
    reason = unavailable_reason(event, current_app.config["NOW"]())
    return render_template("register.html", event=event, reason=reason, error=None)


@bp.post("/events/<int:event_id>/register")
def post_registration(event_id: int) -> tuple[str, int]:
    event = _event_or_404(event_id)
    clock = current_app.config["NOW"]
    try:
        name = register(get_db(), event_id, request.form.get("name", ""), clock)
    except RegistrationRejected as e:
        event = _event_or_404(event_id)  # fresh count: hide the form if now full/closed
        reason = unavailable_reason(event, clock())
        return render_template(
            "register.html", event=event, reason=reason, error=e.message
        ), e.status
    return render_template("registered.html", event=event, name=name), 201
