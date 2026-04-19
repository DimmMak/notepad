"""`.notepad` — Bulletpoint logbook CLI.

Subcommands:
    (default)   → show last 20 entries
    add <text> [#tag ...]  → append a timestamped bullet
    today       → show entries from today
    yesterday   → show entries from yesterday
    week        → show last 7 days
    search <term>          → grep entries
    tag <name>  → filter by tag
    tags        → list all unique tags + counts
    stats       → quick metrics

Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from collections import Counter
from typing import Iterable

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, ROOT)

from scripts.lib import note_io  # noqa: E402


LOG_PATH = os.path.join(ROOT, "notes", "log.md")


# ───────────────────────── helpers ─────────────────────────

def _extract_tags(args_tokens: list[str]) -> tuple[str, list[str]]:
    """Split CLI tokens into text + tags.

    Tokens starting with '#' are tags. Everything else is text.
    Works whether user says:
        .notepad add "pizza idea" #food #ideas
        .notepad add pizza idea #food #ideas
    """
    text_parts: list[str] = []
    tags: list[str] = []
    for t in args_tokens:
        if t.startswith("#") and len(t) > 1:
            tags.append(t[1:])
        else:
            text_parts.append(t)
    return " ".join(text_parts).strip(), tags


def _render_entries(entries: Iterable[dict]) -> str:
    """Render parsed entries back to their raw form, one per line."""
    lines = [e["raw"] for e in entries]
    if not lines:
        return "_(no matching entries)_"
    return "\n".join(lines)


def _in_date_range(entry: dict, start: dt.datetime, end: dt.datetime) -> bool:
    iso = entry.get("iso")
    if not isinstance(iso, dt.datetime):
        return False
    return start <= iso < end


# ───────────────────────── subcommands ─────────────────────

def cmd_add(tokens: list[str]) -> int:
    text, tags = _extract_tags(tokens)
    if not text:
        print("usage: .notepad add <text> [#tag1 #tag2 ...]", file=sys.stderr)
        return 1
    line = note_io.append_entry(text, tags, log_path=LOG_PATH)
    print("🗒️  Added:")
    print(line)
    return 0


def cmd_recent(n: int = 20) -> int:
    entries = list(note_io.iter_entries(LOG_PATH))
    recent = entries[-n:]
    print(f"# 🗒️ .notepad — last {len(recent)} entries\n")
    print(_render_entries(recent))
    return 0


def cmd_today() -> int:
    now = dt.datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=1)
    matches = [e for e in note_io.iter_entries(LOG_PATH) if _in_date_range(e, start, end)]
    print(f"# 🗒️ Today ({start.date().isoformat()}) — {len(matches)} entries\n")
    print(_render_entries(matches))
    return 0


def cmd_yesterday() -> int:
    now = dt.datetime.now().astimezone()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today_start - dt.timedelta(days=1)
    end = today_start
    matches = [e for e in note_io.iter_entries(LOG_PATH) if _in_date_range(e, start, end)]
    print(f"# 🗒️ Yesterday ({start.date().isoformat()}) — {len(matches)} entries\n")
    print(_render_entries(matches))
    return 0


def cmd_week() -> int:
    now = dt.datetime.now().astimezone()
    start = (now - dt.timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now + dt.timedelta(minutes=1)
    matches = [e for e in note_io.iter_entries(LOG_PATH) if _in_date_range(e, start, end)]
    print(f"# 🗒️ Last 7 days — {len(matches)} entries\n")
    print(_render_entries(matches))
    return 0


def cmd_search(term: str) -> int:
    term_lower = term.lower()
    matches = [e for e in note_io.iter_entries(LOG_PATH) if term_lower in e["text"].lower()]
    print(f"# 🔎 .notepad search '{term}' — {len(matches)} matches\n")
    print(_render_entries(matches))
    return 0


def cmd_tag(name: str) -> int:
    name = note_io.normalize_tag(name) or name.lstrip("#").lower()
    matches = [e for e in note_io.iter_entries(LOG_PATH) if name in e["tags"]]
    print(f"# 🏷️  .notepad tag #{name} — {len(matches)} entries\n")
    print(_render_entries(matches))
    return 0


def cmd_tags() -> int:
    counter: Counter = Counter()
    for e in note_io.iter_entries(LOG_PATH):
        counter.update(e["tags"])
    if not counter:
        print("_(no tags yet)_")
        return 0
    print(f"# 🏷️  All tags — {len(counter)} unique\n")
    print("| 🟣 Tag | 🟣 Count |")
    print("| ------ | -------- |")
    for tag, n in counter.most_common():
        print(f"| #{tag} | {n} |")
    return 0


def cmd_stats() -> int:
    entries = list(note_io.iter_entries(LOG_PATH))
    if not entries:
        print("# 📊 .notepad stats\n\n_(no entries yet)_")
        return 0
    total = len(entries)
    bytes_ = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
    days: Counter = Counter()
    for e in entries:
        days[e["date"]] += 1
    most_day, most_count = days.most_common(1)[0]
    oldest = entries[0]["iso"]
    newest = entries[-1]["iso"]
    unique_tags = len({t for e in entries for t in e["tags"]})
    print("# 📊 .notepad stats\n")
    print("| 🟣 Metric | 🟣 Value |")
    print("| --------- | -------- |")
    print(f"| Total entries | {total} |")
    print(f"| File size | {bytes_} bytes |")
    print(f"| Oldest | {oldest.isoformat()} |")
    print(f"| Newest | {newest.isoformat()} |")
    print(f"| Unique tags | {unique_tags} |")
    print(f"| Busiest day | {most_day} ({most_count}) |")
    print(f"| Days with entries | {len(days)} |")
    return 0


# ───────────────────────── dispatch ────────────────────────

def run(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    # No args → show recent.
    if not argv:
        return cmd_recent()

    # First positional might be a subcommand or free text.
    sub = argv[0]
    rest = argv[1:]

    if sub in ("add",):
        return cmd_add(rest)
    if sub in ("today",):
        return cmd_today()
    if sub in ("yesterday",):
        return cmd_yesterday()
    if sub in ("week", "7d"):
        return cmd_week()
    if sub == "search" and rest:
        return cmd_search(" ".join(rest))
    if sub == "tag" and rest:
        return cmd_tag(rest[0])
    if sub == "tags":
        return cmd_tags()
    if sub == "stats":
        return cmd_stats()

    # Anything else → treat entire argv as free text to add.
    # Supports the one-liner UX: `.notepad pizza idea #food`
    return cmd_add(argv)


if __name__ == "__main__":
    raise SystemExit(run())
