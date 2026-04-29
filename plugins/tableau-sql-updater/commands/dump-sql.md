---
description: Download a Tableau datasource and write its full Initial SQL and Custom SQL to local .sql files. Read-only.
argument-hint: <datasource-name> [output-dir] [site]
---

Pull the live SQL off a Tableau datasource and write it to local `.sql` files. Use this when you want to read or edit the SQL — `inspect-sql` only shows a 500-char preview.

## Args
- datasource name (required) — first positional. Quote if it contains spaces.
- output directory — second positional, default `./sql`. Created if missing. Resolved relative to the user's current working directory.
- site — third positional, default `cars`. Either `cars` or `dealertools`.

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
  --site "${3:-cars}" \
  --datasource-name "${1:-}" \
  --dump-sql "${2:-./sql}"
```

## Output

The script prints the file paths it wrote, one per line. Filenames are `<datasource-slug>_initial.sql` and `<datasource-slug>_custom.sql` (or `_custom_1.sql`/`_custom_2.sql` if there are multiple distinct Custom SQL relations — duplicates from the physical+logical layer are deduped automatically).

After it runs, list the file paths back to the user. Don't dump the SQL contents into chat unless the user asks — the files are the artifact.

If the output says "No Initial SQL or Custom SQL found on this datasource", the datasource is using a direct table/view connection, not Custom SQL. Surface that clearly.
