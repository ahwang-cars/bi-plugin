# Adding a new skill or command to bi-plugin

This repo is a Claude Code plugin marketplace. Each top-level entry under `plugins/` is one plugin, listed in `.claude-plugin/marketplace.json`. To add a new tool, you author a new plugin and append it to that list.

## Decision: skill vs. slash command vs. both

| Use | When |
|---|---|
| **Skill** (`skills/<name>/SKILL.md`) | Multi-step workflows where Claude needs to make decisions or pause for user confirmation between steps. Triggered by natural-language intent. |
| **Slash command** (`commands/<name>.md`) | Atomic, deterministic operations the user already knows they want. Triggered by typing `/<plugin>:<command>`. |
| **Both** | When the same underlying script powers a workflow *and* a few sharp one-shot ops. The skill orchestrates; the slash commands are direct entry points. (See `tableau-sql-updater` for an example.) |

If you find yourself writing more than ~5 distinct operations under one plugin, that's a sign to split into multiple plugins, not one mega-skill.

## Steps

1. **Copy the template.**
   ```bash
   cp -R plugins/_template plugins/<your-plugin-name>
   ```

2. **Edit `plugins/<your-plugin-name>/.claude-plugin/plugin.json`.**
   - `name` — kebab-case, becomes the namespace prefix (`/<your-plugin-name>:command`).
   - `description` — shown in `/plugin` manager.
   - `keywords` — for discovery.
   - `userConfig` — every secret or per-user setting goes here. Mark secrets with `"sensitive": true`. Claude Code prompts for these at install/enable and injects them as env vars (`MY_KEY` → `MY_KEY`).

3. **Author the skill (if any).**
   - Rename `skills/_template/` to `skills/<your-skill-name>/`.
   - Replace `SKILL.md` frontmatter — the `description` is what Claude matches user intent against, so be specific about trigger phrases.
   - Reference scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/...`.
   - Reference persistent state via `${CLAUDE_PLUGIN_DATA}/...` — survives plugin updates.
   - Delete the skill folder if your plugin is slash-commands-only.

4. **Author slash commands (if any).**
   - One `commands/<name>.md` per command.
   - Frontmatter: `description` (one line) and `argument-hint` (autocomplete preview).
   - Body: prose instructions for Claude *plus* the bash invocation pattern.
   - Delete the `commands/` folder if your plugin is skill-only.

5. **Drop scripts in `scripts/`.**
   - Python: keep `requirements.txt` and `bootstrap.sh` (template provides both). The bootstrap creates a venv at `${CLAUDE_PLUGIN_DATA}/venv` on first run.
   - Other runtimes: replace `bootstrap.sh` with whatever idempotent setup makes sense, or delete it if the script is dependency-free.

6. **Add the plugin to the marketplace manifest.**
   In `.claude-plugin/marketplace.json`, append an entry to `plugins`:
   ```json
   {
     "name": "<your-plugin-name>",
     "source": "./plugins/<your-plugin-name>",
     "description": "...",
     "category": "...",
     "keywords": ["..."]
   }
   ```

7. **Update the top-level `README.md`** with a row for the new plugin.

8. **Test locally before pushing.**
   From a scratch directory:
   ```
   /plugin marketplace add /Users/<you>/bi-plugin
   /plugin install <your-plugin-name>@bi-plugin
   ```
   Confirm `userConfig` prompts fire. Run a slash command or trigger the skill with a known-good input.

9. **Push to main.** With no `version` field, every commit becomes a new auto-update. Bump `version` in `plugin.json` once you want stable releases.

## Conventions

- **Credentials** never live in repo files. Always go through `userConfig`.
- **Scripts** read credentials from env vars matching the `userConfig` keys. Support a fallback path (`--config` flag, env vars set manually) so the script remains usable standalone.
- **Output paths**: write user data to the user's CWD (`./sql/<TICKET>.sql`, etc.), not into `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}`.
- **`${CLAUDE_PLUGIN_DATA}`** is for plugin-managed state (venvs, caches, generated artifacts). Survives plugin updates.
- **`${CLAUDE_PLUGIN_ROOT}`** is the installed plugin directory. Read-only. Resets on plugin update.
- One skill workflow per plugin, plus its supporting commands. Don't bundle unrelated tools into one plugin.
