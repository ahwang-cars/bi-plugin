---
description: Download a Tableau datasource and write its full Initial SQL and Custom SQL to local .sql files. Read-only.
argument-hint: <datasource-name-or-luid> [site] [output-dir]
---

Pull the live SQL off a Tableau datasource and write it to local `.sql` files. Use this when you want to read or edit the SQL — `inspect-sql` only shows a 500-char preview.

## Args
- datasource (required) — first positional. Either the human-readable name (quote if it contains spaces) or the datasource LUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`). LUID skips the name-lookup pager and is faster. Note: the numeric ID in a Tableau web URL (e.g. `/datasources/106191281`) is **not** the LUID.
- site — second positional, default `cars`. Either `cars` or `dealertools`.
- output directory — third positional, default `./sql`. Created if missing. Resolved relative to the user's current working directory.

If no datasource is given, ask the user and exit.

## Run

```bash
# Self-bootstrap plugin paths + locate a config.json. The harness does not propagate
# userConfig env vars to Bash-tool execution (see plugin README).
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
export CLAUDE_PLUGIN_DATA="${HOME}/.claude/plugins/data/bi-plugin/tableau-sql"

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
  --dump-sql "${3:-./sql}"
```

## Output

The script prints the file paths it wrote, one per line. Filenames are `<datasource-slug>_initial.sql` and `<datasource-slug>_custom.sql` (or `_custom_1.sql`/`_custom_2.sql` if there are multiple distinct Custom SQL relations — duplicates from the physical+logical layer are deduped automatically).

After it runs, list the file paths back to the user. Don't dump the SQL contents into chat unless the user asks — the files are the artifact.

If the output says "No Initial SQL or Custom SQL found on this datasource", the datasource is using a direct table/view connection, not Custom SQL. Surface that clearly.
