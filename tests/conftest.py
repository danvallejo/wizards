from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.db import connect

# Fixed clock: before every event the tests create unless they say otherwise.
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def make_app(tmp_path: Path):
    def make(**overrides: Any) -> Flask:
        config = {
            "DATABASE": str(tmp_path / "test.db"),
            "NOW": lambda: NOW,
            "BASE_URL": "",  # ignore any BASE_URL in the developer's environment
            "DETECT_IP": lambda: "10.0.0.5",
            "LIST_IPS": lambda: [],
        }
        config.update(overrides)
        return create_app(config)

    return make


@pytest.fixture
def app(make_app) -> Flask:
    return make_app()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def rows(app: Flask, sql: str, *params: Any) -> list[dict[str, Any]]:
    conn = connect(app.config["DATABASE"])
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


VALID_EVENT = {
    "name": "Friday Night Magic",
    "game": "mtg",
    "format": "Draft",
    "date": "2026-11-06",
    "time": "18:30",
    "timezone": "America/Los_Angeles",
    "duration_min": "",
    "capacity": "8",
    "location": "Your Game Store, 123 Main St",
}


def create_event(client: FlaskClient, **fields: str) -> int:
    """POST a valid event (with overrides) and return its id."""
    resp = client.post("/events", data={**VALID_EVENT, **fields})
    assert resp.status_code == 302, resp.get_data(as_text=True)
    return int(resp.headers["Location"].rsplit("/", 1)[1])
