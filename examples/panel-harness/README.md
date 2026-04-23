# panel harness — example

Small, runnable example of using the **panel** skill to drive a goal from intuition to execution. Three phases, each driven by a different panel pattern.

```
┌──────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────┐
│ Phase 1              │   │ Phase 2                 │   │ Phase 3             │
│ setup goal           │→ │ plan goal               │→ │ run harness         │
│ (ask, main persona)  │   │ (review, upstream+main) │   │ (review per episode)│
│ → goal.md            │   │ → goal-plan-N.{md,json} │   │ → signals + verdict │
└──────────────────────┘   └─────────────────────────┘   └─────────────────────┘
```

Self-contained. The panel skill is vendored under `.claude/skills/panel/`. Python stdlib only.

## The three phases

Each phase has a dedicated **harness skill** under `.claude/skills/` that tells Claude Code exactly how to drive it.

| Phase | Skill | Panel pattern | Why that pattern | Output |
|---|---|---|---|---|
| 1 — Goal setup | [`harness-setup-goal`](.claude/skills/harness-setup-goal/SKILL.md) | `ask` (single main persona, `answer` mode) | The main persona has memory of your prior work. One voice, with context — the right thing to turn a vague direction into a specific goal. | `goal.md` with *Why this goal exists* section |
| 2 — Goal planning | [`harness-plan-goal`](.claude/skills/harness-plan-goal/SKILL.md) | `review` (`parallel_with_main`, main + 2 upstream personas) | Multiple independent reads catch planning blind spots; the main persona synthesizes the final plan. | `goal-plan-N.md` (per-increment sections) + `goal-plan-N.harness.json` (machine list). `goal.md` is never edited. |
| 3 — Execution | [`harness-run`](.claude/skills/harness-run/SKILL.md) | Per-episode upstream review — default `review` (upstream-only `parallel_with_main`), with `challenge` / `explore` / `ask` available when the question changes. | Upstream personas model user understanding. They're the voice that reads progress. | signal files + verdicts; archived passes on retry |

Plus one off-main-flow skill invoked by the operator after running episodes:

| Skill | Panel pattern | When to use | Output |
|---|---|---|---|
| [`harness-customize`](.claude/skills/harness-customize/SKILL.md) | `explore` (broad upstream + downstream + lateral mix) | After ≥ 3 episodes where the same kind of objection keeps surfacing across unrelated increments — or when porting the harness to a new domain. Tunes the *soft* parts (agent prompts, scout phase order, skill wording) while leaving signal/episode infrastructure frozen as hard rails. | `proposal-YYYY-MM-DD.md` — operator diffs by hand; nothing auto-applied. |

## Prereqs

- Python 3.9+ (stdlib only)
- Claude Code (`claude` CLI) for the agents and skills
- `PANEL_API_KEY` — get one at Profile → API Access on panel.humx.ai

## One-time setup

```bash
cd examples/panel-harness
cp .env.example .env                                             # paste your PANEL_API_KEY
python .claude/skills/panel/panel_client.py setup                # PROPOSES team/persona defaults + prints `state set` commands
# ... run the printed `panel_client.py state set ...` lines to apply ...
python .claude/skills/panel/panel_client.py discover             # sanity check
```

## Running from scratch (teaches all three phases)

```bash
cd examples/panel-harness
python harness/scout.py              # → "phase 1 — no goal.md yet. run harness-setup-goal"
```

Open Claude Code in this directory and invoke the `harness-setup-goal` skill. When it's done, tick scout again → it'll point at phase 2. And so on. Phase 3 is the main loop.

## Skipping straight to phase 3 (already-planned goal)

The example ships with reference goal files as `.example`. Phase-3 needs three things in place: the stable goal, the numbered plan's prose + machine files, and `config.active_plan` pointing at the plan.

