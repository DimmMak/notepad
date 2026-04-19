# .notepad — Schema

**Schema version:** 0.1
**Storage:** `notes/log.md` (single append-only markdown file)

---

## Entry format

Every entry = one markdown bullet on one line. This keeps the file grep-friendly
and diff-friendly forever.

```markdown
- **YYYY-MM-DD HH:MM** · <text> · `#tag1` `#tag2` · _iso:YYYY-MM-DDTHH:MM:SS±HH:MM_
```

### Fields

| Field | Format | Required | Notes |
|---|---|---|---|
| Date + time | `**YYYY-MM-DD HH:MM**` | ✅ | Local time, human-readable |
| Text | free-form | ✅ | User's note — the payload |
| Tags | `` `#tag` `` space-separated | ❌ | Zero or more. Lowercase. |
| ISO timestamp | `_iso:YYYY-MM-DDTHH:MM:SS±HH:MM_` | ✅ | Machine parseable, timezone-aware |

Separator between fields = ` · ` (middle dot). Chosen because it's rare in prose.

---

## Parser contract

- `scripts/lib/note_io.parse_entry(line: str) -> dict | None`
- Returns `{"date":..., "time":..., "text":..., "tags":[...], "iso":...}` on match
- Returns `None` on malformed lines (logs a warning, doesn't crash)

## Writer contract

- `scripts/lib/note_io.append_entry(text: str, tags: list[str]) -> str`
- Generates timestamp deterministically from `datetime.now(timezone.local)`
- Returns the exact line that was appended
- File write is append-only. No other mode supported.

---

## Invariants

- **I1** Append-only: `log.md` only ever grows until the v0.2 archive rotation.
- **I2** One entry per line: a newline inside user text is escaped to `\\n`.
- **I3** Tag format: `#[a-z0-9-]+` — rejected otherwise (no spaces, no uppercase).
- **I4** ISO timestamp always timezone-aware (no naive datetimes).
- **I5** Never rewrite past entries. Typo fixes = new entry referencing old ISO.

---

## Migration plan

- v0.1 → v0.2: optional `priority:P0-P3` field (space-separated after tags).
- v0.1 → v0.3: log rotation monthly to `notes/archive/log-YYYY-MM.md`.
- Backward-compat: parser must accept v0.1 entries forever.
