# Panel Skill

Harness skill that allows easy communication with Companion Panel API v1.

Multi-persona analysis: single-persona answers (`ask`), two-sided debates (`debate`), multi-perspective synthesis (`explore`), and focused reads with main-persona synthesis (`review`). Adversarial pressure on a held position is a `review` with lateral personas and a challenge-shaped prompt — see `examples/panel-challenge-belief/`.

## Installation for Claude Code

Add the marketplace:
```
/plugin marketplace add neurowelt/panel-skill
```

Then install the plugin:
```
/plugin install panel@panel-marketplace
```

After install, drop your API key into the skill's `.env`:
```bash
cp skills/panel/.env.example skills/panel/.env
# then set PANEL_API_KEY (and optionally PANEL_BASE_URL)
```

## Installation for Codex

Add the marketplace:
```bash
codex plugin marketplace add neurowelt/panel-skill
```

Then install `panel` from the marketplace in the Codex plugin directory. See [`.codex/INSTALL.md`](./.codex/INSTALL.md) for the full flow.

## First-time use

Useful first-time commands:
- `/panel discover` — list the teams, personas, modes, and models available to you
- `/panel help <question>` — ask the skill which panel option fits your problem
- `/panel setup` — propose an initial panel setup for the current working project (requires your confirmation before it writes state)

After `setup` has been applied, every subsequent call inherits team, main persona, project, and per-intent default participants from `.claude/panel_state.json` — the minimal call shape becomes just `/panel <intent> "$input"`.

## Examples

A set runnable examples under [`./examples/`](./examples/), each self-contained (Python stdlib only, panel skill vendored under `.claude/skills/panel/`). They cover the range — from a 2-minute "hello world" to a full agent harness that drives a goal across three phases with different panel patterns.

> [!NOTE]
> The vendored `panel/` skill under each example is a copy of the canonical [`skills/panel/`](./skills/panel/). If you change the canonical, run `scripts/sync-example-skills.sh` to propagate it, or `scripts/sync-example-skills.sh check` to verify no drift. Best option is to install from the marketplace.

| Example | Pattern | What it teaches |
|---|---|---|
| [`hello-panel`](./examples/hello-panel/) | `review` | 2-minute onboarding. One call, two vantages, one synthesis — the core move in ~200 words. |
| [`panel-lateral-read`](./examples/panel-lateral-read/) | `review` with lateral personas | Catch emergent / cross-cutting / second-order effects that linear upstream+downstream reads miss. |
| [`panel-challenge-belief`](./examples/panel-challenge-belief/) | `review` + lateral | Adversarial pressure on a held belief *before* you build on top of it. Verdict: holds up / does not hold up. |
| [`panel-minimize-drift`](./examples/panel-minimize-drift/) | mixed, at checkpoints | Pattern (not a skill): periodic panel calls at T=0/T=1/T=2/T=3 to catch agent drift while correction is cheap. |
| [`panel-harness`](./examples/panel-harness/) | `ask` → `review` → `review` | Goal → plan → run. Full three-phase episodic harness; each phase uses the panel pattern that fits its drift vector. |

### Reusable subskills

Most examples ship a thin wrapper skill you can lift into your own project. They preset the intent, the participant mix, and an archival convention on top of the base panel skill:

- [`lateral-read`](./examples/panel-lateral-read/.claude/skills/lateral-read/) — lateral-heavy `review` for cross-cutting / emergent reads
- [`challenge-belief`](./examples/panel-challenge-belief/.claude/skills/challenge-belief/) — `review` + lateral personas with a challenge-shaped prompt, archived with verdict
- [`harness-setup-goal` / `harness-plan-goal` / `harness-run` / `harness-customize`](./examples/panel-harness/.claude/skills/) — the four phase skills that drive the full `panel-harness` loop

Drop any of them into your `.claude/skills/` alongside the panel skill — no example-specific wiring needed.

> [!NOTE]
> Multi-persona intents (`explore`, `review`, `debate`) take ~8–15 min wall time — dispatch them as background tasks. Claude Code backgrounds panel calls automatically; other harnesses may need to wire that themselves.
