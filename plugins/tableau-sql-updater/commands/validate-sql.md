---
description: Diff a local SQL file against the live Custom SQL on a Tableau datasource. Exits 1 on mismatch with a unified diff.
argument-hint: <datasource-name> <sql-file> [site]
---

Validate that the live Custom SQL on a Tableau datasource matches a local file. Use this after a publish (to confirm deploy) or any time someone wants to re-verify prod against the committed ticket SQL.

## Args
- `$1` — datasource name (required). Quote if it contains spaces.
- `$2` — path to the SQL file to compare against (required, e.g. `sql/EASD-2288.sql`). Resolved relative to the user's current working directory.
- `$3` — site (optional, default `cars`). Either `cars` or `dealertools`.

If either `$1` or `$2` is missing, ask the user and exit. If `$2` doesn't exist on disk, say so and exit — don't try to construct one.

## Run

```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/tableau_sql_updater.py" \
  --site "${3:-cars}" \
  --datasource-name "$1" \
  --validate-sql "$2"
```

## Output

- Exit 0: live datasource matches the file (whitespace-normalized). Report "MATCH" to the user.
- Exit 1: mismatch. The script prints a unified diff. Pass it through verbatim and tell the user the live state has drifted from the file.
- "No Custom SQL relations found in datasource" means the datasource isn't using Custom SQL (e.g. it's a direct table connection). Surface this clearly — validation failed not because of drift but because there's nothing to compare against.
