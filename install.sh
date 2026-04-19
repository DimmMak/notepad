#!/bin/bash
set -e
SRC="$HOME/Desktop/CLAUDE CODE/notepad"
DEST="$HOME/.claude/skills/notepad"

if [ -L "$DEST" ] || [ -e "$DEST" ]; then
    rm -rf "$DEST"
fi

ln -s "$SRC" "$DEST"
echo "✅ .notepad symlinked: $DEST -> $SRC"

VALIDATOR="$HOME/Desktop/CLAUDE CODE/future-proof/scripts/validate-skill.py"
if [ -f "$VALIDATOR" ]; then
    python3 "$VALIDATOR" "$DEST" || echo "⚠️  validator reported issues"
fi
