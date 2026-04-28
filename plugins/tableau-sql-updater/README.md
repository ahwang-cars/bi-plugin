# tableau-sql-updater

Update and validate the Custom SQL or Initial SQL of a Tableau Online datasource (or workbook) via the REST API. No Tableau Desktop round-trip.

## Install

From inside Claude Code:

```
/plugin marketplace add <github-org>/bi-plugin
/plugin install tableau-sql-updater@bi-plugin
```

On install, Claude Code will prompt for the `userConfig` values listed below. They're stored securely and injected as env vars when the skill or slash commands run.

### userConfig

| Key | Required | Sensitive | Notes |
|---|---|---|---|
| `tableau_token_name` | yes | no | Tableau Personal Access Token name |
| `tableau_token_secret` | yes | yes | Tableau PAT secret |
| `tableau_server_url` | no | no | Defaults to `https://us-west-2b.online.tableau.com` |
| `tableau_site_id` | no | no | Defaults to `cars`. Other supported: `dealertools` |
| `redshift_user` | yes | no | Redshift username embedded into the .tdsx for connection auth |
| `redshift_password` | yes | yes | Redshift password embedded into the .tdsx |

Each user generates their own PAT in Tableau Online (Settings → My Account Settings → Personal Access Tokens) and configures it in their own Claude Code install. There are no shared credentials.

## What you get

Once installed, three things become available:

| Surface | Type | Purpose |
|---|---|---|
| `tableau-sql-updater` | Skill | Multi-step ticket-driven workflow: confirm target → save SQL to `sql/<TICKET>.sql` → dry-run → publish → validate. Triggered by natural-language asks like "update the SQL on datasource X". |
| `/tableau-sql-updater:inspect-sql` | Slash command | One-shot read of current Custom + Initial SQL on a datasource. |
| `/tableau-sql-updater:validate-sql` | Slash command | Diff a local SQL file against the live datasource. Exits 1 on mismatch. |

## Where SQL files live

The skill writes ticket-scoped SQL to `sql/<TICKET>.sql` in your **current working directory**, not in the plugin install directory. Commit those files to whatever repo you use for SQL audit trail.

The plugin itself does not store any per-ticket SQL.

## First-run behavior

The first time any of the three surfaces runs, `scripts/bootstrap.sh` creates a Python venv at `${CLAUDE_PLUGIN_DATA}/venv` and pip-installs `tableauserverclient`. Subsequent runs are no-ops.

`${CLAUDE_PLUGIN_DATA}` persists across plugin updates, so this only happens once per install (and again after a `requirements.txt` change).

## Standalone use (without Claude Code)

The script still works as a plain CLI for local testing. From this directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
# Use --config (legacy config.json) OR set env vars TABLEAU_TOKEN_NAME, TABLEAU_TOKEN_SECRET, etc.
python scripts/tableau_sql_updater.py --datasource-name "<name>" --inspect-only
```

## Gotchas

- **Post-publish auth error is cosmetic.** The script embeds DB credentials into the `.tdsx` *before* publish, then tries to re-apply them via the REST API after. The post-publish call fails on Bridge-connected datasources with `400033: Authentication update is not allowed`. The publish itself succeeded — ignore the traceback.
- **Two Custom SQL relations are normal.** Most datasources have the same query in two places (physical layer + logical/object-graph layer). Tableau's UI shows it as one. The updater edits both to keep them consistent.
- **`--switch-to-table` changes the physical layer only.** The logical-table caption (e.g. "Custom SQL Query") persists in the UI even after switching — this is cosmetic. Renaming the caption requires Tableau Desktop.
- **Always run `validate-sql` after a publish** when the change is driven by a ticket.

## Troubleshooting

- **"Provide credentials via --config..."** — `userConfig` not set. Reconfigure the plugin.
- **"No datasource found with name: ..."** — the name lookup is case-insensitive but otherwise exact. If ambiguous across projects, use `--datasource-id` (looks up Tableau Online → datasource → URL contains the UUID).
- **Extract refresh fails after publish** — check Bridge connection settings in Tableau Online; embedded credentials may need to be re-saved manually.
