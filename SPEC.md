# SPEC — Event Calendar for Tabletop Game Events

Source requirements: `Senior_Software_Engineer_—_Take-Home.md`. This file resolves its gaps
and conflicts (decisions below were made with the repo owner on 2026-10-25).

- Tier: 2, plus one targeted concurrency test (last-seat race). Timebox 3h.
- Isolation: none — work lands directly on `main` (owner decision; no branches).

## Setup plan

- Tools to install: Python venv at `.venv` (Python 3.14 already present). No uv.
- Git: checkpoint commits on `main`, one per slice below, real messages, no
  `Co-Authored-By` trailer. Before every commit: `/codex:review --wait`, fix findings,
  re-run until clean (`/codex:review` is not available in this harness; the gate is
  `codex review --uncommitted`, Codex CLI 0.163.0). **Never push** (owner pushes to the
  public host). The owner's `DECISIONS.md` is staged into every commit made while it has
  changes. Claude never edits it.
  Slices: (0) SPEC.md, (1) tooling + game templates, (2) event creation + DB,
  (3) calendar, (4) event page + .ics + QR, (5) registration + capacity,
  (6) seed + README, (7) EVIDENCE.md.
- Files the gauntlet adds:
  - `tools/gauntlet.sh` — single entry point; runs every layer, fails closed
  - `tools/mutants.py` — manual mutation runner; proves each mutant was applied
    (file changed) and restored (`git diff --exit-code`)
  - `tools/check_no_game_names.py` — grep gate: core event code contains no game names
  - `requirements.txt`, `requirements-dev.txt` — exact pinned versions
  - `pyproject.toml` — ruff, mypy, pytest config
- Runtime dependencies:
  - `flask` — routing, forms, Jinja templates and test client in one package
  - `qrcode` — QR generation (spec: must be a library); SVG output, no Pillow needed
  - `icalendar` — .ics generation (spec: must be a library); also used in tests to parse output back
- Dev dependencies: `pytest`, `pytest-cov` (coverage gate), `pytest-randomly` (random order),
  `mypy`, `ruff`, `pip-audit` (one supply-chain run).
- Stdlib: `sqlite3`, `zoneinfo`, `tomllib`.

## Decisions (gap/conflict resolutions)

| # | Topic | Decision |
|---|---|---|
| 1 | Capacity | Each template has `max_capacity`; shipped games are all ≤ 30. No global cap. Organizer capacity must be 1..`max_capacity`, checked on the server. The form starts at the max. |
| 2 | Duplicates | Duplicate = same *normalized* name per event: trim the name, collapse whitespace, casefold. Enforced by DB `UNIQUE(event_id, name_key)`. Known limit: two real people with the same name need to tell themselves apart (README). |
| 3 | Location | Per-event field, prefilled from `STORE_LOCATION` config. Written to the .ics `LOCATION`. |
| 4 | Time | Each event has an IANA timezone field, prefilled from `STORE_TZ` (default `America/Los_Angeles`); invalid name → 400. Organizer enters date/time local to that tz. Event stores tz + UTC start/end. End = start + duration in minutes; defaults to the template's `default_duration_min`, organizer can change it. .ics uses UTC `DTSTART`/`DTEND`. A start time that doesn't exist in that tz (DST gap) → 400 "This time does not exist in <tz> (daylight saving change)". A start time that is ambiguous (DST overlap) → 400 "This time is ambiguous in <tz>". |
| 5 | Format | Template lists `formats`; event stores one; server rejects a format not in that game's list. |
| 6 | Min players | Template `min_players`; display-only status on event page. Nothing enforced. |
| 7 | QR URL | Registration URL base = `BASE_URL` env if set, else `http://<auto-detected LAN IP>:8000`. The IP is detected once at startup (UDP socket `connect` + `getsockname`, which sends no packets); if detection fails, it falls back to `127.0.0.1`. The app runs on `0.0.0.0:8000`. QR encodes `<base>/events/<id>/register`. Known limit: can pick the wrong interface on VPN/Docker → set `BASE_URL`. |
| 8 | Past events | Creating past events is allowed (eases seeding). Registration is rejected once `now >= event start`. |
| 9 | Templates | Data file `games.toml` (stdlib `tomllib`). Adding a 4th game = add a TOML table; no code change. Core code never branches on game id. |
| 10 | Calendar | Grouped-by-day agenda list (no JS/calendar lib). Each event is grouped under its date in its *own* tz. Day headings are in ascending date order; entries within a day are sorted by UTC start. Time is shown with the tz abbreviation (e.g. `18:30 PST`). |
| 11 | Games | Magic: The Gathering, Pokémon TCG, Disney Lorcana (owner may veto). |
| 12 | Removed/renamed game | At creation the event snapshots everything it later displays from its template: `game_id`, game name, `min_players` (format, capacity and duration are already stored). Old events render after their game leaves `games.toml`; new events can't pick it. Event pages and the calendar never read the template. |

