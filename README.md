# bi-plugin

Claude Code plugin marketplace for the Cars Commerce BI team. Each plugin in this repo wraps a piece of BI tooling (Tableau, Redshift, etc.) as a skill, slash commands, or both, and ships via the standard Claude Code plugin install flow.

## Install the marketplace

In Claude Code:

```
/plugin marketplace add ahwang-cars/bi-plugin
```

Then install whichever plugins you want. They're independent — install only what you need.

## Available plugins

| Plugin | Install command | What it does |
|---|---|---|
| `tableau-sql-updater` | `/plugin install tableau-sql-updater@bi-plugin` | Edit and validate Tableau Online Custom SQL / Initial SQL via REST API. Includes the `tableau-sql-updater` workflow skill plus `/tableau-sql-updater:inspect-sql` and `/tableau-sql-updater:validate-sql` commands. |

After install, Claude Code will prompt you for any per-user config the plugin needs (e.g. Tableau Personal Access Token). Each user uses their own credentials — there are no shared secrets.

## Update an installed plugin

```
/plugin update <plugin-name>@bi-plugin
```

Plugins in this repo currently auto-update on every commit (no `version` field set). When a plugin stabilizes we'll start pinning SemVer.

## Contributing

To add a new plugin to this marketplace, see [`docs/adding-a-skill.md`](docs/adding-a-skill.md). The short version:

1. `cp -R plugins/_template plugins/<your-plugin>`
2. Edit `plugin.json`, write `SKILL.md` and/or `commands/*.md`, drop scripts in `scripts/`.
3. Append your plugin to `.claude-plugin/marketplace.json` and add a row to the table above.
4. Test locally with `/plugin marketplace add /path/to/this/repo`.
5. Push.

## Repo layout

```
bi-plugin/
├── .claude-plugin/marketplace.json   # marketplace manifest
├── plugins/
│   ├── tableau-sql-updater/          # first plugin
│   └── _template/                    # skeleton — copy to start a new plugin
└── docs/adding-a-skill.md            # contributor guide
```
