# bi-plugin

Cars BI team tooling, packaged for two audiences:

- **Claude Code users** — install as a plugin and get skills + slash commands. Self-serve, no admin needed.
- **Everyone else** — clone the repo and run the underlying scripts directly. No Claude Code needed.

Each plugin under `plugins/` is built around a self-contained Python (or other-language) script. The plugin metadata is just a UX wrapper.

---

## Available plugins

| Plugin | What it does |
|---|---|
| `tableau-sql-updater` | Edit and validate Tableau Online Custom SQL / Initial SQL via REST API. |

See each plugin's `README.md` for setup details and prerequisites.

---

## Option 1: Install as a Claude Code plugin

In Claude Code:

```
/plugin marketplace add ahwang-cars/bi-plugin
/plugin install tableau-sql-updater@bi-plugin
```

Claude prompts for any per-user config the plugin needs (e.g. Tableau Personal Access Token). Each user uses their own credentials — no shared secrets.

Update later with `/plugin update tableau-sql-updater@bi-plugin`. Plugins auto-update on every commit while in early dev (no `version` pin yet); once a plugin stabilizes we'll start pinning SemVer.

---

## Option 2: Run the script directly (no Claude Code)

Clone the repo and run the script in any plugin's `scripts/` directory:

```bash
git clone https://github.com/ahwang-cars/bi-plugin.git
cd bi-plugin/plugins/tableau-sql-updater
python3.12 -m venv venv && source venv/bin/activate
pip install -r scripts/requirements.txt

# either point at a config.json:
python scripts/tableau_sql_updater.py --config /path/to/config.json \
  --datasource-name "<datasource>" --inspect-only

# or set env vars and skip --config:
export TABLEAU_TOKEN_NAME=... TABLEAU_TOKEN_SECRET=...
python scripts/tableau_sql_updater.py --datasource-name "<datasource>" --inspect-only
```

Requires Python 3.10+ (system `python3` on macOS is 3.9.6, too old). Use Homebrew (`brew install python@3.12`) or python.org if needed.

You lose the workflow skill, slash commands, and the auto-managed credential store, but the underlying functionality is identical.

---

## Contributing

To add a new plugin to this marketplace, see [`docs/adding-a-skill.md`](docs/adding-a-skill.md). Short version:

1. `cp -R plugins/_template plugins/<your-plugin>`
2. Edit `plugin.json`, write `SKILL.md` and/or `commands/*.md`, drop scripts in `scripts/`.
3. Append your plugin to `.claude-plugin/marketplace.json` and add a row to the table above.
4. Test locally with `/plugin marketplace add /path/to/this/repo`.
5. Push.

---

## Repo layout

```
bi-plugin/
├── .claude-plugin/marketplace.json   # marketplace manifest
├── plugins/
│   ├── tableau-sql-updater/          # first plugin
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/                   # multi-step workflows (Claude-Code-only)
│   │   ├── commands/                 # slash commands (Claude-Code-only)
│   │   ├── scripts/                  # the actual tooling (works standalone)
│   │   └── README.md
│   └── _template/                    # skeleton — copy to start a new plugin
├── docs/adding-a-skill.md            # contributor guide
└── CLAUDE.md                         # maintainer notes
```
