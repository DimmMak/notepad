"""Safe note I/O for .notepad.

Append-only log operations. Pure functions for parsing + writing
bulletpoint entries per SCHEMA.md. Stdlib only.

Key contracts:
- append_entry(text, tags) → writes one bullet, returns the line
- parse_entry(line) → dict | None (None on malformed, never raises)
- iter_entries(path) → yield parsed dicts, skip malformed with warn

Invariants:
- I1: file is only ever appended to.
- I2: one entry per line (newlines in text escaped).
- I5: past entries never rewritten.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
from typing import Iterable, Optional


# Where log.md lives — set by caller, defaults to the skill's notes/ dir.
DEFAULT_LOG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "notes", "log.md")
)


# Regex matches:
#   - **YYYY-MM-DD HH:MM** · text · `#tag`... · _iso:...YYYY-MM-DDTHH:MM:SS±HH:MM_
# Tags block is optional. Text must not contain newlines (we escape them).
_ENTRY_RE = re.compile(
    r"^\-\s+"
    r"\*\*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\*\*\s*·\s*"     # date + time
    r"(.+?)"                                                   # text (non-greedy)
    r"(?:\s*·\s*((?:`#[a-z0-9-]+`\s*)+))?"                    # optional tags block
    r"\s*·\s*_iso:([^_]+)_\s*$",                              # iso timestamp
)

_TAG_IN_BLOCK_RE = re.compile(r"`#([a-z0-9-]+)`")
_VALID_TAG_RE = re.compile(r"^[a-z0-9-]{1,30}$")


def _local_now() -> dt.datetime:
    """Return timezone-aware local time."""
    return dt.datetime.now().astimezone()


def _escape_text(text: str) -> str:
    """Single-line-safe text. Newlines → \\n literal."""
    if text is None:
        return ""
    # Collapse CR/LF to \n literal so the entry stays one line.
    return str(text).replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n").strip()


def normalize_tag(tag: str) -> Optional[str]:
    """Lowercase, strip leading '#', validate format. Returns None if invalid."""
    if tag is None:
        return None
    t = str(tag).strip().lstrip("#").lower()
    if not _VALID_TAG_RE.match(t):
        return None
    return t


def format_entry(
    text: str,
    tags: Iterable[str] = (),
    *,
    now: Optional[dt.datetime] = None,
) -> str:
    """Format a single entry line per SCHEMA.md. Does NOT write to disk."""
    moment = (now or _local_now()).astimezone()
    date_s = moment.strftime("%Y-%m-%d %H:%M")
    iso_s = moment.isoformat(timespec="seconds")
    clean_text = _escape_text(text)

    # Filter + dedupe tags while preserving order.
    norm_tags: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        t = normalize_tag(raw)
        if t and t not in seen:
            seen.add(t)
            norm_tags.append(t)

    parts = [f"- **{date_s}** · {clean_text}"]
    if norm_tags:
        tag_block = " ".join(f"`#{t}`" for t in norm_tags)
        parts.append(tag_block)
    parts.append(f"_iso:{iso_s}_")

    return " · ".join(parts)


def append_entry(
    text: str,
    tags: Iterable[str] = (),
    *,
    log_path: str = DEFAULT_LOG,
    now: Optional[dt.datetime] = None,
) -> str:
    """Append one entry to the log file. Returns the line that was written."""
    line = format_entry(text, tags, now=now)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def parse_entry(line: str) -> Optional[dict]:
    """Parse one log line. Returns dict or None (never raises)."""
    if not line or not isinstance(line, str):
        return None
    m = _ENTRY_RE.match(line.strip())
    if not m:
        return None
    date_s, time_s, text, tag_block, iso_s = m.groups()
    tags = _TAG_IN_BLOCK_RE.findall(tag_block or "")
    try:
        parsed_iso = dt.datetime.fromisoformat(iso_s)
    except ValueError:
        return None
    return {
        "date": date_s,
        "time": time_s,
        "text": text.strip(),
        "tags": tags,
        "iso": parsed_iso,
        "raw": line.rstrip("\n"),
    }


def iter_entries(log_path: str = DEFAULT_LOG) -> Iterable[dict]:
    """Yield parsed entries from the log. Skip malformed lines with warning."""
    if not os.path.exists(log_path):
        return
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for ln, raw in enumerate(f, start=1):
                raw = raw.rstrip("\n")
                if not raw.strip():
                    continue
                entry = parse_entry(raw)
                if entry is None:
                    print(f"[note_io] WARN {log_path}:{ln} malformed entry skipped",
                          file=sys.stderr)
                    continue
                yield entry
    except OSError as e:
        print(f"[note_io] ERROR reading {log_path}: {e}", file=sys.stderr)


def is_safe_path(path: str, root: str) -> bool:
    """True iff path is inside root. Path-traversal guard."""
    try:
        root_abs = os.path.abspath(root) + os.sep
        path_abs = os.path.abspath(path)
        return path_abs.startswith(root_abs) or path_abs == os.path.abspath(root)
    except Exception:
        return False
