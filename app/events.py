import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.games import GameTemplate

MAX_NAME_LEN = 100
MAX_DURATION_MIN = 24 * 60


@dataclass(frozen=True)
class NewEvent:
    name: str
    game: GameTemplate
    format: str
    capacity: int
    tz: str
    start: datetime  # aware, UTC
    end: datetime
    location: str


def iso_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _local(utc_text: str, tz_name: str) -> datetime:
    return parse_iso_utc(utc_text).astimezone(ZoneInfo(tz_name))


def local_day(utc_text: str, tz_name: str) -> str:
    """'Fri Nov 6, 2026' in the event's own timezone."""
    d = _local(utc_text, tz_name)
    return f"{d:%a %b} {d.day}, {d.year}"


def local_time(utc_text: str, tz_name: str) -> str:
    """'18:30 PST' in the event's own timezone."""
    return f"{_local(utc_text, tz_name):%H:%M %Z}"


def _int_in_range(raw: str, low: int, high: int) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if low <= value <= high else None


def local_to_utc(day: str, at: str, tz_name: str) -> datetime:
    """Interpret a wall-clock date/time in tz_name; ValueError with a user message.

    Rejects DST-gap (nonexistent) and DST-overlap (ambiguous) times rather than guessing.
    """
    try:
        zone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Unknown timezone") from None
    try:
        wall = datetime.strptime(f"{day} {at}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("Enter a valid date and time") from None
    try:
        early = wall.replace(tzinfo=zone, fold=0).astimezone(UTC)
        late = wall.replace(tzinfo=zone, fold=1).astimezone(UTC)
    except OverflowError:  # e.g. year 1 in a zone ahead of UTC
        raise ValueError("Enter a valid date and time") from None
    if early != late:
        if early.astimezone(zone).replace(tzinfo=None) != wall:
            raise ValueError(f"This time does not exist in {tz_name} (daylight saving change)")
        raise ValueError(f"This time is ambiguous in {tz_name}")
    return early


def validate_event(
    form: Mapping[str, str], games: Mapping[str, GameTemplate]
) -> tuple[NewEvent | None, list[str]]:
    """Validate a create-event form. Returns (event, []) or (None, error messages)."""
    errors: list[str] = []
    game = games.get(form.get("game", ""))
    if game is None:
        return None, ["Unknown game"]

    name = form.get("name", "").strip()
    if not name:
        errors.append("Name is required")
    elif len(name) > MAX_NAME_LEN:
        errors.append(f"Name must be at most {MAX_NAME_LEN} characters")

    fmt = form.get("format", "")
    if fmt not in game.formats:
        errors.append(f"Choose a format for {game.name}")

    capacity = _int_in_range(form.get("capacity", ""), 1, game.max_capacity)
    if capacity is None:
        errors.append(f"Capacity must be between 1 and {game.max_capacity}")

    raw_duration = form.get("duration_min", "").strip()
    duration = (
        _int_in_range(raw_duration, 1, MAX_DURATION_MIN)
        if raw_duration
        else game.default_duration_min
    )
    if duration is None:
        errors.append(f"Duration must be between 1 and {MAX_DURATION_MIN} minutes")

    location = form.get("location", "").strip()
    if not location:
        errors.append("Location is required")

    tz_name = form.get("timezone", "").strip()
    start: datetime | None = None
    end: datetime | None = None
    try:
        start = local_to_utc(form.get("date", ""), form.get("time", ""), tz_name)
        end = start + timedelta(minutes=duration or 0)
        end.astimezone(ZoneInfo(tz_name))  # the page shows end in local time
    except ValueError as e:
        errors.append(str(e))
    except OverflowError:  # end (UTC or local) runs past year 9999
        errors.append("Enter a valid date and time")

    if errors or capacity is None or start is None or end is None:
        return None, errors
    return NewEvent(
        name=name,
        game=game,
        format=fmt,
        capacity=capacity,
        tz=tz_name,
        start=start,
        end=end,
        location=location,
    ), []


def create_event(db: sqlite3.Connection, event: NewEvent) -> int:
    cur = db.execute(
        "INSERT INTO events (name, game_id, game_name, min_players, format, capacity,"
        " tz, start_utc, end_utc, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event.name,
            event.game.id,
            event.game.name,
            event.game.min_players,
            event.format,
            event.capacity,
            event.tz,
            iso_utc(event.start),
            iso_utc(event.end),
            event.location,
        ),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def get_event(db: sqlite3.Connection, event_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = db.execute(
        "SELECT e.*, (SELECT count(*) FROM registrations r WHERE r.event_id = e.id)"
        " AS registered FROM events e WHERE e.id = ?",
        (event_id,),
    ).fetchone()
    return row
