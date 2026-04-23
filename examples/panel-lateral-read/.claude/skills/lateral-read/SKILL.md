---
name: lateral-read
description: Use when the operator is making a decision about an artifact, feature, or change that will sit inside a system with people, time, or relationships — and they want to surface emergent / cross-cutting / second-order effects that neither upstream (author-side) nor downstream (consumer-side) reads would catch. Symptoms — operator says "what am I missing?" / "what might happen that we didn't plan for?" / "something feels off and I can't name it"; the decision has multi-month unfold potential; the artifact touches an ecosystem, a team, or user behaviors that might reshape around it. NOT for intrinsic-quality reviews, NOT for audience-reception reads, NOT for belief stress-tests.
---

# lateral-read

## Core move

Lateral personas sit off the production→consumption arrow. They catch what's structurally invisible to upstream and downstream reads: emergent behaviors, cross-cutting ripple effects, relational dynamics, time-shaped second-order consequences, pre-existing patterns that quietly break when the new thing lands.

The read isn't prescriptive — it's *possibility mapping*. The value is naming patterns that hadn't been named yet.

## Before firing — verify it's a lateral question

Three checkpoints:

1. **Is there a system the artifact lives in?** The artifact has to be something that will interact with people, time, or ongoing relationships — not a pure technical object evaluated in isolation. A function's correctness is not lateral material. A feature's effect on team dynamics is. If the operator is asking about an artifact's intrinsic quality (does it work, is it good), redirect to `review` with upstream personas — that's not this.

2. **Have upstream and/or downstream been considered?** Lateral is additive, not a substitute. If upstream's "does this plan make sense?" hasn't been answered, do that first. If downstream's "will users get it?" hasn't been thought through, use `panel-audience-read`. Lateral adds a third dimension on top of those, not a replacement.

3. **Is there anything the operator is worried about but can't name?** This is the strongest signal for lateral. "Something feels off" that isn't about the artifact itself is often the system trying to tell them about an emergent or cross-cutting effect their linear view doesn't surface. Pursue the "can't name" — lateral exists for exactly that.

If checkpoint 1 fails, redirect to `review`. If checkpoint 2 fails, redirect to whichever linear read fits. If checkpoint 3 is the motivation, fire confidently.

## Why lateral specifically

Upstream and downstream are both *on the arrow*. They model the producer and the consumer, but they can't see off-arrow effects:

| What gets missed | Why it gets missed |
|---|---|
| Emergent behaviors (users reshape around the feature in ways nobody specified) | Upstream modeled the design, downstream modeled reception of the design. Neither modeled what users *do next* after adopting. |
| Cross-cutting ripples (technical choice that changes team dynamics; API change that reshapes third-party ecosystem) | Those ripples travel through a dimension the arrow doesn't point in. |
| Relational dynamics (who talks to whom, who defers to whom after this ships) | Linear thinking treats the artifact as the payload; lateral treats the artifact as a perturbation to a relationship graph. |
| Time-shaped things (smooth at launch, broken at month-6 when the pattern surfaces) | Upstream and downstream read the artifact at a snapshot; lateral reads what happens when it runs for a while. |
| Pre-existing-pattern breakdowns (something quietly load-bearing stops working because the new thing displaces it) | The thing that broke wasn't on anyone's map, so no linear read notices it was there. |

Lateral personas specialize in catching these. Not all of them; not deterministically. But the dimension they point at is real, and it stays blind without them.

## Steps

1. **Collect two inputs from the operator:**
   - **artifact** — what's being decided / built / changed. One sentence.
   - **system context** — what the artifact sits inside. Who uses it, what it's part of, what relationships or dependencies are adjacent to it. Two to four sentences. Specificity matters — "our team" is weaker than "a 12-person eng org, 4 timezones, primarily async".

