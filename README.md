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

To start with demo data (five events relative to today: one full, one with a single seat
left, one in the past), run this once on an empty database:

```sh
.venv/bin/python seed.py
```

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

## Design write-up

### Capacity: where it lives and how it's enforced

Capacity has two levels. Each game template in `games.toml` sets a `max_capacity` (30 for
Magic and Pokémon, 24 for Lorcana). The organizer picks the event's own `capacity` when
creating it, and the server rejects anything outside 1..`max_capacity`. That number is
stored on the event row, so later edits to the template don't change existing events.

Registration (`app/registrations.py`) is enforced on the server inside one SQLite
transaction opened with `BEGIN IMMEDIATE`, which takes the database write lock *before*
anything is read. Under the lock it reads the clock, then rejects in this order: event
already started (409), name already registered (409, even when the event is also full),
event full (409); otherwise it inserts. Duplicates are names compared after trimming,
collapsing whitespace and ignoring case, backed by a `UNIQUE(event_id, name_key)`
constraint.

**Concurrent registrations for the last seat:** the second request blocks on the write
lock (up to a 5 s busy timeout) until the first commits, then sees the new count and gets
"This event is full". `tests/test_concurrency.py` races 20 threads for the last seat, 20
rounds, and asserts exactly one winner every time. To prove the test can catch a race I
removed the transaction: 18 of 20 racers got in and a capacity-5 event overbooked to 22.
With a deferred `BEGIN`, the losers got 500s instead of a clean "full".

The limit of this design is SQLite's single writer, which is plenty for one store. On
Postgres the same rule would be `SELECT … FOR UPDATE` on the event row, or a conditional
`INSERT … SELECT … WHERE (count) < capacity`.

### Template system

A game is a table in `games.toml`: `name`, `formats`, `default_duration_min`,
`max_capacity`, `min_players`. It's validated at startup; a bad entry stops the app with
an error naming the game. Templates drive the create form (format list, prefilled
capacity and duration), server-side validation (format must be on the list, capacity
≤ max) and the event page (the "needs N players to start" status, display only). Core
code never names a game; `tools/check_no_game_names.py` fails the build if it does. Each
event saves the game's name and `min_players` when it's created, so events still display
correctly if their game is later removed from the file.

**Adding a 4th game** is a new `[games.<id>]` table and a restart, with no code change
(a test does exactly this). **A non-card game** is the same if it fits these properties.
If it needs a new kind of property, such as team size or a number of tables, that means a
new field on `GameTemplate`, its validation, and the code that uses it. That's growth in
the schema, still with no per-game `if`.

### What I cut or faked, and what's next

- **Cut, per the brief:** auth (anyone can create events), editing/cancelling events,
  payments, email, recurring events, admin dashboard.
- **Kept simple:** a grouped-by-day agenda rather than a month grid; Flask's development
  server, not a production WSGI server; no schema migrations (delete the database after
  pulling a schema change); `min_players` is display only.
- **Heuristics:** the QR base URL is the LAN IP detected at startup (`BASE_URL`
  overrides it). Duplicate detection is by name only, so two people with the same name
  need to tell themselves apart (e.g. "Alex K").
- **Checked only by tests, not by hand:** importing the `.ics` into Google Calendar or
  Outlook (tests parse it back with `icalendar`), and scanning the QR with a phone (tests
  rebuild the QR from the expected URL and require an exact match).
- **Next:** players cancelling their own registration plus a waitlist that promotes the
  next player, organizer login, a month view, real migrations, and rate limiting on
  registration.

## AI usage note

I used Claude Code (Claude Opus) to write the code, test-first, against a spec I approved
before any code existed (`SPEC.md`; my reasoning for each decision is in `DECISIONS.md`).
Before every commit, OpenAI's Codex CLI (`codex review`) reviewed the staged diff. From the
third commit on, I also reviewed each commit before it was made.

Examples of AI output that was wrong:

- **Claude** wrote `with sqlite3.connect(...) as conn:` to set up the schema, assuming
  that closes the connection. It only commits, so the connection leaked. Turning every
  warning into a test failure caught it (`ResourceWarning`), and the fix uses
  `contextlib.closing`.
- **Codex** claimed the 100% branch-coverage gate "cannot pass" with the tests as written.
  Running the gate showed it already passed, so I rejected that claim. I kept the useful
  part (two missing validation cases) as new tests.
- **Claude** implemented every feature but never wrote tests for two scenarios I had
  approved in the spec (adding a 4th game end to end, and an event outliving its removed
  game). It also called the 4th-game case "tested" in a draft of this README. Checking
  each spec scenario against the tests caught it before commit; both tests now exist,
  backed by mutants.
- **Codex** asked for a database migration when a column was added. Rejected: nothing
  had been deployed, so the README says to delete the development database instead.

Codex also caught real bugs, all fixed test-first:
- Registration read the clock before waiting for the lock, so a request that waited
  across the event's start could still get in.
- `.ics` IDs would have collided between two databases.
- A start time near year 9999 crashed the event page.
