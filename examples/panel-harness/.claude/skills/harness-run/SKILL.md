---
name: harness-run
description: Use when `goal.md` and `goal.harness.json` both exist and the operator is ready to walk increments. Explains the scout's 4-phase episodic loop, the four work agents, and — critically — when to use which panel intent for upstream review. Default review pattern is `review` (parallel_with_main, upstream personas). This skill also documents when to reach for `challenge` / `explore` / `ask` instead.
---

# Phase 3 — Run the harness

**Purpose.** Execute the planned increments one episode at a time. Four agents per episode (episode-framer → worker → forensics → upstream-review) each write a `.md` result plus a tiny `<phase>-signal.json` (shape: `{"done": true, "results": "ok"}`; review's `results` carries the verdict). The scout routes on the review's `results`; passes archive on retry.

**Panel pattern for this phase:** per-increment *upstream review* — default `review` (parallel_with_main with upstream personas). The upstream personas model user understanding, so they're the right voice for "is this progress?" Alternatives are listed below — use them when the review's question isn't progress.

## Trigger

`goal.md` exists, `goal.harness.json` exists, and at least one increment has `state: "pending"` or `state: "in_progress"`.

## Prereqs

- Both phase-1 and phase-2 artifacts present
- Panel skill configured; `panel_client.py setup` applied
- A project set in panel state if you want memory across episodes (recommended)

## Scout mechanics (refresher)

Each episode targets exactly one increment. Inside an episode, four phases run in order:

| Phase | Agent | Result file (rich, markdown) | Signal file (tiny) |
|---|---|---|---|
| 1 | `episode-framer` | `frame.md` | `frame-signal.json` |
| 2 | `worker` | `<artifact>.md` (name from `increment.artifact_name`) | `work-signal.json` |
| 3 | `forensics` | `forensics.md` | `forensics-signal.json` |
| 4 | `upstream-review` | `review.md` | `review-signal.json` (`results` = verdict) |

Signal shape is uniform `{"done": true, "results": "ok"}`, except review's signal where `results` is the verdict (`"proceed"` / `"revise"` / `"walled"`) for scout routing. All human content lives in the `.md` file. Humans should not need to read any signal JSON.

Scout commands:

- `python harness/scout.py status` — human-readable state
- `python harness/scout.py next` — single machine-readable line for shell loops
- `python harness/scout.py advance` — after `results: proceed`, bump to next increment
- `python harness/scout.py retry` — after `results: revise`, archive to `pass-K/` and restart from episode-framer
- `python harness/scout.py goal` — increment ledger

Verdicts on `review-signal.json.results`:

| `results` | Scout action |
|---|---|
| `proceed` | Mark increment `advanced`, bootstrap next pending increment's episode |
| `revise` | Archive current signals + `.md` reports + artifact to `pass-K/`, episode-framer re-runs |
| `walled` | Stop. Operator reads `review.md` and resolves. |

## Two ways to drive the loop

- **Manual:** `python harness/scout.py` prints which agent to run next; invoke that agent in Claude Code; repeat.
- **Autonomous:** `harness/run_scout.sh` — while-loop wrapper that spawns `claude --agent <name>` between ticks and calls `advance`/`retry` on verdicts. Pause with `touch harness/.scout-pause`.

## Panel intent choice for upstream-review — the interesting decision

The upstream-review agent always frames a two-part position (local fit + goal alignment) and runs one panel call to evaluate it. **Which intent it uses depends on what question it's asking.**

| Intent | Mode | When to use | What you get back |
|---|---|---|---|
| **`review`** (default) | `parallel_with_main` | *"Is this progress toward the goal?"* Most episodes. | Upstream contributions (independent reads) + main-persona synthesis. No structured verdict — agent derives one. |
| **`challenge`** | dedicated adversarial endpoint | *"Will this survive objections?"* Use when the operator has committed to a direction and wants to stress-test, not re-frame. | Structured: `holds_up`, `confidence`, `strongest_objection`, `would_change_mind_if`, `overlooked_factors`. |
| **`explore`** | `panel` (two-stage synthesis) | *"What are the deep perspectives on this?"* Use for high-stakes increments where you need a full multi-angle read, not just progress vibes. | Two-stage: each participant analyzes, then re-analyzes with enriched context, then main synthesizes. |
| **`ask`** | `answer` | *"What does one voice say quickly?"* Use for trivial increments where a full review is overkill. | Single persona answer. |

**Default:** `review`. Deviate only when the question genuinely changes.

### Participant selection

- **`review`** — upstream-only (`upstream:conceptual_provocateur, upstream:domain_diver, upstream:ground_truth_reporter`). These model user-facing understanding of progress.
- **`challenge`** — upstream-only gives the cleanest adversarial attack from the user's vantage. Adding a downstream persona (e.g. `downstream:coherence_auditor`) helps when the objection space includes implementation concerns.
- **`explore`** — broad mix, upstream + downstream + lateral, to surface perspectives the operator hasn't already considered.
- **`ask`** — main persona only.

The upstream-review agent (`.claude/agents/upstream-review.md`) defaults to `review` with upstream-only participants. Edit that agent's prompt if a particular episode needs a different intent — the scout is pattern-agnostic, it only cares that `review-signal.json` ends up with a `results` value the scout recognizes (`proceed` / `revise` / `walled`).

## Handling `revise`

When `results: revise` comes back, `review.md`'s **Revise instructions** section tells the next episode-framer pass what to change. The scout archives the failed pass to `pass-K/` and starts fresh. The episode-framer *must* incorporate the revise instructions (see `episode-framer.md`'s contract — **Incorporates revise instructions** is a required section on retry passes).

If you see the same **Strongest objection** across two consecutive passes, that's a signal the episode-framer isn't actually incorporating the feedback. Check `pass-*/frame.md` to verify. If the framer is honestly trying and still can't satisfy the objection, the problem is upstream — the goal or the increment itself is wrong. That's when `results: walled` is the right answer.

## Handling `walled`

`walled` stops the scout. Operator reads the review and decides:

- **Goal is wrong** → edit `goal.md`, maybe regenerate `goal.harness.json` via `harness-plan-goal`.
- **Increment is wrong** → edit `goal.harness.json` (split, merge, or reorder), run `scout.py retry` on the current episode.
- **Walled in error** → manually edit `review-signal.json` to `verdict: proceed` (or delete the signal and re-run upstream-review with steering).

No autonomous recovery — walled requires operator judgment.

## Constraints for agents in this phase

- **Agents stop after writing their signal.** No self-review, no chaining, no "helpfully" running the next phase.
- **One panel call per agent run** — the upstream-review agent picks one intent, makes one Bash call.
- **Relay panel errors verbatim** — if `panel_state.json` is missing, the panel client tells the operator to `setup`; pass that through, don't bootstrap state.
- **Never touch `.env` or `panel_state.json` directly** — see `.claude/skills/panel/SKILL.md`.

## Related

- Previous: `harness-plan-goal` — produces `goal.harness.json`.
- Work agents: `.claude/agents/{episode-framer,worker,forensics,upstream-review}.md`.
- Scout + runner: `harness/scout.py`, `harness/run_scout.sh`.
- Panel skill: `.claude/skills/panel/SKILL.md`.
