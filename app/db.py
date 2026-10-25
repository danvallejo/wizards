import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path: str) -> sqlite3.Connection:
    # isolation_level=None: no implicit transactions; writers use explicit
    # BEGIN IMMEDIATE. timeout: wait up to 5s on the write lock instead of erroring.
    conn = sqlite3.connect(path, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    db: sqlite3.Connection = g.db
    return db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app: Flask) -> None:
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(app.config["DATABASE"])) as conn:
        conn.executescript(SCHEMA.read_text())
    app.teardown_appcontext(close_db)
