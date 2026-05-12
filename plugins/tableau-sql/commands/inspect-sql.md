---
description: Print the current Custom SQL and Initial SQL on a Tableau datasource (or workbook). Read-only.
argument-hint: <datasource-name-or-luid> [site]
---

Inspect the current SQL on a Tableau datasource without modifying anything.

## Args
- datasource (required) — first positional. Either the human-readable name from Tableau Online (quote if it contains spaces) or the datasource LUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`). LUID skips the name-lookup pager and is faster. Note: the numeric ID in a Tableau web URL (e.g. `/datasources/106191281`) is **not** the LUID.
- site — second positional, default `cars`. Either `cars` or `dealertools`.

If no datasource is given, ask the user and exit.

## Run

```bash
# Self-bootstrap plugin paths + locate a config.json. The harness does not propagate
# userConfig env vars to Bash-tool execution (see plugin README).
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
export CLAUDE_PLUGIN_DATA="${HOME}/.claude/plugins/data/bi-plugin/tableau-sql"

CONFIG="${TABLEAU_CONFIG:-}"
if [ -z "$CONFIG" ]; then
  for c in "${HOME}/.tableau-config.json"; do
    [ -f "$c" ] && CONFIG="$c" && break
  done
fi
CONFIG_FLAG=()
[ -n "$CONFIG" ] && CONFIG_FLAG=(--config "$CONFIG")

# Wrap the harness substitution in SINGLE quotes so user-typed double quotes
# don't escape into the surrounding bash. eval re-parses to set positional args.
# (Use ${N:-...} forms throughout — bare $N gets pre-substituted by the harness.)
ARGS_RAW='$ARGUMENTS'
eval set -- $ARGS_RAW

# Route by LUID shape: UUIDs go to --datasource-id (skips the name-lookup pager).
ARG1="${1:-}"
if [[ "$ARG1" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
  TARGET_FLAG=(--datasource-id "$ARG1")
else
  TARGET_FLAG=(--datasource-name "$ARG1")
fi

PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql.py" \
  "${CONFIG_FLAG[@]}" \
  --site "${2:-cars}" \
  "${TARGET_FLAG[@]}" \
  --inspect-only
```

If the user said "workbook" instead of "datasource", swap `--datasource-name` for `--workbook-name`.

Output is the script's standard inspection summary: connection info, Initial SQL (if any), each Custom SQL relation, and any direct table/view references. Don't post-process — pass through verbatim.
