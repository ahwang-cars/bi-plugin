---
description: Run two SQL scripts on Redshift and diff their result sets. Exits 1 on mismatch.
argument-hint: <a-file> <b-file> [--final-query "SELECT ..."]
---

Diff Redshift result sets between two SQL scripts. The script opens one connection per side, runs each file in order (so `CREATE TEMPORARY TABLE` persists within a side), and compares row count + per-column aggregates of the final SELECT.

For the common case "Initial v1 vs Initial v2, same Custom SQL," call the script directly with `--a initial_v1.sql custom.sql --b initial_v2.sql custom.sql`. The bare slash command below covers the simple "one file per side" case; multi-file sides should invoke the script with the full preamble from the `diff-sqls` skill.

## Args

- `$1` — file for side A (required)
- `$2` — file for side B (required)
- remaining args — passed through to `diff_sqls.py` (e.g. `--final-query "..."`, `--label-a old --label-b new`)

If `$1` or `$2` is missing, ask the user and exit.

## Run

```bash
# Self-bootstrap plugin paths. Creds auto-discover from
# ~/.tableau-config.json → ~/sql-updater/config.json → ~/.diff-sqls-config.json
# (or set DIFF_SQLS_CONFIG / REDSHIFT_* env vars to override).
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
export CLAUDE_PLUGIN_DATA="${HOME}/.claude/plugins/data/bi-plugin/diff-sqls"

CONFIG_FLAG=()
[ -n "${DIFF_SQLS_CONFIG:-}" ] && CONFIG_FLAG=(--config "$DIFF_SQLS_CONFIG")

ARGS_RAW='$ARGUMENTS'
eval set -- $ARGS_RAW

A="${1:-}"
B="${2:-}"
shift 2 2>/dev/null || true

PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/diff_sqls.py" \
  "${CONFIG_FLAG[@]}" \
  --a "$A" --b "$B" "$@"
```

## Output

Markdown to stdout **and** auto-saved to a file (the artifact you paste into the ticket as proof of validation). Three sections: row count, column aggregates (distinct + null counts per column), and a row-level set diff for small result sets. Exit 0 if everything matches, 1 otherwise.

Default save path: `diff-<labelA>-vs-<labelB>-<UTC-timestamp>.md` in cwd. Override with `--output PATH` in the pass-through args (e.g. `--output diffs/EASD-2288.md`). The saved-file path is printed to stderr after the run.

If the script errors with "Last statement … is not a SELECT/WITH," the files only set up temp tables — re-run with `--final-query "SELECT ... FROM <temp_table>"`, or pair the file with a Custom SQL file via the skill's multi-file form.