2. **Invoke `review` with lateral-heavy participants. One bash call:**

   ```bash
   python .claude/skills/panel/panel_client.py review \
     "<ARTIFACT + SYSTEM CONTEXT>. What might emerge, ripple, or break that isn't about the artifact itself? What patterns does this introduce into the system that nobody designed? What pre-existing pattern is doing quiet work that this might displace?" \
     --participants "lateral:<YOUR_EMERGENCE_WATCHER>,lateral:<YOUR_TOPOLOGY_READER>,upstream:<YOUR_CONCEPTUAL_ANCHOR>"
   ```

   **Participant selection:**
   - **2 lateral personas** that model emergence, cross-cutting patterns, or relational dynamics.
   - **1 upstream persona as anchor** — to keep the reads tethered to what's actually being built. Without this anchor, lateral reads drift into pure speculation. Upstream keeps them grounded in the artifact.
   - **Avoid downstream** — downstream would redirect the read toward audience reception, which is `panel-audience-read`'s job.

   Run takes 5–8 min. Use Bash background mode.

3. **Write `reads/YYYY-MM-DD-<slug>.md`.** Structure:

   ```markdown
   # Lateral read: <artifact slug>

   **Date:** YYYY-MM-DD
   **Artifact:** <one-sentence description>
   **System context:** <2–4 sentences on what it sits inside>

   > Persona names from the panel team that ran this call; readers' teams will differ.

   ## What might emerge
   <patterns that might arise from interaction>

   ## What might ripple
   <cross-cutting effects in unintended directions>

   ## What might quietly break
   <pre-existing patterns the artifact might displace>

   ## Per-persona reads
   ### <persona name>
   <their read, verbatim>

   ## Synthesis (main persona)
   <filter from "everything" to "most likely to matter">

   ## Operator note (after sitting with the read)
   <what the operator decided to watch, plan for, or change based on the read>
   ```

4. **Don't route.** Lateral reads don't return verdicts. The skill's job is delivery; the operator sits with the read and decides what to do.

5. **Remind the operator** to fill in the "Operator note" after they've acted or built guardrails. Lateral predictions are most useful when revisited at T+3 months — did the predicted patterns appear? That feedback tightens their use of lateral over time.

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "Lateral reads are just speculation." | They are speculation — by design. Emergence isn't forecastable, but naming possibilities is still valuable. The value is *possibility mapping*, not prediction. Don't apply a prediction standard to a mapping tool. |
| "Upstream and downstream already covered this." | If you felt that were true, this skill wouldn't have been triggered. Check what's unnamed; if nothing is, the linear reads were enough. |
| "This reads like vibes, not analysis." | Lateral surfaces what linear analysis structurally misses. It *is* another kind of analysis — one that uses emergence and topology as its primitives rather than causation. Vibes ≠ the thing being described. |
| "The operator just wants a recommendation, not a read." | Then redirect. Lateral is not a decision tool; it's an input. If they need a call, use `challenge` on the decision instead. |

## Red flags — stop and reshape

- Operator is asking about the artifact's intrinsic quality → redirect to `review` with upstream.
- Operator wants audience-reception analysis → redirect to `panel-audience-read`.
- Operator wants a yes/no verdict → redirect to `challenge`.
- The artifact has no system context (it's a standalone technical object with no human or temporal surface) → lateral won't produce anything useful; use `ask` or `review`.
- Operator hasn't considered upstream or downstream at all → lateral first is putting the roof on before the walls. Get linear coverage first.

## Constraints

- **One artifact per invocation.** Lateral blurs fast across multiple artifacts; keep it focused.
- **Write only to `reads/`.**
- **Never hand-edit `panel_state.json` or `.env`.** See `.claude/skills/panel/SKILL.md`.
- **Use upstream as anchor.** Don't fire lateral-only without an upstream participant — reads drift into speculation.

## Related

- Panel skill rules: `.claude/skills/panel/SKILL.md`
- Sibling demos:
  - `hello-panel` — 2-min onboarding showing review + upstream/downstream contrast
  - `panel-audience-read` — downstream-heavy reads for reception/translation
  - `panel-challenge-belief` — adversarial verdict on a held belief
  - `panel-harness` — goal lifecycle harness (full workflow example)
