# tableau-sql-updater

Update and validate the Custom SQL or Initial SQL of a Tableau Online datasource (or workbook) via the REST API. No Tableau Desktop round-trip.

Two ways to use it: as a Claude Code plugin (smooth UX) or as a standalone Python CLI (works anywhere with Python 3.10+).

## Prerequisites (either path)

- Python 3.10+. macOS system `python3` is 3.9.6 — too old. Install via Homebrew (`brew install python@3.12`) or python.org.
- A Tableau Personal Access Token (Tableau Online → Settings → My Account Settings → Personal Access Tokens). Each user generates their own — no shared credentials.
- Database (Redshift) username + password if you'll be publishing changes; the script embeds these into the `.tdsx` so the connection authenticates after publish.

---

## Option A: Claude Code / Cowork

**Claude Code (terminal, self-serve):**

```
/plugin marketplace add ahwang-cars/bi-plugin
/plugin install tableau-sql-updater@bi-plugin
```

**Cowork (desktop, admin-mediated):** Cowork has no `/plugin` slash command. An org admin adds `ahwang-cars/bi-plugin` via Organization settings → Plugins → Add plugin → GitHub, then sets the state (Available / Installed by default / Required). End users then open the **Customize** sidebar → **Browse plugins** modal to install. See the [top-level README](../../README.md) for the full Cowork flow.

On install, Claude prompts for the `userConfig` values listed below. They're stored securely and injected as env vars when commands run. The Python venv is auto-bootstrapped on first use.

### userConfig

| Key | Required | Sensitive | Notes |
|---|---|---|---|
| `tableau_token_name` | yes | no | Tableau Personal Access Token name |
| `tableau_token_secret` | yes | yes | Tableau PAT secret |
| `tableau_server_url` | no | no | Defaults to `https://us-west-2b.online.tableau.com` |
| `tableau_site_id` | no | no | Defaults to `cars`. Other supported: `dealertools` |
| `redshift_user` | yes | no | Redshift username embedded into the .tdsx |
| `redshift_password` | yes | yes | Redshift password embedded into the .tdsx |

### What you get

| Surface | Type | Purpose |
|---|---|---|
| `tableau-sql-updater` | Skill | Multi-step ticket-driven workflow: confirm target → save SQL to `sql/<TICKET>.sql` → dry-run → publish → validate. Triggered by natural-language asks like "update the SQL on datasource X". |
| `/tableau-sql-updater:inspect-sql` | Slash command | One-shot read of current Custom + Initial SQL on a datasource. |
| `/tableau-sql-updater:validate-sql` | Slash command | Diff a local SQL file against the live datasource. Exits 1 on mismatch. |

The skill writes ticket-scoped SQL to `sql/<TICKET>.sql` in your **current working directory**, never into the plugin install. Commit those files to whatever repo you use for SQL audit trail.

---

## Option B: Standalone CLI (no Claude Code)

```bash
git clone https://github.com/ahwang-cars/bi-plugin.git
cd bi-plugin/plugins/tableau-sql-updater

python3.12 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

Then run with credentials supplied one of two ways:

**Via env vars:**
```bash
export TABLEAU_TOKEN_NAME="<your PAT name>"
export TABLEAU_TOKEN_SECRET="<your PAT secret>"
export REDSHIFT_USER="<your redshift user>"
export REDSHIFT_PASSWORD="<your redshift password>"
# optional, if not 'cars' / default server:
export TABLEAU_SITE_ID="dealertools"
export TABLEAU_SERVER_URL="https://..."

python scripts/tableau_sql_updater.py --datasource-name "<name>" --inspect-only
```

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
python scripts/tableau_sql_updater.py --config my-config.json \
  --datasource-name "<name>" --inspect-only
```

Common operations:
```bash
# Inspect
python scripts/tableau_sql_updater.py --datasource-name "X" --inspect-only

# Update Custom SQL (dry-run, then publish)
python scripts/tableau_sql_updater.py --datasource-name "X" --custom-sql-file sql/TICKET.sql --dry-run
python scripts/tableau_sql_updater.py --datasource-name "X" --custom-sql-file sql/TICKET.sql

# Validate live state matches a file
python scripts/tableau_sql_updater.py --datasource-name "X" --validate-sql sql/TICKET.sql

# Switch Custom SQL to a direct table
python scripts/tableau_sql_updater.py --datasource-name "X" --switch-to-table "schema.tablename" --dry-run
```

`--site dealertools` to target the dealertools site. `--workbook-name` instead of `--datasource-name` for workbook targets. `--help` for the full flag list.

What you give up vs. Option A: the auto-invoked workflow (Claude makes decisions and pauses for confirmation), the slash commands, and userConfig credential management. The underlying functionality is identical.

---

## Gotchas

- **Post-publish auth error is cosmetic.** The script embeds DB credentials into the `.tdsx` *before* publish, then tries to re-apply them via the REST API after. The post-publish call fails on Bridge-connected datasources with `400033: Authentication update is not allowed`. The publish itself succeeded — ignore the traceback.
- **Two Custom SQL relations are normal.** Most datasources have the same query in two places (physical layer + logical/object-graph layer). Tableau's UI shows it as one. The updater edits both to keep them consistent.
- **`--switch-to-table` changes the physical layer only.** The logical-table caption (e.g. "Custom SQL Query") persists in the UI even after switching — this is cosmetic. Renaming the caption requires Tableau Desktop.
- **Always run `--validate-sql` after a publish** when the change is driven by a ticket.

## Troubleshooting

- **"Provide credentials via --config..."** — env vars not set and no `--config` passed. Either reconfigure the plugin (Option A) or `export` the variables (Option B).
- **"No datasource found with name: ..."** — the name lookup is case-insensitive but otherwise exact. If ambiguous across projects, use `--datasource-id` (find the UUID in the Tableau Online URL when viewing the datasource).
- **`TypeError: unsupported operand type(s) for |`** during `tableauserverclient` import — your venv is using Python 3.9. Recreate with `python3.12 -m venv venv`.
- **Extract refresh fails after publish** — check Bridge connection settings in Tableau Online; embedded credentials may need to be re-saved manually.
