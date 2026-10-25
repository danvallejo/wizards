"""Real execution: start the actual server and walk the end-to-end flow over HTTP.

create event -> calendar -> .ics -> follow the QR's registration path -> register until
full -> duplicate -> full rejection. Uses a throwaway database. Fails closed: any
unexpected status or content exits nonzero.
"""

import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from datetime import time as dt_time
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.qr import detect_lan_ip  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOCAL = "http://127.0.0.1:8000"
LA = ZoneInfo("America/Los_Angeles")


def fetch(url: str, form: dict[str, str] | None = None) -> tuple[int, str]:
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def check(label: str, ok: bool) -> None:
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        raise SystemExit(1)


def walk() -> None:
    # 30 days out, so the event is always open; expectations computed independently.
    day = datetime.now(LA).date() + timedelta(days=30)
    start = datetime.combine(day, dt_time(18, 0), LA).astimezone(UTC)
    heading = f"{day:%a %b} {day.day}, {day.year}"
    status, html = fetch(f"{LOCAL}/")
    check("calendar starts empty", status == 200 and "No events scheduled" in html)

    status, html = fetch(f"{LOCAL}/events/new?game=lorcana")
    check("create form prefilled from template", status == 200 and 'max="24"' in html)

    status, html = fetch(
        f"{LOCAL}/events",
        {
            "name": "Real Run Sealed",
            "game": "lorcana",
            "format": "Sealed",
            "date": day.isoformat(),
            "time": "18:00",
            "timezone": "America/Los_Angeles",
            "duration_min": "",
            "capacity": "2",
            "location": "Back Room, 1 Elm St",
        },
    )
    check("event created, redirected to its page", status == 200 and "0 / 2 registered" in html)
    match = re.search(r"http://[\d.]+:8000/events/(\d+)/register", html)
    check("page shows LAN registration URL", match is not None and "<svg" in html)
    assert match is not None
    reg_url, event_id = match.group(0), match.group(1)
    print(f"     registration URL: {reg_url}")

    status, html = fetch(f"{LOCAL}/")
    check("event on calendar", "Real Run Sealed" in html and heading in html)

    with urllib.request.urlopen(f"{LOCAL}/events/{event_id}/invite.ics", timeout=10) as resp:
        [vevent] = Calendar.from_ical(resp.read()).walk("VEVENT")
    check(
        ".ics parses with correct fields",
        str(vevent["SUMMARY"]) == "Real Run Sealed"
        and vevent.decoded("DTSTART") == start
        and vevent.decoded("DTEND") == start + timedelta(minutes=150)  # Lorcana default
        and str(vevent["LOCATION"]) == "Back Room, 1 Elm St",
    )

    check(
        "QR host is this machine's detected LAN IP",
        reg_url.startswith(f"http://{detect_lan_ip()}:8000/"),
    )
    # Follow the QR's path via loopback: LAN reachability needs a real phone on the
    # same network (and some sandboxes block non-loopback addresses).
    reg_url = LOCAL + urllib.parse.urlsplit(reg_url).path
    status, html = fetch(reg_url)
    check("registration form served at the QR path", status == 200 and 'name="name"' in html)

    check("register Alex", fetch(reg_url, {"name": "Alex"})[0] == 201)
    status, html = fetch(reg_url, {"name": " alex "})
    check("duplicate rejected", status == 409 and "Alex is already registered" in html)
    check("register Sam (fills event)", fetch(reg_url, {"name": "Sam"})[0] == 201)
    status, html = fetch(reg_url, {"name": "Jo"})
    check("full event rejected", status == 409 and "This event is full (2/2)" in html)
    status, html = fetch(f"{LOCAL}/events/{event_id}")
    check("page shows 2 / 2 registered", "2 / 2 registered" in html)


def main() -> None:
    with socket.socket() as probe:  # any listener counts, whatever it answers
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise SystemExit("FAIL port 8000 already in use; stop that server first")
    with tempfile.TemporaryDirectory() as tmp:
        # run on the repo defaults, whatever the developer's app settings are
        app_settings = {"BASE_URL", "GAMES_FILE", "STORE_TZ", "STORE_LOCATION", "DATABASE"}
        env = {k: v for k, v in os.environ.items() if k not in app_settings}
        env["DATABASE"] = f"{tmp}/real-run.db"
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "flask",
                "--app",
                "app",
                "run",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--no-reload",  # a reloader child would outlive terminate()
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(f"{LOCAL}/", timeout=1)
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                raise SystemExit("FAIL server did not start")
            walk()
        finally:
            server.terminate()
            server.wait(timeout=10)
    print("REAL RUN PASSED")


if __name__ == "__main__":
    main()
