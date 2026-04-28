---
description: Download a Tableau datasource and write its full Initial SQL and Custom SQL to local .sql files. Read-only.
argument-hint: <datasource-name> [output-dir] [site]
---

Pull the live SQL off a Tableau datasource and write it to local `.sql` files. Use this when you want to read or edit the SQL — `inspect-sql` only shows a 500-char preview.

## Args
- `$1` — datasource name (required). Quote if it contains spaces.
- `$2` — output directory (optional, default `./sql`). Created if missing. Resolved relative to the user's current working directory.
- `$3` — site (optional, default `cars`). Either `cars` or `dealertools`.

If `$1` is missing, ask the user for the datasource name and exit.

## Run

```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site "${3:-cars}" \
  --datasource-name "$1" \
  --dump-sql "${2:-./sql}"
```

## Output

The script prints the file paths it wrote, one per line. Filenames are `<datasource-slug>_initial.sql` and `<datasource-slug>_custom.sql` (or `_custom_1.sql`/`_custom_2.sql` if there are multiple distinct Custom SQL relations — duplicates from the physical+logical layer are deduped automatically).

After it runs, list the file paths back to the user. Don't dump the SQL contents into chat unless the user asks — the files are the artifact.

If the output says "No Initial SQL or Custom SQL found on this datasource", the datasource is using a direct table/view connection, not Custom SQL. Surface that clearly.
