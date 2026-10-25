from pathlib import Path

from tests.conftest import VALID_EVENT, create_event

SHIPPED = (Path(__file__).resolve().parent.parent / "games.toml").read_text()

FOURTH_GAME = """
[games.test_game]
name = "Test Game"
formats = ["Casual"]
default_duration_min = 60
max_capacity = 3
min_players = 2
"""


def games_file(tmp_path: Path, text: str) -> str:
    path = tmp_path / "games.toml"
    path.write_text(text)
    return str(path)


def test_fourth_game_needs_only_data(make_app, tmp_path):
    client = make_app(GAMES_FILE=games_file(tmp_path, SHIPPED + FOURTH_GAME)).test_client()
    form = client.get("/events/new?game=test_game").get_data(as_text=True)
    assert 'name="capacity" value="3"' in form
    assert 'name="duration_min" value="60"' in form

    event_id = create_event(client, game="test_game", format="Casual", capacity="3")
    assert "Test Game" in client.get(f"/events/{event_id}").get_data(as_text=True)
    assert "Needs 2 players to start" in client.get(f"/events/{event_id}").get_data(as_text=True)
    for name in ("A", "B", "C"):
        assert client.post(f"/events/{event_id}/register", data={"name": name}).status_code == 201
    assert client.post(f"/events/{event_id}/register", data={"name": "D"}).status_code == 409
    # the template's own max applies, not another game's
    assert create_event_status(client, game="test_game", format="Casual", capacity="4") == 400


def create_event_status(client, **fields) -> int:
    return client.post("/events", data={**VALID_EVENT, **fields}).status_code


def test_event_survives_its_game_being_removed(make_app, tmp_path):
    with_game = make_app(GAMES_FILE=games_file(tmp_path, SHIPPED + FOURTH_GAME)).test_client()
    event_id = create_event(with_game, game="test_game", format="Casual", capacity="3")

    # restart with the game removed from the file (same database)
    client = make_app(GAMES_FILE=games_file(tmp_path, SHIPPED)).test_client()
    page = client.get(f"/events/{event_id}").get_data(as_text=True)
    assert "Test Game" in page
    assert "Needs 2 players to start" in page
    assert "Test Game" in client.get("/").get_data(as_text=True)
    assert client.get("/events/new?game=test_game").status_code == 400
    assert create_event_status(client, game="test_game", format="Casual") == 400
