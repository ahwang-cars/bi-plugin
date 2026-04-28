#!/usr/bin/env bash
# Idempotent venv bootstrap. First call creates the venv and installs deps;
# subsequent calls are no-ops if requirements.txt is unchanged.
#
# CLAUDE_PLUGIN_DATA persists across plugin updates (per Claude Code plugin docs);
# CLAUDE_PLUGIN_ROOT points at the installed plugin directory.

set -euo pipefail

: "${CLAUDE_PLUGIN_DATA:?CLAUDE_PLUGIN_DATA env var is required (set by Claude Code at runtime).}"
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT env var is required (set by Claude Code at runtime).}"

VENV="$CLAUDE_PLUGIN_DATA/venv"
REQ="$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"
HASH_FILE="$VENV/.requirements.sha256"

mkdir -p "$CLAUDE_PLUGIN_DATA"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi

CURRENT_HASH=$(shasum -a 256 "$REQ" | awk '{print $1}')
PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")

if [[ "$CURRENT_HASH" != "$PREV_HASH" ]]; then
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$REQ"
  echo "$CURRENT_HASH" > "$HASH_FILE"
fi

# Print the python interpreter so callers can capture it: PY=$(bootstrap.sh)
echo "$VENV/bin/python"
