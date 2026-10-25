import uuid

import pytest

from tests.conftest import VALID_EVENT, create_event, rows


def post(client, **fields):
    return client.post("/events", data={**VALID_EVENT, **fields})


def event_count(app):
    return rows(app, "SELECT count(*) AS n FROM events")[0]["n"]


def test_create_valid_event(app, client):
    event_id = create_event(client)
    [event] = rows(app, "SELECT * FROM events WHERE id = ?", event_id)
    assert uuid.UUID(event.pop("uid")).version == 4
    assert event == {
        "id": event_id,
        "name": "Friday Night Magic",
        "game_id": "mtg",
        "game_name": "Magic: The Gathering",
        "min_players": 4,
        "format": "Draft",
        "capacity": 8,
        "tz": "America/Los_Angeles",
        "start_utc": "2026-11-07T02:30:00Z",
        "end_utc": "2026-11-07T05:30:00Z",  # mtg default 180 min
        "location": "Your Game Store, 123 Main St",
    }


def test_redirects_to_event_page(client):
    resp = post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/events/")


def test_duration_override(app, client):
    event_id = create_event(client, duration_min="90")
    [event] = rows(app, "SELECT end_utc FROM events WHERE id = ?", event_id)
    assert event["end_utc"] == "2026-11-07T04:00:00Z"


def test_per_event_timezone(app, client):
    event_id = create_event(client, timezone="America/New_York")
    [event] = rows(app, "SELECT tz, start_utc FROM events WHERE id = ?", event_id)
    assert event == {"tz": "America/New_York", "start_utc": "2026-11-06T23:30:00Z"}


def test_capacity_at_template_max_accepted(app, client):
    event_id = create_event(client, capacity="30")
    assert rows(app, "SELECT capacity FROM events WHERE id = ?", event_id)[0]["capacity"] == 30


def test_capacity_max_comes_from_template(app, client):
    resp = post(client, game="lorcana", format="Sealed", capacity="25")
    assert resp.status_code == 400
    assert "Capacity must be between 1 and 24" in resp.get_data(as_text=True)


def test_past_event_allowed(app, client):
    create_event(client, date="2020-01-01")
    assert event_count(app) == 1


@pytest.mark.parametrize(
    "fields,message",
    [
        ({"capacity": "31"}, "Capacity must be between 1 and 30"),
        ({"capacity": "0"}, "Capacity must be between 1 and 30"),
        ({"capacity": "-3"}, "Capacity must be between 1 and 30"),
        ({"capacity": "eight"}, "Capacity must be between 1 and 30"),
        ({"capacity": ""}, "Capacity must be between 1 and 30"),
        ({"game": "chess"}, "Unknown game"),
        ({"game": ""}, "Unknown game"),
        ({"game": "lorcana", "format": "Expanded"}, "Choose a format for Disney Lorcana"),
        ({"format": ""}, "Choose a format for Magic: The Gathering"),
        ({"name": ""}, "Name is required"),
        ({"name": "   "}, "Name is required"),
        ({"name": "x" * 101}, "Name must be at most 100 characters"),
        ({"location": " "}, "Location is required"),
        ({"date": "2026-13-01"}, "Enter a valid date and time"),
        ({"date": ""}, "Enter a valid date and time"),
        ({"time": "25:00"}, "Enter a valid date and time"),
        ({"date": "9999-12-31", "time": "23:59"}, "Enter a valid date and time"),
        ({"date": "9999-12-31", "time": "15:00"}, "Enter a valid date and time"),
        (
            {"date": "9999-12-31", "time": "22:00", "timezone": "Asia/Tokyo"},
            "Enter a valid date and time",
        ),
        (
            {"date": "0001-01-01", "time": "00:00", "timezone": "Asia/Tokyo"},
            "Enter a valid date and time",
        ),
        ({"duration_min": "0"}, "Duration must be between 1 and 1440 minutes"),
        ({"duration_min": "1441"}, "Duration must be between 1 and 1440 minutes"),
        ({"duration_min": "long"}, "Duration must be between 1 and 1440 minutes"),
        ({"timezone": "Mars/Olympus"}, "Unknown timezone"),
        ({"timezone": ""}, "Unknown timezone"),
        (
            {"date": "2026-03-08", "time": "02:30"},
            "This time does not exist in America/Los_Angeles (daylight saving change)",
        ),
        (
            {"date": "2026-11-01", "time": "01:30"},
            "This time is ambiguous in America/Los_Angeles",
        ),
    ],
)
def test_invalid_event_rejected(app, client, fields, message):
    resp = post(client, **fields)
    assert resp.status_code == 400
    assert message in resp.get_data(as_text=True)
    assert event_count(app) == 0


def test_missing_fields_rejected(app, client):
    resp = client.post("/events", data={})
    assert resp.status_code == 400
    assert event_count(app) == 0


def test_rejected_form_keeps_entered_values(client):
    resp = post(client, capacity="99", name="Keep Me")
    assert 'value="Keep Me"' in resp.get_data(as_text=True)


def test_new_event_form_prefills_from_template(client):
    resp = client.get("/events/new?game=lorcana")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    for fmt in ("Core Constructed", "Infinity Constructed", "Sealed"):
        assert fmt in html
    assert 'name="capacity" value="24"' in html
    assert 'max="24"' in html
    assert 'name="duration_min" value="150"' in html
    assert 'value="America/Los_Angeles"' in html
    assert 'value="Your Game Store, 123 Main St"' in html


def test_new_event_without_game_lists_games(client):
    html = client.get("/events/new").get_data(as_text=True)
    for game_id in ("mtg", "pokemon", "lorcana"):
        assert f"/events/new?game={game_id}" in html


def test_new_event_unknown_game_is_400(client):
    assert client.get("/events/new?game=chess").status_code == 400
