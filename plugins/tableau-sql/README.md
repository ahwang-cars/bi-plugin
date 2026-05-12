# tableau-sql

Update and validate the Custom SQL or Initial SQL of a Tableau Online datasource (or workbook) via the REST API. No Tableau Desktop round-trip.

Two ways to use it: as a Claude Code plugin (smooth UX) or as a standalone Python CLI (works anywhere with Python 3.10+).

## Prerequisites (either path)

- Python 3.10+. macOS system `python3` is 3.9.6 — too old. Install via Homebrew (`brew install python@3.12`) or python.org.
- A Tableau Personal Access Token (Tableau Online → Settings → My Account Settings → Personal Access Tokens). Each user generates their own — no shared credentials.
- Database (Redshift) username + password if you'll be publishing changes; the script embeds these into the `.tdsx` so the connection authenticates after publish.

---

## Option A: Claude Code plugin

```
/plugin marketplace add ahwang-cars/bi-plugin
/plugin install tableau-sql@bi-plugin
```

On install, Claude prompts for the `userConfig` values listed below. The Python venv is auto-bootstrapped on first use.

### Credentials setup (required)

The Claude Code harness does not currently propagate plugin `userConfig` env vars into the bash that slash commands run, so each command's Run block reads creds from a JSON config file instead. The schema matches the standalone-CLI config (see Option B below).

Lookup order:

1. `$TABLEAU_CONFIG` env var, if set
2. `~/.tableau-config.json`
3. `~/sql-updater/config.json` (legacy location — kept for back-compat with the pre-plugin standalone setup)

Create the file at one of those paths (and `chmod 600`). One PAT pair per site (cars and dealertools) — generate each in the corresponding Tableau Online site at Settings → My Account Settings → Personal Access Tokens. Server URL is hardcoded (`https://us-west-2b.online.tableau.com`). The skill asks which site to target on each invocation. See the example JSON under "Option B → Via a config.json" further down.

### userConfig (cosmetic — see note above)

The `/plugin` config UI exposes these keys, but the values currently are not reaching the slash command runtime. They're listed here for reference and to keep the schema accurate:

| Key | Sensitive | Notes |
|---|---|---|
| `tableau_token_name_cars` | no | PAT name for the cars site |
| `tableau_token_secret_cars` | yes | PAT secret for the cars site |
| `tableau_token_name_dealertools` | no | PAT name for the dealertools site |
| `tableau_token_secret_dealertools` | yes | PAT secret for the dealertools site |
| `redshift_user` | no | Redshift username embedded into the .tdsx |
| `redshift_password` | yes | Redshift password embedded into the .tdsx |

### What you get

| Surface | Type | Purpose |
|---|---|---|
| `update-sql` | Skill | Multi-step ticket-driven workflow: confirm target → save SQL to `sql/<TICKET>.sql` → dry-run (with diff) → publish (auto-validates against the input file). Triggered by natural-language asks like "update the SQL on datasource X". Invoked as `/tableau-sql:update-sql` if you want to trigger it explicitly. |
| `/tableau-sql:inspect-sql` | Slash command | One-shot read of current Custom + Initial SQL on a datasource (500-char preview). |
| `/tableau-sql:dump-sql` | Slash command | Download and write full Initial + Custom SQL to local .sql files for editing or audit. |
| `/tableau-sql:validate-sql` | Slash command | Diff a local SQL file against the live datasource. Exits 1 on mismatch. |

The skill writes ticket-scoped SQL to `sql/<TICKET>.sql` in your **current working directory**, never into the plugin install. Commit those files to whatever repo you use for SQL audit trail.

---

## Option B: Standalone CLI (no Claude Code)

```bash
git clone https://github.com/ahwang-cars/bi-plugin.git
cd bi-plugin/plugins/tableau-sql

python3.12 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

Then run with credentials supplied one of two ways:

**Via env vars:**
```bash
export TABLEAU_TOKEN_NAME="<PAT name for the site you're hitting>"
export TABLEAU_TOKEN_SECRET="<PAT secret for that site>"
export REDSHIFT_USER="<your redshift user>"
export REDSHIFT_PASSWORD="<your redshift password>"
# optional, defaults to 'cars':
export TABLEAU_SITE_ID="dealertools"

