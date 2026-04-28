---
name: tableau-sql-updater
description: Update or validate the Custom SQL / Initial SQL of a Tableau Online data source (or workbook) without opening Tableau Desktop. Trigger when the user asks to update, replace, inspect, validate, or switch-to-table the SQL of a Tableau datasource or workbook.
---

# Tableau SQL Updater

Programmatically edit a Tableau Online data source's Custom SQL or Initial SQL via the REST API — no Tableau Desktop round-trip.

## Prerequisites (handled by the plugin)

- Python 3.9+ on PATH.
- Credentials configured via plugin `userConfig` at install time (`tableau_token_name`, `tableau_token_secret`, `redshift_user`, `redshift_password`). These are injected as env vars (`TABLEAU_TOKEN_NAME`, `TABLEAU_TOKEN_SECRET`, `REDSHIFT_USER`, `REDSHIFT_PASSWORD`) when commands run.
- The Python venv is bootstrapped on first use by `${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh` into `${CLAUDE_PLUGIN_DATA}/venv` and persists across plugin updates.

If the user has not yet configured credentials, point them at the plugin README and stop.

## Where to save SQL files

Save ticket-scoped SQL in the **user's current working directory** under `sql/<TICKET>.sql` (e.g. `sql/EASD-2288.sql`). These are committed to whatever repo the user is operating from as the audit trail of what was deployed — `--validate-sql` can re-verify prod against the committed file at any time.

Do NOT save SQL into `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}` — that's plugin install state, not user data.

## When to use this skill

User says things like:
- "update the custom SQL for datasource X"
- "point datasource X at table `schema.table` instead of custom SQL"
- "validate the SQL on datasource X matches ticket-123.sql"
- "inspect the current SQL on datasource X"
- "update Initial SQL on datasource X"

Default site is `cars`. Other site in scope: `dealertools`.

For one-shot read-only operations users will more often invoke the slash commands directly:
- `/tableau-sql-updater:inspect-sql <datasource>` — show current SQL (truncated 500-char preview)
- `/tableau-sql-updater:dump-sql <datasource> [output-dir]` — write full Initial + Custom SQL to local .sql files
- `/tableau-sql-updater:validate-sql <ticket-or-file>` — diff against committed file

This skill owns the multi-step *write* workflow.

## Standard workflow

Follow this sequence for any SQL update:

1. **Confirm target and site.** Ask the user which datasource and which site (`cars` or `dealertools`) if not clear.
2. **Save the new SQL to `sql/<TICKET>.sql`** in the user's current working directory (e.g. `sql/EASD-2288.sql`).
3. **Dry-run** with `--dry-run` to confirm the script found the relations and the new SQL preview looks right.
4. **Confirm with the user** before publishing.
5. **Publish** (drop `--dry-run`).
6. **Validate** after publish with `--validate-sql` to prove the live datasource now matches the file.

## Invocation pattern

Every command runs through the bootstrap script to ensure the venv exists and deps are installed. Pattern:

```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" <flags…>
```

`bootstrap.sh` prints the path to the venv's `python`; the second line invokes the script using it. First run is slow (creates venv, installs `tableauserverclient`); subsequent runs are no-ops.

## Commands

### Inspect current SQL (preview)
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --inspect-only
```

### Dump full SQL to files
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --dump-sql ./sql
```
Writes `<slug>_initial.sql` and `<slug>_custom.sql` (or `_custom_1.sql`/`_custom_2.sql` for multiple distinct relations) into `./sql`. Read-only.

### Update Custom SQL (dry-run, then publish)
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
# Dry run
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --custom-sql-file sql/<TICKET>.sql --dry-run

# Publish
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --custom-sql-file sql/<TICKET>.sql
```

### Validate live SQL matches a file
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --validate-sql sql/<TICKET>.sql
```
Exits 0 on match, 1 on mismatch (with a unified diff).

### Switch Custom SQL to a direct table/view
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --switch-to-table "schema.tablename" --dry-run
```

### Update Initial SQL
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site <cars|dealertools> \
  --datasource-name "<Datasource Name>" --initial-sql-file <file>.sql --dry-run
```

### Workbook targets
Swap `--datasource-name` for `--workbook-name` for workbook targets (same flags apply).

## Flag reference

| Flag | Purpose |
|------|---------|
| `--site` | `cars` or `dealertools` (default: `cars`) |
| `--datasource-name` / `--datasource-id` | Target datasource (name looks up ID) |
| `--workbook-name` / `--workbook-id` | Target workbook instead of datasource |
| `--custom-sql-file` | Replace Custom SQL with the contents of this file |
| `--initial-sql-file` | Replace Initial SQL with the contents of this file |
| `--remove-initial-sql` | Remove Initial SQL entirely |
| `--switch-to-table` | Replace Custom SQL with a direct table ref (`schema.table`) |
| `--relation-name` | Only update the relation with this exact name |
| `--validate-sql` | Download and diff Custom SQL against a file (exit 1 on mismatch) |
| `--dump-sql` | Download and write full Initial + Custom SQL to .sql files in this directory |
| `--inspect-only` | Print current SQL; no changes |
| `--dry-run` | Modify locally but do NOT publish |
| `--output-dir` | Save the modified `.tdsx` locally |
| `--local-tdsx` / `--local-twbx` | Use a local file instead of downloading |
| `--config` | (Legacy) Path to config.json for standalone use outside the plugin |

## Helper: split_sql.py

If someone hands you one combined `.sql` file with both Initial SQL and Custom SQL, split it first:
```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/split_sql.py" combined.sql --output-dir ./split_output
```
Marker between sections must be `-- CUSTOM SQL BELOW --`. Output: `initial_sql.sql` and `custom_sql.sql`.

## Gotchas

- **Post-publish auth error is cosmetic.** The script embeds DB credentials into the `.tdsx` XML *before* publish, then tries to re-apply them via the REST API after publish. The API call fails on Bridge-connected datasources with `400033: Authentication update is not allowed`. The publish itself succeeded — ignore the traceback.
- **Two Custom SQL relations are normal.** Most datasources have the same query in two places (physical layer + logical/object-graph layer). Tableau's UI shows it as one. The updater edits both to keep them consistent.
- **`--switch-to-table` changes the physical layer only.** The logical-table caption (e.g. "Custom SQL Query") persists in the UI even after switching — this is cosmetic. Renaming the caption requires Tableau Desktop (it rewrites column bindings safely).
- **Always run `--validate-sql` after publish** when the change is driven by a ticket. It proves the deployed state matches the file you intended to ship.
- **Credentials live in plugin `userConfig`** (managed by Claude Code). Never commit them or paste them into shell history.

## Troubleshooting

- **"Provide credentials via --config..."** — `userConfig` not set or env vars not injected. Have the user reconfigure the plugin (`/plugin` → tableau-sql-updater → reconfigure).
- **"No datasource found with name: ..."** — check the exact casing; the name lookup is case-insensitive but the string must otherwise match. If ambiguous across projects, use `--datasource-id`.
- **Extract refresh fails after publish** — check the Bridge connection settings in Tableau Online; embedded credentials may need to be re-saved manually.
- **`bootstrap.sh: CLAUDE_PLUGIN_DATA env var is required`** — script being run outside the Claude Code plugin runtime. Set those env vars manually or use the legacy `--config config.json` path with a venv you create yourself.
