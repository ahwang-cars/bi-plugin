#!/usr/bin/env bash
# Idempotent venv bootstrap. Copy as-is to any plugin that needs a Python venv;
# adjust the minimum Python version below to match your dependency needs.
#
# Delete this file if your plugin has no Python deps.

set -euo pipefail

: "${CLAUDE_PLUGIN_DATA:?CLAUDE_PLUGIN_DATA env var is required (set by Claude Code at runtime).}"
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT env var is required (set by Claude Code at runtime).}"

# Set MIN_PY_MAJOR/MIN_PY_MINOR to whatever your deps require. macOS system python is 3.9.
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PY_MAJOR}, ${MIN_PY_MINOR}) else 1)"; then
      echo "python3"
      return 0
    fi
  fi
  return 1
}

VENV="$CLAUDE_PLUGIN_DATA/venv"
REQ="$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"
HASH_FILE="$VENV/.requirements.sha256"

mkdir -p "$CLAUDE_PLUGIN_DATA"

if [[ ! -x "$VENV/bin/python" ]]; then
  PY_BIN=$(find_python) || {
    echo "ERROR: this plugin requires Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+, but none was found on PATH." >&2
    exit 1
  }
  "$PY_BIN" -m venv "$VENV"
fi

CURRENT_HASH=$(shasum -a 256 "$REQ" | awk '{print $1}')
PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")

if [[ "$CURRENT_HASH" != "$PREV_HASH" ]]; then
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$REQ"
  echo "$CURRENT_HASH" > "$HASH_FILE"
fi

echo "$VENV/bin/python"
