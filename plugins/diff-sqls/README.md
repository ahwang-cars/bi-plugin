# diff-sqls

Run two SQL scripts against Redshift and produce a structured diff of their result sets — row count, per-column distinct/null counts, and (for small results) a row-level set diff.

Built for the "did my refactor change the output?" workflow, including Tableau Initial SQL files that build temp tables consumed by a Custom SQL.

Two ways to use it: as a Claude Code plugin (skill + slash command), or as a standalone Python CLI.

## Prerequisites (either path)

- Python 3.10+. macOS system `python3` is 3.9 — too old. Install via `brew install python@3.12` or python.org.
- Redshift cluster you can read from, with credentials for a user that can run both SQL scripts.

---

## Option A: Claude Code plugin

```
/plugin marketplace add ahwang-cars/bi-plugin
/plugin install diff-sqls@bi-plugin
```

On install, Claude prompts for the `userConfig` keys listed below. The Python venv auto-bootstraps on first use.

### Credentials setup (required)

Creds are read from a JSON config file. Auto-discovery order:

1. `$DIFF_SQLS_CONFIG` env var, if set
2. `~/.tableau-config.json` (shared with `tableau-sql`)
3. `~/.diff-sqls-config.json`

**Recommended: extend your existing `~/.tableau-config.json`.** The Redshift user/password are read from the same `connection_credentials` block `tableau-sql` already uses; you only need to add a top-level `redshift` block with host/port/database. `tableau-sql` ignores the new block.

```json
{
  "tableau_server": { "...": "..." },
  "cars_site":      { "...": "..." },
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

`chmod 600 ~/.tableau-config.json` (you should already have done this).

**Alternative: standalone config.** If you don't use `tableau-sql`, put everything in `~/.diff-sqls-config.json`:

```bash
cat > ~/.diff-sqls-config.json <<'EOF'
{
  "redshift": {
    "host": "dw.xyz.us-east-1.redshift.amazonaws.com",
    "port": 5439,
    "database": "dw",
    "user": "<your redshift user>",
    "password": "<your redshift password>"
  }
}
EOF
chmod 600 ~/.diff-sqls-config.json
```

Env vars (`REDSHIFT_HOST`/`PORT`/`DATABASE`/`USER`/`PASSWORD`) fill any gaps the config file doesn't supply. Config values take precedence when both are present.

### What you get

| Surface | Type | Purpose |
|---|---|---|
| `diff-sqls` | Skill | Natural-language workflow: identify sides, pick labels, run the diff, surface the verdict. Handles multi-file sides (Initial + Custom). |
| `/diff-sqls:diff` | Slash command | One-shot: `/diff-sqls:diff old.sql new.sql`. For multi-file sides, use the skill. |

---

## Option B: Standalone CLI (no Claude Code)

```bash
git clone https://github.com/ahwang-cars/bi-plugin.git
cd bi-plugin/plugins/diff-sqls

python3.12 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

Credentials via env vars:
```bash
export REDSHIFT_HOST="dw.xyz.us-east-1.redshift.amazonaws.com"
export REDSHIFT_USER="<user>"
export REDSHIFT_PASSWORD="<password>"
# optional:
export REDSHIFT_PORT=5439
export REDSHIFT_DATABASE=dw

python scripts/diff_sqls.py --a old.sql --b new.sql
```

Or via the same JSON config the plugin uses:
```bash
python scripts/diff_sqls.py --config ~/.diff-sqls-config.json --a old.sql --b new.sql
```

Common patterns:
```bash
# Initial v1 vs Initial v2, shared Custom SQL
python scripts/diff_sqls.py \
  --a initial_v1.sql custom.sql \
  --b initial_v2.sql custom.sql \
  --label-a v1 --label-b v2

# Initial-only, diff a specific temp table
python scripts/diff_sqls.py \
  --a initial_v1.sql --b initial_v2.sql \
  --final-query "SELECT * FROM leads_final"
```

`--help` for the full flag list.

---

## Output

Markdown printed to stdout **and** saved to a file (the file is the artifact you paste into a ticket as proof of validation). Three sections:

1. **Row count** — both sides + MATCH/DIFF.
2. **Column aggregates** — total rows, distinct count, and null count per column on each side. Side B's schema is canonical; if the columns differ between sides, side A's extras are dropped.
3. **Row-level diff** — set difference of the two result sets. Skipped automatically when either side exceeds `--row-diff-limit` (default 1000) because the diff happens in Python memory.

Each report opens with a header recording timestamp, the input files for each side, and the `--final-query` if overridden — so a reviewer reading the file cold knows exactly what was compared.

**Output path:** defaults to `diff-<labelA>-vs-<labelB>-<UTC-timestamp>.md` in the current working directory. Override with `--output PATH` (e.g. `--output diffs/EASD-2288.md`). The file is opened before the first query runs, so a partial report survives mid-run failures.

Exit code: `0` if row count and every column aggregate match, `1` otherwise. Useful in CI/scripts.

## Gotchas

- **Last statement must be a SELECT.** If a side's concatenated input ends on `CREATE TEMPORARY TABLE …`, the script exits with an error. Either append a SELECT file to that side, or pass `--final-query`.
- **Each side runs on its own connection.** Deliberate — keeps temp-table namespaces independent. The flip side: setup runs twice (once per side), which is wasted work if the two sides share a setup phase. Optimizing that is a follow-up.
- **Set-diff requires sortable column 1.** `ORDER BY 1` is hardcoded for determinism. Move a comparable column first if needed.

## Troubleshooting

- **"Missing Redshift credentials"** — neither `--config` nor `REDSHIFT_*` env vars were resolved. See "Credentials setup" above.
- **"Last statement … is not a SELECT/WITH"** — pair the file with one that does the final SELECT, or pass `--final-query "SELECT ... FROM <temp>"`.
- **`TypeError: unsupported operand type(s) for |`** during `redshift_connector` or `sqlparse` import — your venv is on Python 3.9. Recreate with `python3.12 -m venv venv`.
