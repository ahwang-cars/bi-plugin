#!/usr/bin/env bash
# Idempotent venv bootstrap. Copy as-is to any plugin that needs a Python venv;
# the only thing plugin-specific here is requirements.txt at scripts/requirements.txt.
#
# Delete this file if your plugin has no Python deps.

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

echo "$VENV/bin/python"
