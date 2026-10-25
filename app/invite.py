import sqlite3
from datetime import datetime

from icalendar import Calendar, Event

from app.events import parse_iso_utc


def event_ics(event: sqlite3.Row, registration_url: str, now: datetime) -> bytes:
    """A single-event iCalendar file with UTC start/end, importable by Google/Outlook."""
    vevent = Event()
    vevent.add("uid", f"{event['uid']}@game-events")
    vevent.add("dtstamp", now)
    vevent.add("dtstart", parse_iso_utc(event["start_utc"]))
    vevent.add("dtend", parse_iso_utc(event["end_utc"]))
    vevent.add("summary", event["name"])
    vevent.add("location", event["location"])
    vevent.add(
        "description",
        f"{event['game_name']} · {event['format']}\nRegister: {registration_url}",
    )
    vevent.add("url", registration_url)
    cal = Calendar()
    cal.add("prodid", "-//Game Events//EN")
    cal.add("version", "2.0")
    cal.add_component(vevent)
    ical: bytes = cal.to_ical()
    return ical
