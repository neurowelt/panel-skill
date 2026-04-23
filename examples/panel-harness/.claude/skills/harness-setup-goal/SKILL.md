---
name: harness-setup-goal
description: Use when the panel harness has no goal.md yet — operator needs to turn a vague sense of "I should work on something" into a specific goal tied to their actual context. The harness models any system against the operator's persona; the subject can be technical (a refactor, an architecture decision, a research question) or not. Symptoms — scout.py prints `no-goal-statement`; operator describes wanting to start but can't name the specific thing.
---

# Phase 1 — Setup the goal

**Terminology note.** "panel" is overloaded:
- *the panel skill* = `.claude/skills/panel/` — the thing you invoke
- *intent* = one of `ask` / `debate` / `explore` / `review` / `challenge`
- *mode* = server-side response shape (e.g. `answer`, `panel`, `parallel_with_main`)

## Overview

Turn a vague direction into a concrete goal the rest of the harness can build on. The panel's main persona has memory of the operator's prior work — one voice with context is the right tool to name what's actually pressing.

**Core rule: the `ask` intent call is mandatory before writing `goal.md`.** The operator who's stuck on a goal is the worst judge of their own notes.

## When to use

- `goal.md` does not exist at the example root
- `scout.py next` prints `no-goal-statement`
- Operator describes the thing in notes / fragments / TODOs rather than a stated goal

## When NOT to use

- `goal.md` already exists — confirm with operator and move aside before overwriting.
- Operator has written a clear unambiguous goal statement and just wants it formatted — skip, write the file directly.
- The goal is a single narrow task — use `panel_client.py ask` or `challenge` directly on the task, don't run the harness.

## Steps

1. **Ask the operator for a seed** — one sentence on domain or discomfort. If they have notes, read them, but do not treat notes as the goal.

2. **Invoke the `ask` intent.** One Bash call:

   ```bash
   python .claude/skills/panel/panel_client.py ask "What is the single most important, most specific thing for me to tackle next around: $SEED? Answer as a goal statement I could work on continuously with autonomous coding/research agents. Be concrete — name the thing, software, research, a thing - don't gesture at a theme."
   ```

3. **Show the response verbatim.** Ask: does this match what's on your mind? Too narrow / too broad / wrong angle?

4. **Iterate.** Re-run `ask` with steering appended until operator accepts. 1–3 iterations typical.

5. **Write `goal.md`** — title + *Why this goal exists* section drawn from the accepted answer. Optionally include *Constraints the plan must respect* and *What this goal deliberately does not settle* if the operator has named any. No increment sections yet — that's phase 2.

6. **Tell operator:** "Phase 1 done. Run the `harness-plan-goal` skill next."

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "Operator said skip the panel skill — that's autonomy." | They're stuck. Stuck + notes ≠ a goal. The `ask` call is *why* they'd unstick. |
| "They already wrote notes — just format them." | Notes are wishes or fragments, not goals. Formatting wishes into `goal.md` encodes the ambivalence into every later phase. |
| "An `ask` call costs minutes — just write it." | A bad goal costs hours of episodes that miss what the operator actually wanted. |
| "Push back once then comply — that's good general behavior." | Not for this phase. Skipping the `ask` call here means skipping phase 1. |
| "I can infer the goal from the operator's history / notes / open threads." | History is evidence, not direction. Using it as direction amounts to "keep doing what you've been doing" — often wrong. |

## Red flags — stop and run `ask`

- About to write `goal.md` without having invoked `ask` at least once
- Formatting the operator's notes into `goal.md` without an `ask` call
- Concluding "simple enough, panel skill is overkill" — that's a phase-2/3 judgment, not phase-1
- Inferring the goal from history instead of asking directly

## If the operator refuses `ask` after one push-back

Do not silently comply. Write `goal.md` with a prominent `## Open questions` section listing verbatim the ambiguities you'd have put to `ask` — missing object, missing scope, missing success criterion, missing constraint. The deferral must be visible so phase 2 sees what was skipped.

## Common mistakes

- **Treating notes as the goal.** They're the *input*, not the output.
- **Skipping to phase-2 pattern-matching.** "It looks like a 3-increment plan" — irrelevant. Phase 1 outputs the *why*, not the *how*.
- **Writing a generic `goal.md`.** If the persona's answer is generic, that's memory cold — surface that, don't paper over.
- **Leading with the solution.** "Port to Rust because Rust" is a solution looking for a goal. Surface what's actually frustrating first.
- **Hand-editing `goal-plan-*.harness.json`, `harness/config.json`, or any episode directory.** Phase 1 writes only `goal.md`.

## Constraints

- Write only `goal.md`.
- One bash call per iteration. Not batched.
- Never touch `.env` or `panel_state.json` directly — the panel skill's rules apply.

## Related

- Next: `harness-plan-goal`
- The panel skill: `.claude/skills/panel/SKILL.md`
