# Installing Panel for Codex

The panel skill is harness-agnostic. The canonical skill lives in `skills/panel/` (`SKILL.md` + `panel_client.py`), and any Codex-flavored agent wrapping goes in `.codex/agents/*.toml`.

When tuning panel intents or persona defaults, edit `skills/panel/SKILL.md` and `panel_client.py` first — those are the source of truth. Regenerate Codex agent files from the source rather than editing generated `.toml` by hand.

## For a new project

Drop the skill into your project and configure API access:

```bash
# 1. Copy the skill into your project
cp -R skills/panel /path/to/project/skills/panel

# 2. Configure API access
cp /path/to/project/skills/panel/.env.example /path/to/project/skills/panel/.env
# then edit .env and set PANEL_API_KEY (and optionally PANEL_BASE_URL)

# 3. First-time bootstrap inside the target project
cd /path/to/project
python skills/panel/panel_client.py setup
```

`setup` is an advisor — it inspects your teams/personas server-side, prints a proposed plan plus the exact shell commands to apply it, and waits for your confirmation. Approve it and it writes `.claude/panel_state.json` with your team/persona defaults. After that, the skill is ready for:

- `python skills/panel/panel_client.py discover` — list teams, personas, modes, models
- `python skills/panel/panel_client.py help "<topic>"` — pick the right intent
- `python skills/panel/panel_client.py ask "<question>"` — single-persona answer
- `panel_client.py debate|explore|challenge|review` — multi-persona modes

## For an existing project

Re-run `panel_client.py setup` whenever you want to refresh the state file or switch default team/persona. Targeted changes go through `panel_client.py state set <key> <value>` / `state clear` — don't hand-edit `.claude/panel_state.json`.

## Run Codex mode

Panel calls can be long-polling (especially `explore` / `debate` modes, which run each participant twice). Launch them as background tasks in your Codex harness so the main agent stays responsive.
