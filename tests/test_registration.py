from datetime import timedelta

import pytest

from tests.conftest import NOW, create_event, rows


def register(client, event_id, name):
    return client.post(f"/events/{event_id}/register", data={"name": name})


def registered(app, event_id):
    return rows(app, "SELECT name FROM registrations WHERE event_id = ? ORDER BY id", event_id)


def test_register_success(app, client):
    event_id = create_event(client)
    resp = register(client, event_id, "  Alex   Kim ")
    assert resp.status_code == 201
    assert "Alex Kim is registered for Friday Night Magic" in resp.get_data(as_text=True)
    assert registered(app, event_id) == [{"name": "Alex Kim"}]


def test_event_page_counts_registrations_and_links_form(client):
    event_id = create_event(client)
    register(client, event_id, "Alex")
    html = client.get(f"/events/{event_id}").get_data(as_text=True)
    assert "1 / 8 registered" in html
    assert f'href="/events/{event_id}/register"' in html


def test_min_players_status_flips_when_reached(client):
    event_id = create_event(client)
    for name in ("A", "B", "C"):
        register(client, event_id, name)
    assert "Needs 4 players to start" in client.get(f"/events/{event_id}").get_data(as_text=True)
    register(client, event_id, "D")
    assert "Enough players to start" in client.get(f"/events/{event_id}").get_data(as_text=True)


def test_full_event_rejected(app, client):
    event_id = create_event(client, capacity="2")
    register(client, event_id, "A")
    register(client, event_id, "B")
    resp = register(client, event_id, "C")
    assert resp.status_code == 409
    assert "This event is full (2/2)" in resp.get_data(as_text=True)
    assert len(registered(app, event_id)) == 2


@pytest.mark.parametrize("again", ["Alex", " alex  ", "ALEX", "Alex\t"])
def test_duplicate_name_rejected(app, client, again):
    event_id = create_event(client)
    register(client, event_id, "Alex")
    resp = register(client, event_id, again)
    assert resp.status_code == 409
    assert "Alex is already registered" in resp.get_data(as_text=True)
    assert len(registered(app, event_id)) == 1


def test_same_name_allowed_on_different_events(app, client):
    first, second = create_event(client), create_event(client)
    assert register(client, first, "Alex").status_code == 201
    assert register(client, second, "Alex").status_code == 201


def test_duplicate_on_full_event_reports_duplicate(client):
    event_id = create_event(client, capacity="1")
    register(client, event_id, "Alex")
    resp = register(client, event_id, "alex")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 409
    assert "Alex is already registered" in html
    assert "This event is full" not in html
    assert 'name="name"' not in html


@pytest.mark.parametrize(
    "name,message",
    [
        ("", "Name is required"),
        ("   ", "Name is required"),
        ("x" * 101, "Name must be at most 100 characters"),
    ],
)
def test_invalid_name_rejected(app, client, name, message):
    event_id = create_event(client)
    resp = register(client, event_id, name)
    assert resp.status_code == 400
    assert message in resp.get_data(as_text=True)
    assert registered(app, event_id) == []


def test_missing_name_field_rejected(app, client):
    event_id = create_event(client)
    assert client.post(f"/events/{event_id}/register", data={}).status_code == 400


def test_name_of_exactly_100_chars_accepted(client):
    event_id = create_event(client)
    assert register(client, event_id, "x" * 100).status_code == 201


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(minutes=5)])
def test_registration_closed_once_started(make_app, offset):
    # event starts 2026-11-07T02:30Z; clock at or after start
    start = NOW.replace(year=2026, month=11, day=7, hour=2, minute=30)
    app = make_app(NOW=lambda: start + offset)
    client = app.test_client()
    event_id = create_event(client)
    resp = register(client, event_id, "Alex")
    assert resp.status_code == 409
    assert "Registration is closed" in resp.get_data(as_text=True)
    assert registered(app, event_id) == []


def test_registration_open_one_minute_before_start(make_app):
    start = NOW.replace(year=2026, month=11, day=7, hour=2, minute=30)
    client = make_app(NOW=lambda: start - timedelta(minutes=1)).test_client()
    assert register(client, create_event(client), "Alex").status_code == 201


def test_register_form(client):
    event_id = create_event(client)
    html = client.get(f"/events/{event_id}/register").get_data(as_text=True)
    assert "Friday Night Magic" in html
    assert 'name="name"' in html


def test_register_form_for_full_event_shows_message_not_form(client):
    event_id = create_event(client, capacity="1")
    register(client, event_id, "Alex")
    resp = client.get(f"/events/{event_id}/register")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "This event is full (1/1)" in html
    assert 'name="name"' not in html


def test_register_form_for_started_event_shows_closed(make_app):
    start = NOW.replace(year=2026, month=11, day=7, hour=2, minute=30)
    client = make_app(NOW=lambda: start).test_client()
    event_id = create_event(client)
    html = client.get(f"/events/{event_id}/register").get_data(as_text=True)
    assert "Registration is closed" in html
    assert 'name="name"' not in html


@pytest.mark.parametrize("method", ["get", "post"])
def test_register_unknown_event_404(client, method):
    assert getattr(client, method)("/events/999/register", data={"name": "A"}).status_code == 404


def test_clock_is_read_while_holding_the_write_lock(app, client):
    from app.db import connect
    from app.registrations import register as do_register

    event_id = create_event(client)
    conn = connect(app.config["DATABASE"])
    reads: list[bool] = []

    def clock():
        reads.append(conn.in_transaction)
        return NOW

    try:
        do_register(conn, event_id, "Alex", clock)
    finally:
        conn.close()
    assert reads and all(reads)


def test_rejected_post_on_full_event_hides_form(client):
    event_id = create_event(client, capacity="1")
    register(client, event_id, "A")
    html = register(client, event_id, "B").get_data(as_text=True)
    assert "This event is full (1/1)" in html
    assert 'name="name"' not in html


def test_rejected_post_on_started_event_hides_form(make_app):
    start = NOW.replace(year=2026, month=11, day=7, hour=2, minute=30)
    client = make_app(NOW=lambda: start).test_client()
    html = register(client, create_event(client), "A").get_data(as_text=True)
    assert "Registration is closed" in html
    assert 'name="name"' not in html


def test_rejected_duplicate_on_open_event_keeps_form(client):
    event_id = create_event(client)
    register(client, event_id, "Alex")
    html = register(client, event_id, "alex").get_data(as_text=True)
    assert "Alex is already registered" in html
    assert 'name="name"' in html
