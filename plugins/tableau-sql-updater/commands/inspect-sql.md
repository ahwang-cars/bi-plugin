---
description: Print the current Custom SQL and Initial SQL on a Tableau datasource (or workbook). Read-only.
argument-hint: <datasource-name> [site]
---

Inspect the current SQL on a Tableau datasource without modifying anything.

## Args
- `$1` — datasource name (required). Use the human-readable name from Tableau Online; the script looks up the UUID. Quote it if it contains spaces.
- `$2` — site (optional, default `cars`). Either `cars` or `dealertools`.

If `$1` is missing, ask the user for the datasource name and exit.

## Run

```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site "${2:-cars}" \
  --datasource-name "$1" \
  --inspect-only
```

If the user said "workbook" instead of "datasource", swap `--datasource-name` for `--workbook-name`.

Output is the script's standard inspection summary: connection info, Initial SQL (if any), each Custom SQL relation, and any direct table/view references. Don't post-process — pass through verbatim.
