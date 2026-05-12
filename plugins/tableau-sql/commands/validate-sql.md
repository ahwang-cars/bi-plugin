---
description: Diff a local SQL file against the live Custom SQL on a Tableau datasource. Exits 1 on mismatch with a unified diff.
argument-hint: <datasource-name-or-luid> <sql-file> [site]
---

Validate that the live Custom SQL on a Tableau datasource matches a local file. Use this after a publish (to confirm deploy) or any time someone wants to re-verify prod against the committed ticket SQL.

## Args
- datasource (required) — first positional. Either the human-readable name (quote if it contains spaces) or the datasource LUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`). LUID skips the name-lookup pager and is faster. Note: the numeric ID in a Tableau web URL (e.g. `/datasources/106191281`) is **not** the LUID.
- sql file path (required) — second positional, e.g. `sql/EASD-2288.sql`. Resolved relative to the user's current working directory.
- site — third positional, default `cars`. Either `cars` or `dealertools`.

If either is missing, ask the user and exit. If the SQL file doesn't exist on disk, say so and exit — don't try to construct one.

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
  --site "${3:-cars}" \
  "${TARGET_FLAG[@]}" \
  --validate-sql "${2:-}"
```

## Output

- Exit 0: live datasource matches the file (whitespace-normalized). Report "MATCH" to the user.
- Exit 1: mismatch. The script prints a unified diff. Pass it through verbatim and tell the user the live state has drifted from the file.
- "No Custom SQL relations found in datasource" means the datasource isn't using Custom SQL (e.g. it's a direct table connection). Surface this clearly — validation failed not because of drift but because there's nothing to compare against.
