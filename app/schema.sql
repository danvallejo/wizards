CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    game_id     TEXT    NOT NULL,
    -- snapshotted from the template so the event outlives template edits/removal
    game_name   TEXT    NOT NULL,
    min_players INTEGER NOT NULL,
    format      TEXT    NOT NULL,
    capacity    INTEGER NOT NULL CHECK (capacity >= 1),
    tz          TEXT    NOT NULL,
    start_utc   TEXT    NOT NULL,  -- ISO 8601 UTC, e.g. 2026-11-07T02:30:00Z
    end_utc     TEXT    NOT NULL,
    location    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS registrations (
    id         INTEGER PRIMARY KEY,
    event_id   INTEGER NOT NULL REFERENCES events (id),
    name       TEXT    NOT NULL,
    name_key   TEXT    NOT NULL,  -- normalized name; duplicate detection
    created_at TEXT    NOT NULL,
    UNIQUE (event_id, name_key)
);
