from tests.conftest import create_event


def test_event_page_shows_details(client):
    event_id = create_event(client, name="Pauper Night")
    resp = client.get(f"/events/{event_id}")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    for text in (
        "Pauper Night",
        "Magic: The Gathering",
        "Draft",
        "Fri Nov 6, 2026, 18:30 PST – 21:30 PST",
        "Your Game Store, 123 Main St",
        "0 / 8 registered",
        "Needs 4 players to start",
    ):
        assert text in html


def test_event_page_shows_own_timezone(client):
    event_id = create_event(client, timezone="America/New_York")
    assert "18:30 EST" in client.get(f"/events/{event_id}").get_data(as_text=True)


def test_unknown_event_is_404(client):
    assert client.get("/events/999").status_code == 404


def test_event_crossing_midnight_shows_end_date(client):
    event_id = create_event(client, time="23:30")
    html = client.get(f"/events/{event_id}").get_data(as_text=True)
    assert "Fri Nov 6, 2026, 23:30 PST – Sat Nov 7, 2026, 02:30 PST" in html
