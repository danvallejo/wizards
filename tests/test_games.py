from pathlib import Path

import pytest

from app.games import GameTemplate, load_games

REPO_GAMES = Path(__file__).resolve().parent.parent / "games.toml"

VALID = """
[games.test_game]
name = "Test Game"
formats = ["Casual"]
default_duration_min = 60
max_capacity = 10
min_players = 2
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "games.toml"
    p.write_text(text)
    return p


def test_shipped_templates_load():
    games = load_games(REPO_GAMES)
    assert len(games) == 3
    assert games["mtg"].name == "Magic: The Gathering"
    for g in games.values():
        assert g.formats
        assert g.default_duration_min > 0
        assert 1 <= g.max_capacity <= 30
        assert 1 <= g.min_players <= g.max_capacity


def test_loads_all_fields(tmp_path):
    games = load_games(write(tmp_path, VALID))
    assert games == {
        "test_game": GameTemplate(
            id="test_game",
            name="Test Game",
            formats=("Casual",),
            default_duration_min=60,
            max_capacity=10,
            min_players=2,
        )
    }


@pytest.mark.parametrize(
    "old,new",
    [
        ("max_capacity = 10", "max_capacity = 0"),
        ('formats = ["Casual"]', "formats = []"),
        ('formats = ["Casual"]', 'formats = [""]'),
        ('formats = ["Casual"]', 'formats = "Casual"'),
        ("default_duration_min = 60", "default_duration_min = 0"),
        ("default_duration_min = 60", 'default_duration_min = "60"'),
        ("min_players = 2", "min_players = 0"),
        ("min_players = 2", "min_players = 11"),
        ('name = "Test Game"', 'name = ""'),
        ("min_players = 2", ""),
        ("max_capacity = 10", "max_capacity = true"),
        ('name = "Test Game"', "name = 5"),
        ('formats = ["Casual"]', 'formats = ["Casual", 3]'),
    ],
)
def test_invalid_template_fails_naming_game(tmp_path, old, new):
    with pytest.raises(ValueError, match="test_game"):
        load_games(write(tmp_path, VALID.replace(old, new)))


def test_no_games_fails(tmp_path):
    with pytest.raises(ValueError, match="no games"):
        load_games(write(tmp_path, "# empty\n"))


def test_non_table_game_entry_fails_naming_game(tmp_path):
    with pytest.raises(ValueError, match="test_game"):
        load_games(write(tmp_path, "[games]\ntest_game = 1\n"))
