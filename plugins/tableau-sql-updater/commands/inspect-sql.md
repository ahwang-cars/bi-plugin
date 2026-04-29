---
description: Print the current Custom SQL and Initial SQL on a Tableau datasource (or workbook). Read-only.
argument-hint: <datasource-name> [site]
---

Inspect the current SQL on a Tableau datasource without modifying anything.

## Args
- datasource name (required) — first positional. Use the human-readable name from Tableau Online; the script looks up the UUID. Quote if it contains spaces.
- site — second positional, default `cars`. Either `cars` or `dealertools`.

If no datasource name is given, ask the user and exit.

## Run

```bash
# Self-bootstrap plugin paths + locate a config.json. The harness does not propagate
# userConfig env vars to Bash-tool execution (see plugin README).
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
export CLAUDE_PLUGIN_DATA="${HOME}/.claude/plugins/data/bi-plugin/tableau-sql-updater"

CONFIG="${TABLEAU_CONFIG:-}"
if [ -z "$CONFIG" ]; then
  for c in "${HOME}/.tableau-config.json" "${HOME}/sql-updater/config.json"; do
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

PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  "${CONFIG_FLAG[@]}" \
  --site "${2:-cars}" \
  --datasource-name "${1:-}" \
  --inspect-only
```

If the user said "workbook" instead of "datasource", swap `--datasource-name` for `--workbook-name`.

Output is the script's standard inspection summary: connection info, Initial SQL (if any), each Custom SQL relation, and any direct table/view references. Don't post-process — pass through verbatim.
