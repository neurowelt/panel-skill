---
name: harness-plan-goal
description: Use when goal.md exists but no active plan is set in config — a stated goal needs to be broken into connected increments before the scout can walk them. Also use when re-planning an existing goal (produces a new goal-plan-N, leaves goal.md and prior plans intact). Symptoms — scout.py prints `no-goal-plan`; operator has a goal but no increment list; operator wants to try a different breakdown of an existing goal.
---

# Phase 2 — Plan the goal into increments

**Terminology note.** See `harness-setup-goal/SKILL.md` → Terminology note. Intents are backticked (`ask`, `review`, etc.); *mode* is a backticked response shape; *the panel skill* is always named in full.

## Overview

Break the goal into the connected increments it actually needs. Each is one atomic unit of work — a build task, a research question, a deliverable — that moves the whole initiative forward.

**Core rule: the `review` intent call is mandatory, even for simple-looking plans.** Phase 2 is not about validating a plan the operator already has. It's about surfacing the increment the operator forgot or the dependency they have backwards.

`review` uses `parallel_with_main` mode — each participant gives an independent proposal, main persona synthesizes. Independent reads catch planning blind spots that a single perspective (including the operator's) can't see by construction.

## When to use

- `goal.md` exists with a populated *Why this goal exists* section
- `harness/config.json → active_plan` is `null`, OR operator wants to re-plan an existing goal
- `scout.py next` prints `no-goal-plan`

## When NOT to use

- The goal is one decision (not 2+) — skip the harness entirely; use `panel_client.py challenge` or `review` directly on the decision.
- `goal.md` has no *Why this goal exists* section — run `harness-setup-goal` first.

## File layout this phase produces

Plans are numbered. Each plan has a prose file and a machine file:

```
goal.md                          # stable — the "why", never edited by this phase
goal-plan-1.md                   # first plan attempt — per-increment sections
goal-plan-1.harness.json         # first plan attempt — machine list for the scout
goal-plan-2.md                   # second plan attempt (if you re-plan)
goal-plan-2.harness.json
...
harness/config.json              # active_plan points at the currently-walked plan
```

When running this skill, pick the next free N (scan `goal-plan-*.md` / `.harness.json`; next integer above max). Write both files. Update `config.active_plan`. The prior plan(s) remain on disk as history.

## Steps

1. Read `goal.md` in full.

2. **Invoke the `review` intent.** One Bash call:

   ```bash
   python .claude/skills/panel/panel_client.py review \
     "Given this goal, propose the connected increments it actually needs — as many as the goal demands, as few as possible. Each: id, name (≤5 words), scope (one sentence), depends_on (ids), retry_risk (low/medium/high). Dependencies must respect natural order. Goal:\n\n$(cat goal.md)\n\nOperator's initial sketch (if any): $OPERATOR_SKETCH" \
     --participants "upstream:conceptual_provocateur,upstream:domain_diver,upstream:ground_truth_reporter"
   ```

   The `--participants` flag takes *side* participants only — the main persona is already configured in state and passed separately by the client. `parallel_with_main` mode enforces 2–3 side participants server-side (verified: HTTP 400 at 4 or more, likely same at 0 or 1 — see "Common mistakes" below). The main synthesizes after; it does not count toward the 2–3.

3. **Show synthesis + upstream contributions to the operator.** Ask specifically: did any persona propose an increment the operator's sketch missed? Did anyone reorder dependencies?

4. **Iterate.** Re-run `review` with steering appended until operator accepts. 1–3 iterations typical.

5. **Pick N.** Scan the project root for existing `goal-plan-*.md` / `goal-plan-*.harness.json`. Pick the next integer above the highest existing (first run: `N=1`).

6. **Write `goal-plan-N.md`** with a brief plan-shape preamble + one section per increment: `## Increment A — name`, with `### What to decide`, `### Definition of done`, `### Alignment check (for the panel skill)`, `### Dependencies`. End with an increment-plan table.

7. **Write `goal-plan-N.harness.json`** — one entry per increment in dependency order:

   ```json
   {
     "goal_file": "goal.md",
     "plan_file": "goal-plan-N.md",
     "increments": [
       {
         "id": "A",
         "name": "<≤5 words>",
         "section": "Increment A",
         "scope": "<one sentence>",
         "artifact_name": "<filename>.md",
         "depends_on": [],
         "retry_risk": "low",
         "state": "pending",
         "first_episode": null,
         "last_episode": null
       }
     ]
   }
   ```

8. **Update `harness/config.json`** — set `active_plan` to `"goal-plan-N.harness.json"`. Leave `current_episode` alone (episode numbering is cumulative across re-plans).

9. **Tell operator:** "Phase 2 done — `goal-plan-N` is active. Run `python harness/scout.py` or the `harness-run` skill."

## Re-planning (N > 1)

If the operator asks to replan an existing goal — for example, the scout walled, or phase-3 forensics keeps revealing the same missing concern — run this skill again. It will write `goal-plan-{N+1}.md` + `.harness.json` and point `config.active_plan` at them. The prior plan's files and episodes stay on disk as history. `goal.md` is not touched. No need to move anything aside.

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "Operator gave me a 3-item plan — just write it." | `review` isn't validating the plan. It's catching the increment the operator forgot, or the wrong dependency order. Skipping means skipping phase 2. |
| "The plan looks coherent to me." | "Coherent to me" ≠ "complete + correctly ordered." Blind spots are by definition things that don't look missing. |
| "Time is tight; `review` is 8–12 min." | 8 min of `review` vs. a wrong increment costing an entire episode (hours). |
| "Overriding the operator's plan unilaterally is paternalistic." | Correct — don't. `review` synthesizes *against* the operator's plan. Operator's sketch is preserved as `$OPERATOR_SKETCH` steering, not replaced. |
| "I'll ask ONE clarifying question inline instead of running `review`." | Inline questions surface *your* concerns. `review` surfaces things neither you nor the operator saw. Different tool for a different failure mode. |

## Red flags — stop and run `review`

- About to write `goal.harness.json` without invoking `review`
- Reasoning "the plan is simple, `review` is overkill" on a 2–4 item list — that's the exact failure mode this phase prevents
- Only checking the operator's plan for internal consistency, not for gaps
- Adding or reordering increments unilaterally instead of through `review`

## Common mistakes

- **Using `ask` instead of `review`.** Single persona misses planning blind spots. Phase 2 demands multiple independent reads — that's `parallel_with_main`.
- **Putting the main persona in `--participants`.** The server counts `--participants` literally — it does not dedup against the main persona. Passing `"PersonaX,upstream:a,upstream:b"` with `--main PersonaX` counts as 3 (inside the 2–3 range, so the server accepts the submit), but it makes main both an independent participant AND the synthesizer — redundant and semantically off for `parallel_with_main`. Pass distinct *side* participants in `--participants`; main is already configured in state and passed separately by the client. The count limit itself is empirical: server returns HTTP 400 at 4+ or at 1 or 0 participants in the list, whatever their identity.
- **Cycles in `depends_on`.** Must be a DAG. Reject and re-prompt.
- **Editing `goal.md`.** Phase 2 never touches `goal.md` — that's phase 1's artifact, meant to stay stable across re-plans. Per-increment sections go in `goal-plan-N.md`.
- **Touching any episode directory.** Phase 2 writes `goal-plan-N.md`, `goal-plan-N.harness.json`, and one field in `harness/config.json`. That's it.

## Constraints

- Write only `goal-plan-N.md`, `goal-plan-N.harness.json`, and one field (`active_plan`) in `harness/config.json`.
- Never edit `goal.md` — it is phase 1's stable output.
- One bash call per iteration.
- Never touch `.env` or `panel_state.json` — the panel skill's rules apply.

## Related

- Previous: `harness-setup-goal`
- Next: `harness-run`
- The panel skill: `.claude/skills/panel/SKILL.md`
