---
name: audience-read
description: Use when the operator has written a piece of content (README, design doc, proposal, brief, decision write-up) and wants to know how it will land with a specific audience that is not themselves. Symptoms — operator says "does this make sense to X?" / "would a Y understand this?" / "I think this is clear but I'm too close to it." NOT for critiquing the content itself, NOT for checking whether a plan is good, NOT for stress-testing a position — only for evaluating how an existing written artifact reads to a reader who doesn't share the author's context.
---

# audience-read

## Core move

You're not reviewing the content. You're simulating a specific reader reading it, via downstream personas whose job is modeling reception rather than generation. The output tells the operator *where their POV and the reader's POV diverge* — which is a different finding than "your plan has a gap" or "your position is weak."

## Before firing — verify it's an audience-read, not something else

Three checkpoints:

1. **Is there a specific audience named?** "Our customers" or "people" is too vague. Usable: "a VP of engineering at a 200-person B2B SaaS, skeptical of AI tooling" / "a senior backend engineer who's shipped LLM features before but has never used our framework" / "an operator on the incident-response team reading this at 3am." Vague audience → output is generic and useless; push back and ask for specifics before firing.

2. **Is there a written artifact?** A path to a file, or the content inline. If the operator wants a read on something that doesn't exist yet ("does the idea of X land?"), redirect to `panel_client.py ask` — they need to draft first, then audience-read.

3. **Is the operator asking about *reception*, not *content*?** "Is this plan any good?" is a content question — use `review` or `challenge`. "Will this read as professional?" is a reception question — fire `audience-read`. If the operator's ask conflates both, split it and ask which they want first.

All three must be yes. If any is no, redirect and name which intent fits instead.

## Steps

1. **Collect two inputs from the operator:**
   - **source** — the content to be read. Preferably a file path (`../panel-harness/README.md`, `./drafts/proposal.md`). Inline text is fine for short excerpts.
   - **audience** — a one-paragraph description. Role, context, skepticism level, what they already know, what they don't, what they care about. Specificity matters: "seasoned LLM engineer" beats "engineer," and "VP of eng who's burned cash on AI tooling that didn't ship" beats "executive."

2. **Invoke `explore` with downstream-heavy participants. One bash call:**

   ```bash
   python .claude/skills/panel/panel_client.py explore \
     "<AUDIENCE DESCRIPTION>. Read this content as that audience and report where author POV and reader POV diverge. Content:\n\n$(cat <SOURCE PATH>)" \
     --participants "downstream:<YOUR_AUDIENCE_TRANSLATOR>,downstream:<YOUR_COHERENCE_AUDITOR>,lateral:<YOUR_EMERGENCE_TRACKER>"
   ```

   **Participant selection:**
   - **2 downstream personas** that model reception/translation/audience fit. Names from *your* panel team — look under `panel_client.py discover` for your downstream branch. The sample above shows generic role-names; replace with your actual persona names.
   - **1 lateral persona** to catch cross-cutting patterns the downstream pair might both miss. Optional but usually worth it.
   - **Avoid upstream personas for this intent** — they model author-side concerns (goal alignment, user-facing progress from the author's side). Including them dilutes the audience read.

   This is a long run (12–20 min — `explore` is the most expensive intent because every participant runs twice). Use background mode on the Bash tool and wait for the notification.

3. **Write `reads/YYYY-MM-DD-<slug>.md`.** The slug is 3–6 words summarizing source + audience (e.g. `panel-harness-for-llm-engineers`, `onboarding-doc-for-new-hires`). Structure:

   ```markdown
   # Audience read: <source>, for <audience slug>

   **Date:** YYYY-MM-DD
   **Source:** <path or inline excerpt>
   **Audience:** <the full audience description>

   > Illustrative persona names below — yours will differ.

   ## Where POV diverges

   <brief synthesis of the main divergence points — 3–6 bullets>

   ## Per-persona reads
   ### <persona name>
   <their read, verbatim>

   ## Synthesis (main persona)
   <the synthesized take>

   ## Operator note (after reading)
   <what the operator decided to do with the read — rewrite sections? scope back the ambition? add a pre-section for context?>
   ```

4. **Don't route — just pass through.** Unlike `challenge` (where `holds_up` routes the decision), audience-read has no verdict. The operator reads the brief and decides what to change; the skill's job is delivery, not judgment.

5. **Remind the operator** to fill in the "Operator note" section after they act. The note is what makes the read worth keeping — without it, the file is a diagnosis with no outcome.

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "I can tell how this will land — I wrote it." | You wrote it, which is exactly why you can't. The whole point of this intent is that you're too close. |
| "`review` would do the same thing — just use that." | `review` asks "is this progress?" which still centers the author's frame. Audience-read asks "does this communicate?" — different job, different personas. |
| "The audience description is clear enough — just fire." | "Clear enough" in the operator's head ≠ clear enough for personas. If the audience isn't a specific persona in the operator's mind, the output will be generic. Push back. |
| "I'll skip the downstream-only rule — upstream gives good feedback too." | Upstream gives *author-side* feedback. That's not the ask. Mixing in upstream here erases the teaching move; if you want upstream feedback, use a different intent. |

## Red flags — stop and reshape

- Audience is "people" / "readers" / "our users" → not specific, output will be generic. Push back.
- Operator wants to be told the content is good → they want validation, not a read. Name that gently and ask what they'd actually want to know.
- Source is conceptual ("the idea of X") not written → redirect to `ask`; draft first, read after.
- Operator's framing is "is this plan any good?" → content question, use `review` or `challenge` instead.
- Upstream personas keep appearing in the `--participants` list → resist. If the operator insists, ask why they want to blend the intents rather than running two separate calls.

## Constraints

- **One source per invocation.** Don't batch sources; don't batch audiences. If the operator has multiple of either, run separate reads.
- **Write only to `reads/`.** No edits to source content, no state-file changes.
- **Never hand-edit `panel_state.json` or `.env`.** See `.claude/skills/panel/SKILL.md`.
- **Persona names in `--participants` are operator-specific** — do not copy them from examples; ask `panel_client.py discover` if uncertain which downstream personas the operator's team has.

## Related

- Panel skill rules and all intents: `.claude/skills/panel/SKILL.md`
- Sibling demos (if present in `../`):
  - `panel-harness` / `panel-harness` — goal lifecycle (`ask` → `review` → per-increment `review`)
  - `panel-challenge-journal` — adversarial verdicts on held positions (`challenge`)
