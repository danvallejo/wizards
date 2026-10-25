from tests.conftest import create_event


def calendar(client):
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def in_order(html, *texts):
    positions = [html.index(t) for t in texts]
    return positions == sorted(positions)


def test_no_events(client):
    assert "No events scheduled" in calendar(client)


def test_grouped_by_day_and_sorted_by_time(client):
    create_event(client, name="Evening", date="2026-11-06", time="18:30")
    create_event(client, name="Noon", date="2026-11-06", time="12:00")
    create_event(client, name="Sunday", date="2026-11-08", time="10:00")
    html = calendar(client)
    assert in_order(html, "Fri Nov 6, 2026", "Noon", "Evening", "Sun Nov 8, 2026", "Sunday")
    assert html.count("Fri Nov 6, 2026") == 1


def test_late_evening_groups_under_local_date(client):
    # 23:00 PST Nov 6 is Nov 7 in UTC
    create_event(client, name="Late", date="2026-11-06", time="23:00")
    html = calendar(client)
    assert "Fri Nov 6, 2026" in html
    assert "Nov 7" not in html


def test_mixed_timezones_keep_headings_in_order(client):
    create_event(client, name="Tokyo", date="2026-11-07", time="10:00", timezone="Asia/Tokyo")
    create_event(client, name="LA", date="2026-11-06", time="20:00")
    html = calendar(client)
    assert in_order(html, "Fri Nov 6, 2026", "LA", "Sat Nov 7, 2026", "Tokyo")
    assert html.count("Fri Nov 6, 2026") == 1
    assert html.count("Sat Nov 7, 2026") == 1


def test_entry_shows_summary_and_links_to_event(client):
    event_id = create_event(client, name="Prerelease", capacity="12")
    html = calendar(client)
    for text in (
        "Prerelease",
        "Magic: The Gathering",
        "18:30 PST",
        "0 / 12",
        f'href="/events/{event_id}"',
    ):
        assert text in html


def test_nav_links_to_calendar(client):
    assert 'href="/"' in client.get("/events/new").get_data(as_text=True)
