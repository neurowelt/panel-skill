---
name: debate-options
description: Use when the operator has two concrete, named options with real merit on both sides and is genuinely stuck between them — and wants the trade-off surfaced sharply rather than a recommendation. Symptoms — operator says "we've been going back and forth on X vs Y" / "both look defensible" / "I keep flipping"; the choice has multi-week consequences (not a daily call); both options have identifiable stakeholders who'd argue for them. NOT for single-position stress-testing, NOT for open exploration, NOT for quick gut-checks, NOT for three-plus-option comparisons.
---

# debate-options

## Core move

`debate` doesn't pick a winner. It runs a back-and-forth between personas with different stakes on the question, producing a transcript that reveals *what you're actually trading off* — typically by the third or fourth exchange, the real tension becomes visible in a way neither option's advocate could have named alone.

**The deliverable is a clarified trade-off sentence**, not a recommendation. "You're choosing between X-with-cost-A and Y-with-cost-B, both defensible; which cost do you prefer to pay?" If a debate returns something more conclusive than that, something went wrong — re-run with a different participant mix.

## Before firing — verify it's a debate question

Four checkpoints:

1. **Exactly two options, both named?** If the operator has three or more, redirect — eliminate to two first (via `ask` or `challenge`) and debate the finalists. If one option is "we'd do something like X," it's not yet concrete enough to debate.

2. **Both options have real merit?** If one option is obviously wrong and the operator just wants confirmation, redirect to `challenge` on the stronger one. Debate requires a live choice — genuine pull in both directions.

3. **Decision has multi-week consequences?** Debate takes 10–15 min of panel time. Right for quarter-shaping decisions; overkill for daily calls. If the operator could A/B the decision cheaply, they should — debate is for decisions that can't be cheaply reversed.

4. **Operator wants tension, not a recommendation?** Check explicitly: "This skill will surface the trade-off sharply, not pick a winner. Is that what you want?" If they want a recommendation, `ask` a senior persona or `challenge` the leading option. Don't use debate as a disguised recommendation engine.

All four must be yes. If any fails, name which and redirect.

## Steps

1. **Extract three things:**
   - **option A** — one sentence stating the first option concretely ("Build the eval tool in-house using our existing eval harness as a base").
   - **option B** — one sentence stating the second option concretely ("Adopt Humanloop as our primary eval platform").
   - **what's at stake** — 2–3 sentences of context: what the decision affects, who cares, what's irreversible about it. Debate is anchored by stakes; without them, personas argue in the abstract.

2. **Invoke `debate`. One bash call:**

   ```bash
   python .claude/skills/panel/panel_client.py debate \
     "<OPTION A> vs <OPTION B>. Context: <WHAT'S AT STAKE>. Surface the real trade-off; don't pick a winner." \
     --participants "upstream:<YOUR_UPSTREAM>,downstream:<YOUR_DOWNSTREAM>,lateral:<YOUR_LATERAL>"
   ```

   **Participant selection:**
   - **Three personas across three branches** is the default — one upstream, one downstream, one lateral. This gives three different axes for the trade-off to reveal itself.
   - **Two personas is the minimum.** Four is the maximum; more than four turns the transcript into noise.
   - **Avoid stacking one branch.** Three upstream personas produce three flavors of the same argument, not a debate — the branch mix IS the tension surface.

   Runs 10–15 min. Use Bash background mode.

3. **Write `transcripts/YYYY-MM-DD-<slug>.md`.** Slug is 3–5 words naming the choice (e.g., `in-house-eval-vs-vendor`, `postgres-vs-dynamodb`, `rewrite-or-patch`). Structure:

   ```markdown
   # <choice slug as title>

   **Date:** YYYY-MM-DD
   **At stake:** <what the decision affects>

   > Persona names from the panel team that ran this call; readers' teams will differ.

   ## Option A
   <verbatim>

   ## Option B
   <verbatim>

   ## Transcript
   ### <persona>
   <what they said>

   ### <persona>
   <what they said>

   [...repeat through the full back-and-forth...]

   ## Summary (main persona)
   <the clarified tension: "you're choosing between X and Y; here's what that actually means">

   ## Operator note (added after deciding)
   <which option the operator picked and why — or what additional information they needed to gather first>
   ```

4. **Don't route — pass through.** Debate has no verdict to branch on. Relay the summary verbatim and ask the operator: does the named tension match what they were feeling? If no, the participant mix was off — offer to re-run with a different constellation.

5. **Remind the operator** to add the "Operator note" section after they act. Debates are most useful revisited later — which option they picked, whether the named tension turned out to be the real one, whether they'd rerun with different personas.

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "Operator wants a recommendation — let me just synthesize one from the transcript." | The whole skill is built around *not doing that*. Debate's value is the tension; a recommendation collapses it. If they want a call, use `challenge` on the leading option. |
| "Both sides of the transcript are saying the same thing — the debate didn't work." | Re-check branch diversity in `--participants`. Three upstream personas produce three flavors of the same read; the fix is branch mix, not re-prompting. |
| "The operator has three options — let me just fire debate anyway." | No. Debate doesn't work with three. Eliminate to two first (via `ask` or `challenge`), then debate finalists. Three-option debate degenerates into voting. |
| "One option is clearly better — the debate will just confirm it." | Then the operator is stress-testing the leader, not deliberating. Use `challenge` on the leader instead. Debate requires genuine pull in both directions. |

## Red flags — stop and reshape

- Operator describes only one concrete option; the other is "some flavor of X" → not yet debate material; concretize option B first.
- Operator wants ranked output → debate doesn't rank; use `ask` with a senior persona or a structured comparison prompt instead.
- Three or more options → eliminate to two first.
- Transcript summary reads like a recommendation → something went wrong in the debate (branch mix, vantage drift, or over-weighted main persona); re-run with different `--participants`.

## Constraints

- **One debate per invocation.**
- **Write only to `transcripts/`.**
- **Never hand-edit `panel_state.json` or `.env`.**
- **Two-to-four participants from ≥2 branches.** Enforce branch diversity.

## Related

- Panel skill rules: `.claude/skills/panel/SKILL.md`
- Sibling demos:
  - `hello-panel` — 2-min onboarding, review intent, 2 vantages
  - `panel-challenge-belief` — stress-test one position, not deliberate between two
  - `panel-audience-read` — translate author-POV to reader-POV
  - `panel-lateral-read` — surface emergent/cross-cutting effects
  - `panel-harness` — full goal → plan → execute lifecycle
