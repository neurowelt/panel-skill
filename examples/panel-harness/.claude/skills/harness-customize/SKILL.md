---
name: harness-customize
description: Use when operator has run episodes and feels persistent friction with how the harness thinks, or when pointing the harness at a new domain where the default agent prompts and phase order seem off. Use when the operator wants to tailor the harness shape (agent prompts, scout PHASES, skill wording) to how their main persona and upstream personas actually reason — without touching signal/episode infrastructure. Symptoms — the same kind of objection keeps appearing in review.md across unrelated increments; operator says "this agent asks for the wrong things"; harness was ported from another project and hasn't been adapted.
---

# Harness customize

**Required reading before applying anything proposed by this skill:** **`superpowers:writing-skills`**. The proposals this skill produces are edits to agent prompts, scout phases, and harness skill wording — in other words, skill authoring. Writing-skills teaches the RED-GREEN-REFACTOR cycle for prose-as-process-code (baseline failure pressure-tests with subagents → write the change addressing specific rationalizations → close loopholes → re-test until bulletproof). Applying customize proposals without that discipline tends to overfit the harness to whichever recent friction was loudest and introduce new failure modes. If `superpowers:writing-skills` isn't installed, install the `superpowers` plugin first (Claude Code plugin, via the superpowers-dev marketplace).

## Overview

Operator-invoked tuning skill. Surfaces persona-driven suggestions for changing the harness's *soft* parts (agent prompts, phase ordering, skill wording) while leaving the *hard* infrastructure alone. Output is a proposal document — nothing is auto-applied.

**Core rule: the `explore` intent is mandatory.** Generative multi-perspective reads beat a single persona's proposals for customization. One voice will suggest only what one voice values.

## When to use

- Operator has run ≥ 3 episodes and the same kind of objection keeps appearing in `review.md` across unrelated increments
- Harness was ported from another project and the default agent prompts don't fit the operator's domain
- Pointing the harness at a new domain and operator wants persona input on prompt shape before the 4-agent loop kicks off
- Operator says "this agent asks for the wrong things" or "the forensics structure misses what I actually care about"

## When NOT to use

- First time running the harness — there's no friction to tune against yet. Run a few episodes first.
- Friction is in a single episode, not systemic — edit that one agent's prompt directly, don't summon a panel.
- Infrastructure (signal shape, episode layout) seems wrong. That's not a customize-skill problem. Edit the code, update the harness skills to match, version up.

## Hard rails — things this skill MUST NOT propose changes to

The personas will cheerfully suggest rewriting anything. The operator must resist.

- **Signal JSON schema.** Every signal stays `{"done": true, "results": "ok"}` (or the verdict form for review). Changing this breaks scout routing.
- **Signal / result filename conventions.** `<phase>-signal.json` + `<phase>.md` (or the worker's `<artifact>.md`). The scout scans by name.
- **Episode directory structure.** `harness/episodes/episode-N/` with `increment.json` + signals + results + `pass-K/` archives. The scout writes here.
- **`harness/config.json` key names.** `active_plan`, `current_episode`. Renaming breaks the scout.
- **`goal.md` / `goal-plan-N.{md,harness.json}` file naming.** These are the contract between phases 1–2 and phase 3.

If the panel proposes changing any of the above, say so to the operator and drop that item from the proposal. Do not write it down as if it were a valid suggestion.

## Soft targets — what the skill MAY propose changes to

- Agent `.md` prompts under `.claude/agents/` — content, structure, emphasis, constraints, red-flag lists.
- Scout's `PHASES` list in `harness/scout.py` — adding sub-phases, splitting one agent's work into two, reordering.
- Harness skill `.md` prompts (setup-goal, plan-goal, run) — wording, rationalization tables, common mistakes.
- Participant selection in `upstream-review.md` for phase-3 `review` / `challenge` / `explore` / `ask` calls.
- The shape of sections *inside* result `.md` files (e.g. adding a "Worker uncertainty" section to the artifact trailer).

## Steps

1. **Gather context.** Read:
   - All agents (`.claude/agents/*.md`)
   - All harness skills (`.claude/skills/harness-*/SKILL.md`)
   - Scout's `PHASES` list (`harness/scout.py`)
   - The 3 most recent episodes' `review.md` + `forensics.md` (if they exist) — these are the friction evidence
   - `goal.md` and the active `goal-plan-N.md`

2. **Frame the ask.** Write a one-page summary of the current harness shape + the friction evidence. Quote specific lines from recent `review.md` / `forensics.md` where the same objection recurred.

3. **Invoke `explore`.** One Bash call:

   ```bash
   python .claude/skills/panel/panel_client.py explore \
     "$FRAMING" \
     --participants "upstream:conceptual_provocateur,downstream:coherence_auditor,lateral:iterative_craftsperson"
   ```

   Broad mix — upstream (user understanding), downstream (implementation coherence), lateral (alternative framings). `explore` runs `panel` mode — two-stage synthesis. Costly but generative; right for "what could this be?"

4. **Write `proposal-YYYY-MM-DD.md`** at the project root:

   ```markdown
   # Harness customization proposal — <date>

   ## Friction evidence
   Quoted lines from recent review.md / forensics.md showing the recurring objection.

   ## Panel synthesis
   One paragraph distillation of the main persona's synthesis.

   ## Suggestions — soft targets
   For each suggestion:
   - **File**: e.g. `.claude/agents/upstream-review.md`
   - **Change**: what to add / modify / remove, concrete enough to diff
   - **Rationale**: which persona raised this and why it addresses the friction

   ## Suggestions dropped (hard rails)
   If any persona suggested changes to signal schema / episode layout / config keys / file-naming contracts — list those here so the operator sees what was filtered and why.
   ```

5. **Hand the proposal to the operator.** They review, pick, edit the soft-target files by hand. Do not apply changes automatically.

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "The panel said change the signal schema to include confidence — it's a good idea." | Hard rail. Drop the suggestion from the proposal and note the drop. Adding fields to signals is possible only through a harness version bump, not a customize pass. |
| "This friction is obvious — I'll just edit the agent directly without a panel call." | Maybe correct for one-off friction. If the same objection appeared 2+ times in `review.md`, that's not one-off — run the skill. |
| "`ask` would be faster than `explore`." | `explore`'s two-stage synthesis is the point. Single persona proposals are under-generative for this phase. Use `explore`. |
| "Apply the proposal automatically to save the operator a step." | No. Customization is a judgment call. The operator diffs and picks — that's the review gate that keeps personas from drifting the harness off-contract. |

## Red flags

- About to edit a signal JSON shape or episode path to match a panel suggestion — **stop, that's a hard rail**
- About to apply the panel's proposals directly without the `proposal-*.md` review step — **stop, let the operator pick**
- Using `ask` or `review` instead of `explore` — **stop, this phase wants generative breadth**

## Constraints

- One `explore` call per customize run. No chaining.
- Write only `proposal-YYYY-MM-DD.md`. Never edit agents, skills, scout, or config directly in this skill. That is the operator's job after reading the proposal.
- Never touch `.env` or `panel_state.json` — the panel skill's rules apply.

## Related

- The panel skill: `.claude/skills/panel/SKILL.md`
- What the operator edits after reading the proposal: `.claude/agents/*.md`, `harness/scout.py`, `.claude/skills/harness-*/SKILL.md`
