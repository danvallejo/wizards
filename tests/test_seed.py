import pytest

import seed
from tests.conftest import rows


def test_seed_creates_demo_events(app):
    seed.seed(app)
    events = rows(
        app,
        "SELECT e.name, e.capacity, e.start_utc,"
        " (SELECT count(*) FROM registrations r WHERE r.event_id = e.id) AS registered"
        " FROM events e ORDER BY e.id",
    )
    assert len(events) == 5
    assert {e["name"] for e in events} >= {"Magic Draft Night", "Commander Night"}
    by_name = {e["name"]: e for e in events}
    assert by_name["Commander Night"]["registered"] == by_name["Commander Night"]["capacity"]
    lorcana = by_name["Lorcana Sealed"]
    assert lorcana["registered"] == lorcana["capacity"] - 1


def test_seeded_full_event_rejects_registration(app):
    seed.seed(app)
    client = app.test_client()
    [full] = rows(app, "SELECT id FROM events WHERE name = 'Commander Night'")
    resp = client.post(f"/events/{full['id']}/register", data={"name": "Late Comer"})
    assert resp.status_code == 409


def test_seed_refuses_non_empty_database(app):
    seed.seed(app)
    with pytest.raises(SystemExit, match="already has events"):
        seed.seed(app)
    assert rows(app, "SELECT count(*) AS n FROM events")[0]["n"] == 5


def test_seed_with_invalid_demo_data_fails_loudly(app, monkeypatch):
    monkeypatch.setattr(seed, "DEMO", [(1, "18:00", "Bad", "mtg", "Not A Format", 8, 0)])
    with pytest.raises(SystemExit, match="'Bad' is invalid"):
        seed.seed(app)


def test_invalid_entry_leaves_database_empty(app, monkeypatch):
    monkeypatch.setattr(
        seed,
        "DEMO",
        [(1, "18:00", "Good", "mtg", "Draft", 8, 2), (2, "18:00", "Bad", "nope", "Draft", 8, 0)],
    )
    with pytest.raises(SystemExit, match="'Bad' is invalid"):
        seed.seed(app)
    assert rows(app, "SELECT count(*) AS n FROM events")[0]["n"] == 0
