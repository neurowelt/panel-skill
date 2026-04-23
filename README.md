# Panel Skill

Harness skill that allows easy communication with Companion Panel API v1.

Multi-persona analysis: single-persona answers (`ask`), two-sided debates (`debate`), full panel deliberations with main-persona synthesis (`explore`), pressure-tests on a held position (`challenge`), and review passes (`review`).

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
| [`hello-panel`](./examples/hello-panel/) | `explore` | 2-minute onboarding. One call, two vantages, one synthesis — the core move in ~200 words. |
| [`panel-audience-read`](./examples/panel-audience-read/) | `explore` with downstream personas | Translate author-native writing → reader-native; surface where your POV and the audience's diverge. |
| [`panel-lateral-read`](./examples/panel-lateral-read/) | `explore` with lateral personas | Catch emergent / cross-cutting / second-order effects that linear upstream+downstream reads miss. |
| [`panel-debate-options`](./examples/panel-debate-options/) | `debate` | Two defensible options — the output isn't a winner, it's a clarified trade-off. |
| [`panel-challenge-belief`](./examples/panel-challenge-belief/) | `challenge` | Adversarial pressure on a held belief *before* you build on top of it. Returns a machine-readable verdict. |
| [`panel-minimize-drift`](./examples/panel-minimize-drift/) | mixed, at checkpoints | Pattern (not a skill): periodic panel calls at T=0/T=1/T=2/T=3 to catch agent drift while correction is cheap. |
| [`panel-harness`](./examples/panel-harness/) | `ask` → `review` → `review` | Goal → plan → run. Full three-phase episodic harness; each phase uses the panel pattern that fits its drift vector. |

### Reusable subskills

Most examples ship a thin wrapper skill you can lift into your own project. They preset the intent, the participant mix, and an archival convention on top of the base panel skill:

- [`audience-read`](./examples/panel-audience-read/.claude/skills/audience-read/) — downstream-heavy `explore` for reader-side reads
- [`lateral-read`](./examples/panel-lateral-read/.claude/skills/lateral-read/) — lateral-heavy `explore` for cross-cutting / emergent reads
- [`debate-options`](./examples/panel-debate-options/.claude/skills/debate-options/) — `debate` between two options, archived as a transcript
- [`challenge-belief`](./examples/panel-challenge-belief/.claude/skills/challenge-belief/) — `challenge` on a held belief, archived with verdict
- [`harness-setup-goal` / `harness-plan-goal` / `harness-run` / `harness-customize`](./examples/panel-harness/.claude/skills/) — the four phase skills that drive the full `panel-harness` loop

Drop any of them into your `.claude/skills/` alongside the panel skill — no example-specific wiring needed.

> [!NOTE]
> `explore` long-polls because `panel` mode runs each participant twice — dispatch it as a background task. Other intents (`ask`, `review`, `challenge`, `debate`, and anything in `parallel_with_main`) are a normal-cost roundtrip. Claude Code backgrounds panel calls automatically; other harnesses may need to wire that themselves.
