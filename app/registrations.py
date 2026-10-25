import sqlite3
from collections.abc import Callable
from datetime import datetime

from app.events import MAX_NAME_LEN, parse_iso_utc


class RegistrationRejected(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def clean_name(raw: str) -> str:
    """Trim and collapse whitespace; raise 400 if empty or too long."""
    name = " ".join(raw.split())
    if not name:
        raise RegistrationRejected(400, "Name is required")
    if len(name) > MAX_NAME_LEN:
        raise RegistrationRejected(400, f"Name must be at most {MAX_NAME_LEN} characters")
    return name


def _full(event: sqlite3.Row) -> str | None:
    if event["registered"] >= event["capacity"]:
        return f"This event is full ({event['registered']}/{event['capacity']})"
    return None


def _closed(event: sqlite3.Row, now: datetime) -> str | None:
    return "Registration is closed" if now >= parse_iso_utc(event["start_utc"]) else None


def unavailable_reason(event: sqlite3.Row, now: datetime) -> str | None:
    """Why the registration form is unavailable (closed or full), or None if open."""
    return _closed(event, now) or _full(event)


def register(
    db: sqlite3.Connection, event_id: int, raw_name: str, clock: Callable[[], datetime]
) -> str:
    """Register a player for an existing event; returns the stored name.

    Capacity is enforced here, not in the UI. BEGIN IMMEDIATE takes SQLite's write
    lock before the seat count is read, so concurrent requests for the last seat
    serialize: the second one sees the first one's row and is rejected as full.
    The clock is read after the lock, so time spent waiting counts toward the cutoff.
    """
    name = clean_name(raw_name)
    db.execute("BEGIN IMMEDIATE")
    try:
        now = clock()
        event = db.execute(
            "SELECT e.capacity, e.start_utc,"
            " (SELECT count(*) FROM registrations r WHERE r.event_id = e.id) AS registered"
            " FROM events e WHERE e.id = ?",
            (event_id,),
        ).fetchone()
        # order matters: closed, then duplicate (even when full), then full
        closed = _closed(event, now)
        if closed:
            raise RegistrationRejected(409, closed)
        existing = db.execute(
            "SELECT name FROM registrations WHERE event_id = ? AND name_key = ?",
            (event_id, name.casefold()),
        ).fetchone()
        if existing is not None:
            raise RegistrationRejected(409, f"{existing['name']} is already registered")
        full = _full(event)
        if full:
            raise RegistrationRejected(409, full)
        db.execute(
            "INSERT INTO registrations (event_id, name, name_key, created_at) VALUES (?, ?, ?, ?)",
            (event_id, name, name.casefold(), now.isoformat()),
        )
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return name
