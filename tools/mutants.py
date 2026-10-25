"""Manual mutation runner: each mutant is a plausible bug the suite must kill.

Proves each mutant executed: the original text must occur exactly once (so the
edit really applied), the file is restored byte-for-byte afterwards and checked.
A kill counts only when pytest exits 1 (tests failed); a collection/usage error
(exit 2+) is a broken mutant, not a kill. Any problem fails the run.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (file, original, mutated, description)
MUTANTS: list[tuple[str, str, str, str]] = [
    (
        "app/games.py",
        "if not isinstance(name, str) or not name.strip():",
        "if not name:",
        "template name type check dropped",
    ),
    (
        "app/games.py",
        "if min_players > max_capacity:",
        "if min_players > max_capacity + 1:",
        "min_players bound off by one",
    ),
    (
        "app/games.py",
        "if not isinstance(raw, dict):",
        "if False:",
        "non-table game entry check dropped",
    ),
    (
        "app/events.py",
        'capacity = _int_in_range(form.get("capacity", ""), 1, game.max_capacity)',
        'capacity = _int_in_range(form.get("capacity", ""), 1, 30)',
        "capacity ceiling hardcoded instead of template max",
    ),
    (
        "app/events.py",
        "if fmt not in game.formats:",
        "if not fmt:",
        "format not checked against the game's list",
    ),
    (
        "app/events.py",
        "    if early != late:",
        "    if False:",
        "DST gap/overlap silently accepted",
    ),
    (
        "app/events.py",
        "end = start + timedelta(minutes=duration or 0)",
        "end = start + timedelta(minutes=game.default_duration_min)",
        "duration override ignored",
    ),
    (
        "app/events.py",
        "except OverflowError:  # end (UTC or local) runs past year 9999",
        "except ZeroDivisionError:  # end (UTC or local) runs past year 9999",
        "end-time overflow surfaces as a 500",
    ),
    (
        "app/views.py",
        "    if event is None:\n        abort(404)\n    return event",
        "    return event",
        "unknown event id not a 404",
    ),
    (
        "app/events.py",
        "        end.astimezone(ZoneInfo(tz_name))  # the page shows end in local time\n",
        "",
        "local end-time range not checked",
    ),
    (
        "app/events.py",
        'days.setdefault(_local(event["start_utc"], event["tz"]).date(), [])',
        'days.setdefault(parse_iso_utc(event["start_utc"]).date(), [])',
        "calendar groups by UTC date, not the event's local date",
    ),
    (
        "app/events.py",
        "for d in sorted(days)]",
        "for d in days]",
        "calendar day headings not sorted",
    ),
    (
        "app/events.py",
        'for event in sorted(events, key=lambda e: str(e["start_utc"])):',
        "for event in events:",
        "events within a day not sorted by start",
    ),
    (
        "app/registrations.py",
        'db.execute("BEGIN IMMEDIATE")',
        'db.execute("BEGIN")',
        "seat check not under the write lock (last-seat race)",
    ),
    (
        "app/registrations.py",
        'if event["registered"] >= event["capacity"]:',
        'if event["registered"] > event["capacity"]:',
        "capacity check off by one (overbooks by one)",
    ),
    (
        "app/registrations.py",
        "        if existing is not None:\n",
        "        if False:\n",
        "duplicate check dropped (UNIQUE backstop only)",
    ),
    (
        "app/registrations.py",
        "        if closed:\n",
        "        if False:\n",
        "registration allowed after start",
    ),
    (
        "app/registrations.py",
        "(event_id, name, name.casefold(), now.isoformat())",
        "(event_id, name, name, now.isoformat())",
        "duplicate key not case-normalized",
    ),
    (
        "app/registrations.py",
        'name = " ".join(raw.split())',
        "name = raw",
        "whitespace not normalized",
    ),
    (
        "app/registrations.py",
        '    db.execute("BEGIN IMMEDIATE")\n    try:\n        now = clock()\n',
        '    now = clock()\n    db.execute("BEGIN IMMEDIATE")\n    try:\n',
        "clock read before taking the write lock",
    ),
    (
        "app/views.py",
        "qr=Markup(qr_svg(url))",
        'qr=Markup(qr_svg(current_app.config["BASE_URL"]))',
        "QR encodes the site root, not the registration link",
    ),
    (
        "app/__init__.py",
        '    if not app.config["BASE_URL"]:\n',
        "    if True:\n",
        "BASE_URL setting ignored",
    ),
    (
        "app/views.py",
        'base: str = current_app.config["BASE_URL"].rstrip("/")',
        'base: str = current_app.config["BASE_URL"]',
        "trailing slash in BASE_URL gives a // link",
    ),
    (
        "app/qr.py",
        '        return "127.0.0.1"',
        '        return ""',
        "no-network fallback broken",
    ),
    (
        "app/invite.py",
        'vevent.add("dtend", parse_iso_utc(event["end_utc"]))',
        'vevent.add("dtend", parse_iso_utc(event["start_utc"]))',
        ".ics end equals start",
    ),
    (
        "app/invite.py",
        'vevent.add("uid", f"{event[\'uid\']}@game-events")',
        'vevent.add("uid", "event@game-events")',
        ".ics UID not unique per event",
    ),
    (
        "app/invite.py",
        'vevent.add("location", event["location"])',
        'vevent.add("location", "")',
        ".ics location missing",
    ),
    (
        "app/events.py",
        "            str(uuid.uuid4()),\n",
        "            str(event.start),\n",
        "event uid not random (collides across databases)",
    ),
    (
        "seed.py",
        '        if db.execute("SELECT count(*) FROM events").fetchone()[0]:\n',
        "        if False:\n",
        "seed duplicates demo data on a second run",
    ),
    (
        "app/events.py",
        "            event.game.name,\n",
        "            event.game.id,\n",
        "game display name not snapshotted on the event",
    ),
    (
        "app/events.py",
        "            event.game.min_players,\n",
        "            4,\n",
        "min_players not snapshotted from the template",
    ),
    (
        "app/events.py",
        '    game = games.get(form.get("game", ""))\n',
        '    game = games.get(form.get("game", "")) if len(form.get("game", "")) < 8 else None\n',
        "core logic only accepts the games it already knows",
    ),
]


def run_one(rel: str, original: str, mutated: str) -> int:
    path = ROOT / rel
    source = path.read_bytes()
    text = source.decode()
    if text.count(original) != 1:
        raise SystemExit(f"FAIL: {rel}: original text found {text.count(original)}x, not 1")
    try:
        path.write_text(text.replace(original, mutated))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-x",
                "-q",
                "-p",
                "no:randomly",
                "-p",
                "no:cacheprovider",
            ],
            cwd=ROOT,
            capture_output=True,
        )
        return result.returncode
    finally:
        path.write_bytes(source)
        if path.read_bytes() != source:
            raise SystemExit(f"FAIL: {rel} not restored")


def main() -> int:
    survivors = 0
    for rel, original, mutated, desc in MUTANTS:
        code = run_one(rel, original, mutated)
        if code == 1:
            print(f"killed   {desc}")
        else:
            survivors += 1
            print(f"SURVIVED {desc} (pytest exit {code})")
    print(f"{len(MUTANTS) - survivors}/{len(MUTANTS)} mutants killed")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
