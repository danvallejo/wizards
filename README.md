# wizards

Event calendar for in-store trading card game events: create an event, see it on the
calendar, share its QR code, and let players register until it fills up.

## Run it locally

Requires Python 3.12+ (developed on 3.14). From the repo root:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/flask --app app run --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000. The SQLite database is created automatically on first start
at `instance/events.db`.

### Recreating the database

Do this to wipe all events and registrations, or if you ran an earlier commit of this
repo (there are no schema migrations, so an old database won't match the current schema):

```sh
# 1. stop the server (Ctrl+C)
# 2. delete the database file — this permanently removes all events and registrations
rm instance/events.db
# 3. start the server again; it creates a fresh, empty database
.venv/bin/flask --app app run --host 0.0.0.0 --port 8000
```

If you set `DATABASE` to a custom path, delete that file instead.

### Scanning the QR code from a phone

The QR code on each event page points at `http://<this machine's LAN IP>:8000/...`,
detected at startup. With the server on `0.0.0.0` (as above) and the phone on the same
Wi-Fi, scanning just works. If the detected address is wrong (VPN, Docker, several
network interfaces), set it explicitly:

```sh
BASE_URL=http://192.168.1.20:8000 .venv/bin/flask --app app run --host 0.0.0.0 --port 8000
```

### Configuration

All optional, set as environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `BASE_URL` | `http://<detected LAN IP>:8000` | Base of the registration link in QR codes and invites |
| `STORE_TZ` | `America/Los_Angeles` | Default timezone on the create-event form |
| `STORE_LOCATION` | `Your Game Store, 123 Main St` | Default location on the create-event form |
| `DATABASE` | `instance/events.db` | SQLite file path |
| `GAMES_FILE` | `games.toml` | Game templates file |

## Run the tests

```sh
.venv/bin/pip install -r requirements-dev.txt
tools/gauntlet.sh
```

`tools/gauntlet.sh` runs lint, format check, type check, the test suite (random order,
100% line and branch coverage required), a check that core code never names a specific
game, and the mutation tests.