```bash
cp goal.md.example                     goal.md
cp goal-plan-1.md.example              goal-plan-1.md
cp goal-plan-1.harness.json.example    goal-plan-1.harness.json
# then edit harness/config.json — set "active_plan": "goal-plan-1.harness.json"
python harness/scout.py                # now points at episode-framer for episode 1
```

The example goal: *plan a 3-day coastal trip for a first-time visitor.* Three increments (destination → dates+transport → itinerary). Nothing technical — the point is to see the review pattern work on a task everyone understands.

## Phase 3 — the scout loop

```bash
python harness/scout.py              # human-readable status
python harness/scout.py next         # one machine-readable line (for run_scout.sh)
python harness/scout.py advance      # after verdict=proceed
python harness/scout.py retry        # after verdict=revise (archives to pass-K/)
python harness/scout.py goal         # increment ledger
```

Two drive modes:

- **Manual:** tick scout, invoke the named agent in Claude Code, tick again.
- **Autonomous:** `harness/run_scout.sh` — while-loop wrapper that spawns `claude --agent <name>` between ticks and handles verdicts automatically. Pause with `touch harness/.scout-pause`.

## Episode files (phase 3)

Inside each episode dir (`harness/episodes/episode-N/`). Each phase produces a **result** (rich `.md`, for humans) plus a tiny **signal** (`{"done": true, "results": "ok"}`, for the scout). Signals are never rich — all content lives in the `.md`.

| Phase file | Writer | Shape |
|---|---|---|
| `increment.json` | scout (on bootstrap) | snapshot of which increment this episode targets |
| `frame.md` | episode-framer | *Task spec*, *Goal alignment*, *Done criteria*, *Watch out for*, *Incorporates revise instructions*, *Inherited constraints from prior forensics* |
| `frame-signal.json` | episode-framer | `{"done": true, "results": "ok"}` |
| `<artifact>.md` | worker | The actual product (name from `increment.json.artifact_name`). Ends with a `## Worker notes` trailer: *Summary*, *Inherited decisions*, *Assumptions*, *Open questions*. |
| `work-signal.json` | worker | `{"done": true, "results": "ok"}` |
| `forensics.md` | forensics | *Done criteria satisfied/unmet*, *Goal alignment check*, *What worked*, *What failed (with why + new constraints for future work)*, *Unexamined assumptions* |
| `forensics-signal.json` | forensics | `{"done": true, "results": "ok"}` |
| `review.md` | upstream-review | *Position*, *Main synthesis summary*, *Upstream contributions*, *Strongest objection*, *Overlooked factors*, *Would change mind if*, *Goal alignment verdict*, *Verdict + confidence + next step*, *Revise instructions* (if revise) |
| `review-signal.json` | upstream-review | `{"done": true, "results": "<verdict>"}` where verdict is `proceed` / `revise` / `walled` |

Archived passes: `harness/episodes/episode-N/pass-K/` on retry. The scout moves everything except `increment.json` into the pass dir.

## What makes this a panel example

Each phase picks a **different** panel pattern for a reason:

- **Phase 1 (`ask`)**: single main persona with memory. One voice is right when the question is "what do I actually care about?"
- **Phase 2 (`review` = parallel_with_main)**: multiple independent reads + synthesis. Right when the question is "how do we break this down?" — the independent reads catch blind spots.
- **Phase 3 (default `review` again, upstream-only)**: upstream personas give independent progress reads. Right when the question is "does this move us forward toward what we said we wanted?"

The alternative phase-3 intents (`challenge`, `explore`, `ask`) exist for when the question genuinely changes — see `harness-run/SKILL.md` for the table.

## Limits of v0

- Manual agent invocation is primary. `run_scout.sh` autonomous mode assumes `claude --agent <name>` works in your environment.
- One active increment per episode; no parallel episodes. Increment dependencies can form a DAG (via `depends_on`), but the scout walks it one-at-a-time.
- One-file artifacts per increment. Multi-file work requires edits to the worker prompt.
- `panel_client.py` + `SKILL.md` are vendored. If you install the panel skill globally, replace these with symlinks.
