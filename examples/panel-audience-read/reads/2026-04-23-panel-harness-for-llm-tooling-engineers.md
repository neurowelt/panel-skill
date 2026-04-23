# Audience read: `../panel-harness/README.md`, for skeptical LLM-tooling engineers

**Date:** 2026-04-23
**Source:** `../panel-harness/README.md` (the goal → plan → execute harness demo)
**Audience:** An engineer who has seen a few LLM-agent demos before (LangChain, AutoGPT, Claude Code's built-in skills) but has never heard of the `/panel` skill and is skeptical that "multi-agent" is more than a wrapper trick. Skimming at 10pm to decide whether to fork. Budget for attention: ~60 seconds before the tab closes.

> Output below is illustrative. Attribution is by branch vantage (downstream / lateral) rather than specific persona names — real panel output shows your own team's persona names in these slots. Run `panel_client.py discover` to see yours.

## Where POV diverges

The author (me) writes as if the reader already knows what "the panel skill" is and why "multi-persona" differs from the multi-agent pattern the skeptic has already tried and dismissed. The reader has neither piece of context. Six concrete divergences:

- **"Panel" reads as "multi-agent"** to a skeptic primed on AutoGPT — pattern-match triggers skepticism before the actual distinction is made.
- **The three-phase diagram shows up before any payoff** — the reader is shown shape before they've been given a reason to care about shape.
- **"Skill" is overloaded** (the panel skill ≠ the harness-* skills ≠ Claude Code's built-in skills) and the reader can't tell which is which from the README alone.
- **"Limits of v0" is at the bottom** — for a skeptic, that section is reassuring ("they know what's not there") but placed where they'll never read it.
- **Skeptics don't read linearly** — they jump to "running from scratch," hit the `PANEL_API_KEY` gate, bounce. The doc presumes a reader who scrolls top-to-bottom.
- **No comparison anchor** — a reader who's already seen LangChain/AutoGPT is implicitly asking "why not that?" The README never addresses this. Silence reads as evasion.

## Per-persona reads

### Downstream voice — reception-modeling read

The opening sentence is *"Small, runnable example of using the **panel** skill to drive a goal from intuition to execution."* To the target reader, "the panel skill" is an undefined noun. They don't know what a panel is. They don't know why it would drive a goal. They especially don't know why they'd care about "from intuition to execution" — that phrasing reads as vague-aspirational, which pattern-matches to LLM tooling that overpromised and under-shipped.

The word "panel" is doing heavy lifting here. In the reader's prior experience, "multi-agent" means a loop of LLM calls pretending to be different roles, which didn't solve anything and burned tokens. Unless the README opens by *distinguishing* panel from that pattern, the skeptic has already categorized this and moved on.

Specific fix: the first 80 words must answer *what problem does this solve that a plain prompt doesn't* — in the reader's vocabulary, not yours. Something like:

> "When you ask an LLM 'what should we do about X?', it gives you one confident synthesis shaped by whatever it guessed you wanted. What you actually need for high-stakes decisions is structured disagreement — independent voices that argue, then synthesize. That's a panel. It's not an agent loop; participants don't act, they just think from fixed angles. This example shows how to wire a panel into a three-phase goal-driven harness."

Ship that, and you've earned the next 60 seconds. Skip it, and the reader decides in paragraph two that this is "multi-agent with extra steps" and closes the tab.

### Downstream voice — constraint-surfacing read

The internal logic of the README is tight — phase 1 → phase 2 → phase 3, each with its own skill, each with a panel pattern chosen for the phase's question. I can trace the author's reasoning and it's coherent. But the reader *doesn't start from that reasoning* — they start from "what even is this?" and the doc doesn't bridge them to the reasoning.

Three coherence gaps that only become visible from the reader's entry point:

1. **"Skill" collision.** The README uses "skill" to mean both the panel skill (CLI + SKILL.md infrastructure) and the four harness-* skills (Claude Code agent-driving docs). To a Claude Code user these ARE both skills, but they operate at different levels. The reader trying to map this to their mental model of Claude Code skills gets stuck — they can't tell if harness-setup-goal is a Python file, a prompt, or a plugin.

2. **`harness-customize` placement.** It's listed in the table as "plus one off-main-flow skill invoked by the operator after running episodes." From the reader's view, that bullet is either essential (and the table structure is misleading) or optional (and therefore why mention it at all?). The ambiguity makes them think they're missing a concept.

3. **"Signal files are never rich — all content lives in the `.md`"** is stated once, in the phase-3 section. But this rule governs the whole harness design — it's the single most reusable insight for a forker. Stating it buried, in one phase, makes the reader think it's a phase-3 convention, not a harness-wide invariant.

Fix for #1: rename the harness-* skills visibly (e.g., always write `harness-setup-goal/SKILL.md` in prose when first introduced) and add a one-line "these are Claude Code agent skills; the panel skill is the CLI/service" clarification near the top.

Fix for #3: elevate the signal/markdown split to the README opening as the "one thing to keep" design insight. That's what a forker would copy; the rest is specifics.

### Lateral voice — emergence-tracking read

Watching the reader's *path* through this doc — not content, path — reveals a pattern the author probably didn't plan for. The skeptic doesn't read linearly. They scan for exit ramps. Three exit-ramp patterns show up:

- **Exit ramp A: they scroll past the README prose straight to "Running from scratch."** They copy-paste the first bash block (`python harness/scout.py`), get "phase 1 — no goal.md yet," and don't know what that means without reading the README they just scrolled past. Bounce.
- **Exit ramp B: they scroll to the "Limits of v0" section** because experienced engineers check the limits first. That section is *at the end* — they have to scroll past three tables of content they don't yet care about. Reaching "Manual agent invocation is primary" at the bottom is the first moment the doc would actually reassure them, but 90% of skeptics quit before reaching it.
- **Exit ramp C: they look for "Why this vs. LangChain?"** This comparison is never made. Silence is interpreted as either "they don't know about LangChain" (unsophisticated) or "they know and chose not to address it" (evasive). Either read pushes the reader toward the door.

The emergent pattern: **this README is written for a reader who has already decided to invest.** It's an onboarding doc, not a pitch doc. The skeptic isn't onboarding — they're deciding. For them, the load-bearing content is the *reason to stay*, not the *shape of the thing*.

Pragmatic move: add a 3-line "What this is / what this isn't" block at the very top, before even the architectural intro.

> **What this is:** a reference example of using panels (structured disagreement between LLM voices) to drive goal work. Python stdlib only, ~500 lines, runnable in 5 min.  
> **What this isn't:** an agent framework, a multi-agent loop, or a replacement for LangChain. It's a pattern for combining panel calls into a workflow; swap the harness for your own.  
> **Who this is for:** engineers who've felt the "one confident wrong answer" failure mode of single-prompt LLM workflows and want structured disagreement as a tool.

Drop that in, and all three exit ramps close. The skeptic now has an anchor to decide from.

## Synthesis (main persona)

The three reads converge on one diagnosis: **the README is written as if the reader is already interested.** It onboards someone who's decided to invest, not someone still deciding. For the skeptic audience, that's a 60-second miss — they bounce before any of the genuinely strong content (the phase-pattern matching, the signal/markdown invariant, the scout's linearity) becomes visible to them.

Concrete moves in priority order:

1. **Add a "What this is / What this isn't / Who this is for" block at the absolute top** (lateral voice's fix). This closes the three exit ramps and buys 2–3 more minutes of attention.
2. **Replace the opening sentence with a pain-first framing** (downstream voice's fix). Define "panel" in the reader's vocabulary *before* you use the word as a modifier ("panel skill," "panel pattern").
3. **Explicitly distinguish panel from multi-agent** in the first 80 words — the skeptic has already categorized "multi-agent" and your silence on the distinction hands them ammo. "Panels don't act, they think from fixed angles" is a clean one-liner.
4. **Elevate the signal/markdown split to a top-of-README design principle** (second downstream voice's fix). It's the single most reusable insight in the harness and you've buried it in phase 3.
5. **Disambiguate "skill"** on first use — one-line note distinguishing the panel skill (CLI + server) from the harness-* skills (Claude Code agent docs).
6. **Consider moving "Limits of v0" up** by two sections. Skeptics want to see self-awareness early, not as a footer.

None of this requires rewriting the architecture or the phase work — just re-sequencing what the reader encounters first. The draft you have is strong for a committed reader. This is an insertion pass for the skeptic reader, not a rewrite.

## Operator note (added after reading)

Audience_translator's observation about "the panel skill" appearing in the first sentence before any reader could know what it means was the sharpest one. I was too close to see it. Rewrote the opening to define panels in reader-vocabulary before using the word as a modifier.

Coherence_auditor's "skill overload" catch was real — Claude Code skills + the panel skill + harness-* skills all collide in the reader's head and I never flagged it. Added a one-line disambiguation in the opening section.

Emergence_tracker's exit-ramp pattern was the most useful finding. I'd never modeled the *path* a skeptic takes through the doc, only the *content* the doc presents. Moved "Limits of v0" up, added the three-line "what this is / isn't / who for" block at the top, and added the "why not LangChain/AutoGPT" one-liner I'd been avoiding because it felt defensive. It's not defensive — it's a courtesy to the reader who was going to ask that silently anyway.

Round-trip cost: 12 min of `explore`, ~40 min of rewriting. Before this read, the README had been re-read by the author three times and seemed fine each time. That's exactly the failure mode this demo is designed to catch — the author cannot be the audience.
