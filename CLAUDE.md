# CLAUDE.md — bi-plugin maintainer notes

This repo is a **Claude Code plugin marketplace** for the Cars Commerce BI team. Each top-level entry under `plugins/` is one plugin, listed in `.claude-plugin/marketplace.json`. Teammates install plugins via `/plugin marketplace add ahwang-cars/bi-plugin`, then `/plugin install <name>@bi-plugin`.

When you (a maintainer) ask me to do work in this repo, I should default to these conventions:

## Adding or editing plugins

- The contributor flow lives in [`docs/adding-a-skill.md`](docs/adding-a-skill.md). Follow it; don't re-derive structure from scratch.
- Skeleton lives at `plugins/_template/` — copy, don't reinvent.
- When adding a plugin, also append it to `.claude-plugin/marketplace.json` and the plugins table in the top-level `README.md`. Easy to forget.
- One workflow per plugin. Don't bundle unrelated tooling.

## Skill vs. slash command

- Skill (`skills/<name>/SKILL.md`): multi-step workflows where Claude makes decisions or pauses for confirmation. Triggered by natural language.
- Slash command (`commands/<name>.md`): atomic, deterministic ops. Triggered by typing `/<plugin>:<command>`.
- Same script can power both. See `tableau-sql-updater` for the pattern.

## Path / runtime conventions

- `${CLAUDE_PLUGIN_ROOT}` — installed plugin dir. Read-only. Resets on plugin update.
- `${CLAUDE_PLUGIN_DATA}` — persistent state (venvs, caches). Survives updates.
- User data (e.g. ticket SQL files) goes in the **user's CWD**, not into the plugin install. Never write `${CLAUDE_PLUGIN_ROOT}/sql/...`.
- Credentials only via `userConfig` in `plugin.json`. Never commit a `config.json`. Scripts read injected env vars.

## Python plugins

- Bootstrap requires **Python 3.10+** (system `python3` on macOS is 3.9, too old). `scripts/bootstrap.sh` probes `python3.13/12/11/10` and falls back to `python3` only if its version satisfies the minimum.
- `bootstrap.sh` is idempotent: rebuilds the venv only when `requirements.txt` hash changes.
- Scripts should keep their standalone CLI usable (`--config` flag, env vars) so they can be tested outside Claude Code.

## Versioning

- No `version` field in `plugin.json` during early dev → every commit is a new auto-update for installed users. Pin SemVer once a plugin stabilizes.

## What goes elsewhere

- Per-user setup (PATs, install steps): the plugin's own `README.md`, not here.
- Workflow docs (when to run what command, ticket conventions): the plugin's `SKILL.md`, not here.
- This file is for *maintainer* context — what to keep in mind when editing the marketplace itself.
