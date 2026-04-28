---
name: TODO-skill-name
description: TODO — one sentence describing when Claude should auto-invoke this skill. The description is what Claude matches user intent against, so be specific about trigger phrases.
---

# TODO skill title

## When to use this skill

Replace this section with example user phrases that should trigger the skill.

## Standard workflow

1. Replace these steps with the actual workflow.
2. Reference scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/...`.
3. Reference persistent state (venv, caches) via `${CLAUDE_PLUGIN_DATA}/...`.

## Invocation pattern

If your skill calls a Python script:

```bash
PY=$(${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.sh)
"$PY" "${CLAUDE_PLUGIN_ROOT}/scripts/your_script.py" <flags>
```

Drop this section if your skill is pure prose.

## Gotchas / Troubleshooting

TODO.
