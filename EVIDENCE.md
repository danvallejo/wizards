# Evidence Report: Event Calendar (Tier 2 + concurrency test)

- **Spec approval:** obtained from the repo owner ("approved", twice: the second time for
  the revision after Codex's first spec review). Spec: `SPEC.md`, committed in `328e7fb`.
  Later changes are listed in its `## Revisions` section.
- **Source state:** git tree `6e540c2e843e61e5d839a248b7cd0a99ce6bcf8a` = commit
  `6b76dab` plus the slice-7 changes (startup QR message, `tools/real_run.py`, seed in the
  gauntlet). It is committed as the commit just before the one adding this file; check it
  with `git rev-parse HEAD~1^{tree}` from the commit that adds this file. This file itself
  is not part of the checked tree. The working tree had no unstaged or untracked files.
- **Run at:** 2026-10-25T19:37:08Z, on macOS (Darwin 25.6.0) with Python 3.14.7.
- **Toolchain:** exact pins in `requirements.txt` / `requirements-dev.txt` (Flask 3.1.3,
  qrcode 8.2, icalendar 7.3.0, pytest 9.1.1, pytest-cov 7.1.0, pytest-randomly 5.0.0,
  mypy 2.4.0, ruff 0.17.2, pip-audit 2.10.1). Reviewer: codex-cli 0.163.0.
- **Entry point:** `tools/gauntlet.sh` runs every layer below except `pip-audit`, which
  needs the network. To repeat a test order: `SEED=6779 tools/gauntlet.sh`.
- **Independent verification:** not performed (Tier 2). Codex reviewed every commit's
  staged diff before it was made. That is a second model reading the code, not a
  fresh-context verifier attacking the finished work.

## Spec → test mapping

All rows are from the final run. Test files are under `tests/`.

| Scenario (SPEC.md) | Test | Status |
|---|---|---|
| Templates load from games.toml | `test_games.py::test_shipped_templates_load`, `::test_loads_all_fields` | pass |
| A 4th game needs only data | `test_template_extensibility.py::test_fourth_game_needs_only_data` | pass |
| Event survives its game being removed | `test_template_extensibility.py::test_event_survives_its_game_being_removed` | pass |
| Invalid template file fails fast | `test_games.py::test_invalid_template_fails_naming_game` (13 cases), `::test_no_games_fails`, `::test_non_table_game_entry_fails_naming_game` | pass |
| Create a valid event | `test_create_event.py::test_create_valid_event`, `::test_redirects_to_event_page`, `::test_duration_override` | pass |
| Per-event timezone | `test_create_event.py::test_per_event_timezone`, `test_event_page.py::test_event_page_shows_own_timezone` | pass |
| Invalid timezone; DST gap; DST overlap → 400 | `test_create_event.py::test_invalid_event_rejected` (cases for each) | pass |
| Capacity 30 accepted, 31 rejected | `test_create_event.py::test_capacity_at_template_max_accepted`, `::test_invalid_event_rejected`, `::test_capacity_max_comes_from_template` | pass |
| Capacity 0 / negative / non-numeric; unknown game; bad format; blank name, bad date/time, blank location, bad duration → 400 | `test_create_event.py::test_invalid_event_rejected` (27 cases), `::test_missing_fields_rejected` | pass |
| Form prefills from template | `test_create_event.py::test_new_event_form_prefills_from_template`, `::test_new_event_without_game_lists_games`, `::test_new_event_unknown_game_is_400` | pass |
| Calendar grouped by day, sorted | `test_calendar.py::test_grouped_by_day_and_sorted_by_time` | pass |
| Late evening groups under local date | `test_calendar.py::test_late_evening_groups_under_local_date` | pass |
| Mixed timezones keep headings in order | `test_calendar.py::test_mixed_timezones_keep_headings_in_order` | pass |
| Entry shows summary, links to event | `test_calendar.py::test_entry_shows_summary_and_links_to_event` | pass |
| No events → "No events scheduled" | `test_calendar.py::test_no_events` | pass |
| Event page details, count, min-players status, QR, .ics link | `test_event_page.py::*`, `test_registration.py::test_min_players_status_flips_when_reached`, `test_invite_and_qr.py::test_event_page_links_invite` | pass |
| QR encodes the registration URL | `test_invite_and_qr.py::test_qr_encodes_detected_lan_url_by_default`, `::test_qr_uses_base_url_when_set`, `::test_detected_ip_is_used_at_startup`, `::test_detect_lan_ip_*`, `::test_startup_prints_*` | pass |
| .ics download | `test_invite_and_qr.py::test_ics_headers`, `::test_ics_content`, `::test_ics_uid_is_stable_and_unique`, `::test_ics_uid_unique_across_databases`, `::test_ics_times_use_utc` | pass |
| Unknown event id → 404 (page, .ics, register) | `test_event_page.py::test_unknown_event_is_404`, `test_invite_and_qr.py::test_ics_unknown_event_404`, `test_registration.py::test_register_unknown_event_404` | pass |
| Register → success page, count increments | `test_registration.py::test_register_success`, `::test_event_page_counts_registrations_and_links_form` | pass |
| Event full → 409, count unchanged | `test_registration.py::test_full_event_rejected`, `::test_rejected_post_on_full_event_hides_form` | pass |
| Duplicate (normalized) → 409, count unchanged | `test_registration.py::test_duplicate_name_rejected` (4 spellings), `::test_same_name_allowed_on_different_events` | pass |
| Duplicate on a full event → already-registered | `test_registration.py::test_duplicate_on_full_event_reports_duplicate` | pass |
| Blank / whitespace / >100-char name → 400 | `test_registration.py::test_invalid_name_rejected`, `::test_missing_name_field_rejected`, `::test_name_of_exactly_100_chars_accepted` | pass |
| now ≥ start → 409 closed | `test_registration.py::test_registration_closed_once_started`, `::test_registration_open_one_minute_before_start`, `::test_clock_is_read_while_holding_the_write_lock` | pass |
| Form for a full event shows message, no form | `test_registration.py::test_register_form_for_full_event_shows_message_not_form`, `::test_register_form_for_started_event_shows_closed` | pass |
| Last-seat race | `test_concurrency.py::test_last_seat_race_has_exactly_one_winner` (20 threads × 20 rounds) | pass |
| **Must NOT:** registrations exceed capacity | race test + full-event tests + mutants 14, 15 | pass |
| **Must NOT:** rejected registration changes the count | count asserted in full / duplicate / closed / invalid tests | pass |
| **Must NOT:** hand-rolled QR or ICS | `app/qr.py` uses `qrcode`, `app/invite.py` uses `icalendar`; checked by code review only, no automated gate | unverified (review only) |
| **Must NOT:** game names or game-id branches in core | `tools/check_no_game_names.py` (0 hits, 16 files) + mutant 32 | pass |
| **Must NOT:** auth, payments, email, recurring, edit/cancel, admin, waitlist | none of these routes exist (`app/views.py` has 7 routes, all for features in the spec) | pass (by inspection) |
| **Must NOT:** push, branches, `Co-Authored-By` | `main` is the only local branch; 0 `Co-Authored-By` lines in `git log`; `origin/main` is still `4d758b5` (nothing pushed) | pass |

## Gauntlet (final fresh run)

| Layer | Command | Result |
|---|---|---|
| Lint | `ruff check .` | All checks passed |
| Format | `ruff format --check .` | 27 files already formatted |
| Types | `mypy` (strict, `app` + `seed`) | Success: no issues found in 10 source files |
| Tests | `pytest -p randomly --randomly-seed=6779` | 118 passed, 0 failed (3.13 s) |
| Coverage | `--cov=app --cov=seed --cov-branch --cov-fail-under=100` | 356/356 statements, 70/70 branches, 100%. All code is new, so changed-line coverage is the same thing |
| No game names in core | `tools/check_no_game_names.py` | scanned 16 files for 6 game words: 0 hits |
| Mutation | `tools/mutants.py` (manual, 32 hand-written mutants) | 32/32 killed |
| Real execution | `tools/real_run.py` | REAL RUN PASSED (13 checks, listed below) |
| Supply chain | `pip-audit -r requirements.txt` | No known vulnerabilities found (exit 0). Runtime licenses: BSD (Flask, Werkzeug, Jinja2, itsdangerous, click, MarkupSafe, qrcode, icalendar), MIT (blinker, six), Apache-2.0 (tzdata), dual (python-dateutil) |
| Secrets | `git ls-files -z \| xargs -0 grep -nIiE "(api[_-]?key\|secret\|password\|token\|BEGIN … PRIVATE)"` | no matches |
| Suite health | random order on every gauntlet run; race test repeated 5× separately | stable; no flaky failures seen |

New dependencies, each justified in `SPEC.md`: `flask`, `qrcode`, `icalendar` (runtime);
pytest, pytest-cov, pytest-randomly, mypy, ruff, pip-audit (dev). New capabilities: a
SQLite file (`instance/events.db`); a UDP `connect()` at startup to choose the LAN IP,
which sends no packets; the dev server listening on `0.0.0.0:8000`.

**Real run checks:** calendar starts empty; create form prefilled from the template;
event created and redirected to its page; page shows the LAN registration URL and an SVG
QR; event appears on the calendar under its local date; `.ics` parses with the right
summary, UTC start/end and location; the QR host is the detected IP; the registration
form is served at the QR's path; register → 201; duplicate → 409; fill → 201; full →
409 "This event is full (2/2)"; page shows "2 / 2 registered".

**Mutants (all killed):** 1 template name type check dropped · 2 min_players bound off
by one · 3 non-table game entry accepted · 4 capacity ceiling hardcoded to 30 · 5 format
not checked · 6 DST gap/overlap accepted · 7 duration override ignored · 8 end-time
overflow → 500 · 9 unknown event not 404 · 10 local end-time range not checked ·
11 calendar groups by UTC date · 12 day headings unsorted · 13 events in a day unsorted ·
14 seat check not under write lock · 15 capacity check off by one · 16 duplicate check
dropped · 17 registration after start · 18 duplicate key not case-folded · 19 whitespace
not normalized · 20 clock read before lock · 21 QR encodes site root · 22 BASE_URL
ignored · 23 trailing slash gives `//` · 24 no-network fallback broken · 25 .ics end =
start · 26 .ics UID not per event · 27 .ics location missing · 28 event uid not random ·
29 seed duplicates on second run · 30 game name not snapshotted · 31 min_players not
snapshotted · 32 core accepts only known games.

## Negative controls (each checker shown to fail on a known-bad input)

| Checker | Known-bad input | Result |
|---|---|---|
| Game-name gate | `"MTG"` in a `.py`; `Disney Lorcana` in an `.html`; an empty directory | exit 1, exit 1, exit 2; `smtg` correctly ignored (exit 0) |
| Format layer | an unformatted file | gauntlet stopped at "format" |
| Coverage gate | one test deselected | exit 1 at 95.35% |
| Mutation runner | a comment-only (equivalent) mutant; a mutant whose original text is absent | exit 1 ("SURVIVED"); exit 1 ("found 0x") |
| Warnings-as-errors | the unclosed sqlite connection (a real bug) | suite failed until fixed |
| Race test | deferred `BEGIN`; no transaction at all | losers got 500s; 18/20 won, overbooking capacity 5 to 22 |
| Real run | capacity check off by one; a non-HTTP listener already on :8000 | exit 1 at "full event rejected"; exit 1 "port 8000 already in use" |

The deferred-`BEGIN` control is permanent (mutant 14). The no-transaction control needs
three edits, which the single-replacement runner can't apply, so it was run once by hand.

## Layers not run as specified

- **N-A:** API-compatibility, migration rehearsal (no public API, no prior release).
- **UNAVAILABLE:** a mutation tool (mutmut) and property-based tests (hypothesis). Both
  were skipped for the 3-hour timebox, as the spec says; nothing ran in their place.
- **SUBSTITUTED:**
  - *QR correctness:* tests rebuild the QR from the expected URL and require an exact
    match. No decoder (zbar) is installed, so this can't catch a bug inside the `qrcode`
    library itself.
  - *.ics import:* tests parse the file back with `icalendar`. This doesn't show that
    Google Calendar or Outlook accept it.
  - *LAN reachability:* every non-loopback address timed out from Claude's command
    sandbox, so the real run follows the QR's path through `127.0.0.1` and checks only
    that the QR's host is the detected IP.

**Manual checks for the owner (not done):**
1. Scan an event's QR with a phone on the same Wi-Fi (with `BASE_URL` set if a VPN is on).
2. Import a downloaded `.ics` into Google Calendar and Outlook.

## Dismissed review findings

- *Codex: "the 100% branch-coverage gate cannot pass"* (slice 1). Disproved by running
  it: the gauntlet passed at 100% before any change. The useful part (two untested
  validation cases) became tests.
- *Codex P1: migrate existing databases when the `uid` column was added* (slice 5).
  Dismissed by the owner: no database has ever been deployed. The README tells users to
  delete `instance/events.db` after a schema change.

## Structural blind spot

Nothing here exercises a production deployment: the Flask development server, a single
SQLite writer, and one machine. The concurrency evidence is threads in one process
sharing one SQLite file. It says nothing about several app servers or another database.

## Honest notes

- **Two approved scenarios had no tests until slice 6** (4th game end to end; event
  outliving its removed game). The README draft wrongly called the first one tested.
  Found by checking every spec scenario against the tests; both tests were added and
  backed by mutants 30–32.
- **Codex raised 23 findings across the run: 21 fixed (app behaviour bugs with a failing
  test first; tooling, template and doc fixes directly), 2 dismissed (above).** Fixed: spec gaps (min_players snapshot, DST, calendar order, QR
  fallback), non-table template entries, gauntlet skipping the mutation layer, redirect
  to a missing page, year-9999 crashes (×2), midnight end date, a broken nav link,
  clock read before the lock, form shown after rejection,
  double message, `.ics` UID collisions, half-seeded database, weekday-named demo event,
  real-run time bomb, `--no-reload`, port guard, isolation from app settings.
- **The real run found a real environment issue:** on the dev machine, LAN detection
  picks the VPN tunnel (`utun7` 10.2.0.2), not Wi-Fi (`en0` 10.0.0.101). The owner chose
  to keep detection and make it visible: the server prints the QR target at startup and
  the event page hints at `BASE_URL` (see SPEC revisions).
- **Commit authorization changed partway through:** commits 1–2 were made under an
  up-front authorization; from slice 2 on, the owner reviewed each staged commit first.
- **Spec revisions** are all recorded in `SPEC.md`: slice reorders (event page into
  slice 2; registration before QR/.ics), grep gate written in Python, the `.ics` title
  conflict inside the spec, the commit-policy change, and the LAN-detection visibility.
