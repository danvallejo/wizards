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
        '    if event is None:\n        abort(404)\n    return render_template("event.html"',
        '    return render_template("event.html"',
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
