---
name: diff-sqls
description: Run two SQL scripts against Redshift and compare their result sets (row count, per-column aggregates, row-level set diff). Trigger when the user asks to compare/diff/validate two SQL files, two versions of a query, or Initial+Custom SQL pairs.
---

# diff-sqls

Run two SQL scripts on the same Redshift cluster and surface a structured diff of their result sets. Built for cases like "did my refactor change the output?" — including Tableau Initial SQL that builds temp tables and a Custom SQL that selects from them.

## When to use this skill

Trigger phrases:
- "compare the v1 and v2 of <thing>"
- "diff the results of these two SQL files"
- "did my change to <initial sql> alter the output?"
- "validate the new SQL returns the same rows as the old one"

## Prerequisites

- Python 3.10+ on PATH.
- A JSON config with Redshift creds. Auto-discovered from (in order):
  1. `$DIFF_SQLS_CONFIG` env var, if set
  2. `~/.tableau-config.json` (shared with `tableau-sql`)
  3. `~/.diff-sqls-config.json`
- The Python venv is bootstrapped on first use by `${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh` into `${CLAUDE_PLUGIN_DATA}/venv` and persists across plugin updates.

The plugin's `userConfig` schema exists, but per the bi-plugin runtime model, those values do not reach the bash this skill runs. Use the config file. If no config is found, point the user at the plugin README's "Credentials setup" and stop.

Recommended: extend the existing `~/.tableau-config.json` with a `redshift` block so both plugins share one creds file. user/password come from the same `connection_credentials` block `tableau-sql` already uses.

```json
{
  "tableau_server": { "...": "..." },
  "cars_site": { "...": "..." },
  "connection_credentials": {
    "username": "<your redshift user>",
    "password": "<your redshift password>"
  },
  "redshift": {
    "host": "dw.xyz.us-east-1.redshift.amazonaws.com",
    "port": 5439,
    "database": "dw"
  }
}
```

Standalone schema (if you don't have `~/.tableau-config.json` and don't want one):
```json
{
  "redshift": {
    "host": "...", "port": 5439, "database": "dw",
    "user": "...", "password": "..."
  }
}
```

## Standard workflow

1. **Identify the two sides.** Ask the user which files (or file pairs) represent side A and side B. Common shapes:
   - Two standalone SELECTs: `old.sql` vs `new.sql`
   - Two Initial SQL versions sharing a Custom SQL: `initial_v1.sql + custom.sql` vs `initial_v2.sql + custom.sql`
   - Initial-only, diffing a specific temp table: pass `--final-query "SELECT * FROM <temp>"`
2. **Confirm labels.** Default labels are `A` and `B`. For version diffs, prefer `--label-a v1 --label-b v2` (or `old`/`new`) so the output reads cleanly.
3. **Run the diff.** It prints row count, column aggregates, and (for ≤1000-row results) a row-level set diff. The same markdown is also auto-saved to a file (default: `diff-<labelA>-vs-<labelB>-<UTC-timestamp>.md` in cwd; override with `--output PATH`).
4. **Surface the verdict.** Exit 0 = full match; exit 1 = at least one aggregate or the row count differs. Don't paste the full markdown output back to the user — summarize the verdict, point at the saved-file path (printed to stderr as `Saved diff report to: …`), and call out the section with the diffs if any. The saved file is what the user will paste into the ticket.

## Invocation pattern

Each Bash call is a fresh subshell, so every invocation includes the bootstrap preamble inline.

```bash
# --- bootstrap preamble (prepend to every invocation) ---
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
export CLAUDE_PLUGIN_DATA="${HOME}/.claude/plugins/data/bi-plugin/diff-sqls"
CONFIG_FLAG=()
[ -n "${DIFF_SQLS_CONFIG:-}" ] && CONFIG_FLAG=(--config "$DIFF_SQLS_CONFIG")
PY=$("$CLAUDE_PLUGIN_ROOT/scripts/bootstrap.sh")
SCRIPT="$CLAUDE_PLUGIN_ROOT/scripts/diff_sqls.py"
# --- end preamble ---

"$PY" "$SCRIPT" "${CONFIG_FLAG[@]}" <flags…>
```

The script auto-discovers the config file from the lookup order above; the preamble only passes `--config` when the user explicitly overrides via `$DIFF_SQLS_CONFIG`.

## Commands

### Two standalone SELECTs
```bash
"$PY" "$SCRIPT" "${CONFIG_FLAG[@]}" \
  --a old.sql --b new.sql \
  --label-a old --label-b new
```

### Initial + Custom pair vs Initial v2 + same Custom
```bash
"$PY" "$SCRIPT" "${CONFIG_FLAG[@]}" \
  --a initial_v1.sql custom.sql \
  --b initial_v2.sql custom.sql \
  --label-a v1 --label-b v2
```
Each `--a` / `--b` list runs in order on its own connection, so temp tables created by `initial_*.sql` are visible to `custom.sql`.

### Initial-only, diff a specific temp table
```bash
"$PY" "$SCRIPT" "${CONFIG_FLAG[@]}" \
  --a initial_v1.sql --b initial_v2.sql \
  --final-query "SELECT * FROM leads_final" \
  --label-a v1 --label-b v2
```

### Custom row-diff threshold
```bash
"$PY" "$SCRIPT" "${CONFIG_FLAG[@]}" \
  --a old.sql --b new.sql --row-diff-limit 10000
```
Default is 1000. Raising it loads both result sets into Python memory and computes set difference — keep it modest.

## Flag reference

| Flag | Purpose |
|------|---------|
| `--a FILE [FILE…]` | Side A: one or more SQL files run in order on a dedicated connection |
| `--b FILE [FILE…]` | Side B: same idea |
| `--label-a` / `--label-b` | Display labels (default `A` / `B`) |
| `--final-query "<SQL>"` | Override the final SELECT (when files only set up temp tables) |
| `--row-diff-limit N` | Skip row-level set diff above this row count (default 1000) |
| `--config` | Path to JSON config with Redshift creds; auto-detected by the preamble |

## Gotchas

- **Last statement must be a SELECT.** If the concatenated files end on `CREATE TEMPORARY TABLE …`, the script exits with an error pointing at the file. Either add a SELECT file to the side's list, or pass `--final-query`.
- **Temp tables don't cross sides.** Each side runs on its own connection. That's deliberate — running v1 and v2 sequentially in one connection would let v1's temp tables leak into v2.
- **Column aggregates use side B's schema.** If the two queries return different column sets, side A's extras are silently ignored. A schema-drift check would be a useful follow-up.
- **Row-level diff requires sortable first column.** The script does `ORDER BY 1` so the rows compare deterministically. If column 1 is non-comparable across rows, that step will fail.
- **Sensitive data lives in your shell *and* in the saved report file.** Output is markdown printed to stdout AND saved to disk (autosave), so PII in the result set lands on the user's filesystem. Don't paste full output into chat or tickets without scrubbing. The saved-file path is printed to stderr after the run.

## Troubleshooting

- **"Missing Redshift credentials: ..."** — the script's auto-discovery searched the paths above and either found no file or found a file missing the required fields. The error message lists exactly which keys are missing. Most common fix: add a `redshift` block (host/port/database) to your existing `~/.tableau-config.json`.
- **"Last statement … is not a SELECT/WITH"** — your file only sets up temp tables. Add the final SELECT file to the side's list, or pass `--final-query "SELECT ... FROM <temp>"`.
- **`bootstrap.sh: CLAUDE_PLUGIN_DATA env var is required`** — the bootstrap preamble didn't run. Ensure the preamble is in the same Bash invocation as the script call.