Template properties: `name`, `formats`, `default_duration_min`, `max_capacity`, `min_players`.

## Concurrency design

Registration runs in one `BEGIN IMMEDIATE` SQLite transaction, which takes the DB write
lock before reading. Inside it: event exists? → not started? → name not already
registered? → `count(registrations) < capacity`? → insert. Two requests can't both see
the last free seat, because the second waits on the lock. `UNIQUE(event_id, name_key)` is
a backstop for duplicates. Connections use `busy_timeout` so waiting requests queue
instead of erroring. Ceiling: one SQLite writer, which is fine for one store. A move to
Postgres would need `SELECT … FOR UPDATE` or a conditional insert (README).

## Scenarios

```gherkin
Feature: Game templates
  Scenario: templates load from games.toml
    Then 3 games are available including "Magic: The Gathering"
    And each has formats, default_duration_min, max_capacity (<= 30), min_players

  Scenario: a 4th game needs only data
    Given a games file with an extra table "test_game"
    When the app starts with that file
    Then "test_game" can be used to create an event and register, with no code change

  Scenario: event survives its game being removed
    Given an event created for "test_game"
    When the app restarts with a games file without "test_game"
    Then the calendar and event page still show the event with game name "Test Game"
    And the event page still shows its min-players status from the snapshot
    And GET /events/new?game=test_game → 400 unknown game

  Scenario: invalid template file fails fast
    Given a game with max_capacity 0 or an empty formats list
    Then app startup raises a ValueError naming the game

Feature: Event creation
  Scenario: create a valid event
    When organizer POSTs name "Friday Night Magic", game mtg, format "Draft",
         date 2026-11-06, time 18:30, capacity 8, location default, duration blank
         timezone default (America/Los_Angeles)
    Then 302 to the event page
    And start_utc = 2026-11-07T02:30Z, end = start + mtg default duration

  Scenario: per-event timezone
    When the same form is posted with timezone "America/New_York"
    Then start_utc = 2026-11-06T23:30Z and the event page shows "18:30 EST"
  Scenario: invalid timezone "Mars/Olympus" → 400, nothing stored
  Scenario: DST gap 2026-03-08 02:30 America/Los_Angeles → 400 "does not exist", nothing stored
  Scenario: DST overlap 2026-11-01 01:30 America/Los_Angeles → 400 "ambiguous", nothing stored

  Scenario: capacity 30 accepted, 31 rejected (mtg max 30)
    Then 30 → created; 31 → 400 "Capacity must be between 1 and 30", nothing stored
  Scenario: capacity 0, negative, non-numeric → 400, nothing stored
  Scenario: unknown game → 400
  Scenario: format not in game's list (e.g. "Expanded" for Lorcana) → 400
  Scenario: blank name, bad date/time, blank location, duration <= 0 → 400 with message
  Scenario: form for game X prefills X's formats, max capacity and default duration (GET /events/new?game=X)

Feature: Calendar
  Scenario: events grouped by local day, sorted by start time
    Given events on Nov 6 18:30, Nov 6 12:00, Nov 8 10:00 (local)
    Then GET / shows a heading for Nov 6 with 12:00 before 18:30, then Nov 8
  Scenario: event late in local evening groups under its own local date, not UTC date
  Scenario: mixed timezones keep day headings in order
    Given a Nov 7 10:00 Asia/Tokyo event (UTC Nov 7 01:00) and a Nov 6 20:00
          America/Los_Angeles event (UTC Nov 7 04:00)
    Then the "Nov 6" heading comes before "Nov 7", each heading appears once
  Scenario: each entry shows name, game, time, registered/capacity, links to event page
  Scenario: no events → "No events scheduled"

Feature: Event page, invite, QR
  Scenario: event page shows details, "3 / 8 registered", min-players status, QR, .ics link
  Scenario: QR encodes the registration URL: BASE_URL when set, else http://<detected-ip>:8000
    (the detector is injected in tests; one test asserts the real detector returns a
     dotted IPv4 string and never raises)
  Scenario: .ics download
    When GET /events/<id>/invite.ics
    Then Content-Type text/calendar, attachment filename
    And parsing it yields one VEVENT with SUMMARY = event name, DTSTART/DTEND in UTC
        equal to stored times, LOCATION = event location, a stable UID
  Scenario: unknown event id → 404 for page, .ics and register

Feature: Registration (capacity-enforced on the server)
  Scenario: register with name → success page, count increments
  Scenario: event full → 409 "This event is full (8/8)", count unchanged
  Scenario: duplicate " alex  " after "Alex" → 409 "Alex is already registered", count unchanged
  Scenario: duplicate on a full event → 409 already-registered (duplicate wins)
  Scenario: blank / whitespace / >100-char name → 400, count unchanged
  Scenario: now >= start → 409 "Registration is closed", count unchanged (fixed clock in test)
  Scenario: registration form for a full event shows the full message, no form
  Scenario: last-seat race
    Given capacity 5 with 4 registered
    When 20 threads POST distinct names at the same time
    Then exactly 1 gets success, 19 get 409 full, and the DB count is 5 (repeated 20 times)
```