python scripts/tableau_sql.py --datasource-name "<name>" --inspect-only
```

Standalone use carries one PAT pair at a time — re-export when switching sites, or use `--config`.

**Via a config.json:**
```bash
cat > my-config.json <<'EOF'
{
  "tableau_server": {
    "server_url": "https://us-west-2b.online.tableau.com",
    "site_id": "dealertools",
    "token_name": "<PAT name>",
    "token_secret": "<PAT secret>"
  },
  "cars_site": {
    "site_id": "cars",
    "token_name": "<PAT name>",
    "token_secret": "<PAT secret>"
  },
  "connection_credentials": {
    "username": "<redshift user>",
    "password": "<redshift password>"
  }
}
EOF
chmod 600 my-config.json   # don't commit this
python scripts/tableau_sql.py --config my-config.json \
  --datasource-name "<name>" --inspect-only
```

Common operations:
```bash
# Inspect (500-char preview)
python scripts/tableau_sql.py --datasource-name "X" --inspect-only

# Dump full Initial + Custom SQL to ./sql/
python scripts/tableau_sql.py --datasource-name "X" --dump-sql ./sql

# Update Custom SQL (dry-run, then publish)
python scripts/tableau_sql.py --datasource-name "X" --custom-sql-file sql/TICKET.sql --dry-run
python scripts/tableau_sql.py --datasource-name "X" --custom-sql-file sql/TICKET.sql

# Validate live state matches a file
python scripts/tableau_sql.py --datasource-name "X" --validate-sql sql/TICKET.sql

# Switch Custom SQL to a direct table
python scripts/tableau_sql.py --datasource-name "X" --switch-to-table "schema.tablename" --dry-run
```

`--site dealertools` to target the dealertools site. `--workbook-name` instead of `--datasource-name` for workbook targets. `--help` for the full flag list.

What you give up vs. Option A: the auto-invoked workflow (Claude makes decisions and pauses for confirmation), the slash commands, and userConfig credential management. The underlying functionality is identical.

---

## Gotchas

- **Post-publish Bridge auth update is logged, not fatal.** Credentials are embedded into the `.tdsx` pre-publish; the script then tries to re-apply them via the REST API. On Bridge-connected datasources this fails with `400033: Authentication update is not allowed`. The script swallows that error and prints a one-line note to stderr — the publish itself already succeeded.
- **Two Custom SQL relations are normal.** Most datasources have the same query in two places (physical layer + logical/object-graph layer). Tableau's UI shows it as one. The updater edits both to keep them consistent.
- **`--switch-to-table` changes the physical layer only.** The logical-table caption (e.g. "Custom SQL Query") persists in the UI even after switching — this is cosmetic. Renaming the caption requires Tableau Desktop.
- **Post-publish validation is automatic.** When you publish with `--custom-sql-file` or `--initial-sql-file`, the script re-downloads the live datasource and diffs it against the input file, exiting non-zero on mismatch. Pass `--no-validate` to skip. `--validate-sql` is still useful for standalone re-checks against a committed ticket file.

## Troubleshooting

- **"Provide credentials via --config..."** or **"No PAT configured for site 'cars'"** — `~/.tableau-creds` is missing or doesn't export the expected variables. See "Credentials setup" above.
- **"CLAUDE_PLUGIN_DATA env var is required"** — you're running `bootstrap.sh` directly outside a slash command. Use the slash commands instead, or set both `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` manually before running.
- **"No datasource found with name: ..."** — the name lookup is case-insensitive but otherwise exact. If ambiguous across projects, use `--datasource-id` (find the UUID in the Tableau Online URL when viewing the datasource).
- **`TypeError: unsupported operand type(s) for |`** during `tableauserverclient` import — your venv is using Python 3.9. Recreate with `python3.12 -m venv venv`.
- **Extract refresh fails after publish** — check Bridge connection settings in Tableau Online; embedded credentials may need to be re-saved manually.
