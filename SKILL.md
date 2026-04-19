---
name: notepad
domain: general
version: 0.1.0
description: >
  Append-only bulletpoint logbook. Every entry auto-tagged with date / time / ISO timestamp / optional user-supplied tags. Quick capture like Windows 11 Notepad, plus recall-by-tag and time-window filters. One flat markdown stream — yours forever, readable anywhere. NOT for: structured knowledge bases (use courserafied). NOT for: scheduled reminders (use schedule). NOT for: long-form writing (use journalist).
capabilities:
  reads:
    - notes/log.md
    - config/settings.json
  writes:
    - notes/log.md (append-only)
  calls: []
  cannot:
    - modify or delete past entries (append-only invariant)
    - execute note contents as code
    - reach outside notepad/notes/
    - auto-sync to cloud
unix_contract:
  data_format: "markdown-bulletpoints"
  schema_version: "0.1"
  stdin_support: true
  stdout_format: "markdown"
  composable_with:
    - home
    - mewtwo
    - courserafied
    - time-machine
---

# .notepad — Bulletpoint Logbook

**One flat stream of timestamped bullets. Capture in 2 seconds, recall by tag / date / keyword.**

---

## 🎯 Commands

| Command | What it does |
|---|---|
| `.notepad` | Show the last 20 entries |
| `.notepad "<text>"` | Append bullet (auto-tag: date, time, ISO) |
| `.notepad add "<text>" [#tag1 #tag2]` | Append with explicit extra tags |
| `.notepad today` | Show only today's entries |
| `.notepad yesterday` | Show yesterday's entries |
| `.notepad week` | Show last 7 days |
| `.notepad search <term>` | Grep entries (full-text) |
| `.notepad tag <name>` | Show all entries with that tag |
| `.notepad tags` | List all unique tags + counts |
| `.notepad stats` | Total entries / total bytes / entries per day |

---

## 📐 Entry format (written to `notes/log.md`)

Every entry is one bullet on one line:

```markdown
- **2026-04-19 17:45** · pizza idea for Friday · `#food` `#ideas` · _iso:2026-04-19T17:45:00-04:00_
```

Auto-tags on every entry:
- **Bold date + time** for human scan
- User-supplied `#tags` (optional)
- `iso:<ISO-8601>` for machine parsing

---

## 🛡️ Safety rules (non-goals)

| Rule | Why |
|---|---|
| Append-only — never modify past entries | Entries are your memory. Editing = drift. |
| Never execute note contents | Data, not code. |
| Never reach outside `notepad/notes/` | Path-traversal guard in `note_io.py`. |
| Never sync to cloud | Your disk is the source of truth. |
| Soft-archive the log monthly (future) | 10k-entry rotation at v0.2. |

---

## 🌳 Tree structure

```
notepad/
├── SKILL.md              ← this file
├── SCHEMA.md             ← entry format
├── config/settings.json  ← defaults
├── scripts/
│   ├── notepad.py        ← CLI (add / show / search / tag)
│   └── lib/note_io.py    ← safe append-only ops
├── notes/
│   └── log.md            ← THE single stream (append-only)
├── tests/
└── install.sh
```

🗒️🔒🃏
