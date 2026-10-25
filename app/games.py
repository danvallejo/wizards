import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GameTemplate:
    id: str
    name: str
    formats: tuple[str, ...]
    default_duration_min: int
    max_capacity: int
    min_players: int


def _positive_int(game_id: str, raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    # bool is an int subclass; `max_capacity = true` must not load as 1
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"game {game_id!r}: {key} must be a positive integer")
    return value


def _parse(game_id: str, raw: Any) -> GameTemplate:
    if not isinstance(raw, dict):
        raise ValueError(f"game {game_id!r}: must be a [games.{game_id}] table")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"game {game_id!r}: name must be a non-empty string")
    formats = raw.get("formats")
    if (
        not isinstance(formats, list)
        or not formats
        or not all(isinstance(f, str) and f.strip() for f in formats)
    ):
        raise ValueError(f"game {game_id!r}: formats must be a non-empty list of names")
    max_capacity = _positive_int(game_id, raw, "max_capacity")
    min_players = _positive_int(game_id, raw, "min_players")
    if min_players > max_capacity:
        raise ValueError(f"game {game_id!r}: min_players exceeds max_capacity")
    return GameTemplate(
        id=game_id,
        name=name,
        formats=tuple(formats),
        default_duration_min=_positive_int(game_id, raw, "default_duration_min"),
        max_capacity=max_capacity,
        min_players=min_players,
    )


def load_games(path: Path) -> dict[str, GameTemplate]:
    """Load and validate game templates; raises ValueError naming the bad game."""
    with path.open("rb") as f:
        tables = tomllib.load(f).get("games", {})
    if not tables:
        raise ValueError(f"{path}: no games defined")
    return {game_id: _parse(game_id, raw) for game_id, raw in tables.items()}
