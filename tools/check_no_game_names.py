"""Fail if core app code mentions any game id or name from games.toml.

Guards the "no if/else on game names" rule. Limit: catches literal spellings only
(case-insensitive, word-bounded), not e.g. a game id assembled from substrings.
Fails closed: unreadable files, missing games or zero scanned files are errors.
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(games_file: Path, app_dir: Path) -> int:
    games = tomllib.loads(games_file.read_text())["games"]
    words = set(games) | {g["name"] for g in games.values()}
    if not words:
        print("FAIL: no game names loaded", file=sys.stderr)
        return 2
    pattern = re.compile("|".join(rf"(?<!\w){re.escape(w)}(?!\w)" for w in words), re.IGNORECASE)
    files = sorted(p for p in app_dir.rglob("*") if p.suffix in {".py", ".html"})
    if not files:
        print(f"FAIL: no source files under {app_dir}", file=sys.stderr)
        return 2
    hits = [
        f"{path}:{n}: {line.strip()}"
        for path in files
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if pattern.search(line)
    ]
    for hit in hits:
        print(hit, file=sys.stderr)
    print(f"scanned {len(files)} files for {len(words)} game words: {len(hits)} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    games_file = Path(args[0]) if args else ROOT / "games.toml"
    app_dir = Path(args[1]) if len(args) > 1 else ROOT / "app"
    sys.exit(main(games_file, app_dir))
