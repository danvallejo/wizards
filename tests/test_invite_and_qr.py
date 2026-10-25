import re
import socket
from datetime import UTC, datetime

from icalendar import Calendar

from app.qr import detect_lan_ip, qr_svg
from tests.conftest import create_event


def page(client, event_id):
    return client.get(f"/events/{event_id}").get_data(as_text=True)


def test_qr_encodes_detected_lan_url_by_default(client):
    event_id = create_event(client)
    url = f"http://10.0.0.5:8000/events/{event_id}/register"
    html = page(client, event_id)
    assert qr_svg(url) in html
    assert url in html


def test_qr_uses_base_url_when_set(make_app):
    client = make_app(BASE_URL="https://events.example.com/").test_client()
    event_id = create_event(client)
    url = f"https://events.example.com/events/{event_id}/register"
    html = page(client, event_id)
    assert qr_svg(url) in html
    assert "10.0.0.5" not in html


def test_qr_differs_per_url():
    assert qr_svg("http://a/events/1/register") != qr_svg("http://a/events/2/register")


def test_detect_lan_ip_returns_ipv4():
    assert re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", detect_lan_ip())


def test_detect_lan_ip_falls_back_to_loopback(monkeypatch):
    def no_network(*args, **kwargs):
        raise OSError("network unreachable")

    monkeypatch.setattr(socket, "socket", no_network)
    assert detect_lan_ip() == "127.0.0.1"


def test_detected_ip_is_used_at_startup(make_app):
    client = make_app(DETECT_IP=lambda: "192.168.7.7").test_client()
    assert "http://192.168.7.7:8000/events/" in page(client, create_event(client))


def invite(client, event_id):
    resp = client.get(f"/events/{event_id}/invite.ics")
    assert resp.status_code == 200
    return resp


def test_ics_headers(client):
    event_id = create_event(client)
    resp = invite(client, event_id)
    assert resp.mimetype == "text/calendar"
    assert resp.headers["Content-Disposition"] == f'attachment; filename="event-{event_id}.ics"'


def test_ics_content(client):
    event_id = create_event(client, name="Friday Night Magic", location="Back Room, 1 Elm St")
    cal = Calendar.from_ical(invite(client, event_id).data)
    [vevent] = cal.walk("VEVENT")
    assert str(vevent["SUMMARY"]) == "Friday Night Magic"
    assert vevent.decoded("DTSTART") == datetime(2026, 11, 7, 2, 30, tzinfo=UTC)
    assert vevent.decoded("DTEND") == datetime(2026, 11, 7, 5, 30, tzinfo=UTC)
    assert str(vevent["LOCATION"]) == "Back Room, 1 Elm St"
    description = str(vevent["DESCRIPTION"])
    assert "Magic: The Gathering · Draft" in description
    assert f"http://10.0.0.5:8000/events/{event_id}/register" in description
    assert str(cal["VERSION"]) == "2.0"
    assert cal["PRODID"]


def test_ics_uid_is_stable_and_unique(client):
    first, second = create_event(client), create_event(client)

    def uid(event_id):
        [vevent] = Calendar.from_ical(invite(client, event_id).data).walk("VEVENT")
        return str(vevent["UID"])

    assert uid(first) == uid(first)
    assert uid(first) != uid(second)


def test_ics_times_use_utc(client):
    event_id = create_event(client, timezone="Asia/Tokyo", date="2026-11-07", time="10:00")
    body = invite(client, event_id).get_data(as_text=True)
    assert "DTSTART:20261107T010000Z" in body


def test_ics_unknown_event_404(client):
    assert client.get("/events/999/invite.ics").status_code == 404


def test_event_page_links_invite(client):
    event_id = create_event(client)
    assert f'href="/events/{event_id}/invite.ics"' in page(client, event_id)


def test_ics_uid_unique_across_databases(make_app, tmp_path):
    def first_uid(db_name):
        client = make_app(DATABASE=str(tmp_path / db_name)).test_client()
        event_id = create_event(client)
        [vevent] = Calendar.from_ical(invite(client, event_id).data).walk("VEVENT")
        return event_id, str(vevent["UID"])

    (id_a, uid_a), (id_b, uid_b) = first_uid("a.db"), first_uid("b.db")
    assert id_a == id_b == 1
    assert uid_a != uid_b