## Must NOT

- Registrations never exceed capacity (concurrency test + full-event test + mutant).
- Rejected registration (full, duplicate, closed, invalid) never changes the stored count.
- No hand-rolled QR or ICS (only the `qrcode` / `icalendar` libraries) — code review.
- Core event/registration code contains no game names or game-id branches — grep gate with negative control.
- Not built: auth, payments, email, recurring, edit/cancel, admin dashboard, waitlist.
- No `git push`, no branches, no `Co-Authored-By`.

## Gauntlet (Tier 2)

`tools/gauntlet.sh` runs: `ruff check`, `ruff format --check`, `mypy app`,
`pytest -p randomly --cov=app --cov-branch --cov-fail-under=100`, the grep gate,
and `tools/mutants.py` (≥5 mutants: capacity `<`→`<=`, drop name normalization, drop
format check, .ics end=start, drop registration-closed check, drop max-capacity check).
Plus `pip-audit -r requirements.txt` once, and a real run: start server, create → calendar
→ .ics → register to full via curl.
Manual, not automated: Google Calendar/Outlook import of the .ics, and a phone scan of
the QR. These are recorded in EVIDENCE as unverified unless the owner does them.
Skipped: mutmut, hypothesis (timebox).

## Revisions
- 2026-10-25 (pre-approval): added decision #12 and scenario "event survives its game
  being removed". The gap surfaced when the owner asked how easy adding a game is.
- 2026-10-25 (after approval #1, before any code): Codex review of SPEC.md found 2 issues,
  and reading the owner's DECISIONS.md found 1 more. Changes:
  - #12: also snapshot `min_players` (Codex: removed-game event page needs it).
  - #7: QR fallback was the request host. Now an auto-detected LAN IP, `:8000` (owner
    answer; Codex: a localhost request host isn't phone-reachable).
  - #4, #10: timezone is per event, prefilled from STORE_TZ (owner answer, resolving the
    "override" wording in DECISIONS.md). Calendar groups by each event's own tz.
  - Approval #1 covers the earlier text only; this version needs re-approval.
- 2026-10-25 (second Codex review, still pre-code):
  - #10: group by local date first, then sort (Codex: UTC-sorted grouping misorders
    headings across timezones). Added a mixed-timezone scenario.
  - #4: DST gap or overlap start times are rejected with 400 (owner answer to the Codex
    finding). Added 2 scenarios.
  - Git: DECISIONS.md is included in every commit while it has changes (owner instruction).
- 2026-10-25 (slice 1, implementation): grep gate is `tools/check_no_game_names.py`, not
  `.sh`. It reads forbidden ids/names from games.toml itself, so new games are covered
  automatically; parsing TOML in shell would be fragile. Same behaviour, fails closed.
- 2026-10-25 (slice 2, Codex finding): a basic event page (details, count, min-players
  status) moves from slice 4 into slice 2, so the post-create redirect never lands on a
  404. Slice 4 adds the QR and .ics to it. Also added: dates whose UTC start or end falls
  outside year 1..9999 → 400 "Enter a valid date and time" (was a 500).
- 2026-10-25 (slice 2, Codex findings): event page shows the end date when an event
  crosses midnight in its own tz. Validation also rejects events whose end can't be
  shown in local time (year-9999 edge), so creation never redirects to a crashing page.
- 2026-10-25 (owner instruction, mid slice 2): **commit authorization withdrawn.** From
  slice 2 on, each slice is staged, then Claude stops and waits for the owner's review
  and go-ahead before committing. Codex review still runs before staging is handed over.
- 2026-10-25 (before slice 4): slices 4 and 5 swap. Registration + capacity lands before
  QR + .ics, so the QR/registration link on the event page never points at a 404.
- 2026-10-25 (slice 5): fixed a conflict inside this spec. Decision #5 said the format
  goes in the .ics title, but the .ics scenario says SUMMARY = event name. Followed the
  scenario: SUMMARY is the event name; game and format go in DESCRIPTION, along with the
  registration link.
- 2026-10-25 (slice 7, real run): on the owner's machine LAN detection picked the VPN
  tunnel (utun7 10.2.0.2), not Wi-Fi (en0 10.0.0.101). Owner chose to keep detection and
  make the choice visible: the server prints the QR target at startup, and the event page
  hints at BASE_URL under the QR. Real-run reachability of LAN addresses can't be tested
  from Claude's sandbox (all non-loopback addresses time out), so `tools/real_run.py`
  checks the QR host equals the detected IP and follows the path via loopback.
