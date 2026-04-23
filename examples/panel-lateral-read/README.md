# panel-lateral-read — example

Upstream personas model the author's side ("what's the shape of this decision?"). Downstream personas model the consumer's side ("how does this land?"). Both sit on the same arrow — production → consumption. **Lateral personas sit off that arrow.** They catch what the linear view is structurally blind to: emergent behaviors, cross-cutting patterns, relational dynamics, second-order effects, time-shaped things.

This demo teaches lateral personas by example: same artifact, read through a lateral-heavy mix, surfacing what an upstream+downstream pair would miss.

Self-contained. Python stdlib only. The panel skill is vendored under `.claude/skills/panel/`.

## The three branches, briefly

| Branch | What it models | Example role |
|---|---|---|
| **Upstream** | Author / designer / originator vantage — "what's the shape of the thing being made?" | conceptual scout, domain expert, pattern spotter |
| **Downstream** | Consumer / user / reader vantage — "how does the thing land with people who use it?" | audience translator, coherence auditor, operator translator |
| **Lateral** | Cross-cutting / emergent / relational vantage — "what patterns does this introduce into the system that nobody designed?" | emergence tracker, social topologist, iterative craftsperson |

Upstream and downstream are both *linear*. Lateral is *cross-cutting*.

## What lateral catches that linear reads miss

The linear view assumes: someone designs a thing, people use the thing, the consequences are observable on either end. That model is correct and useful — and it's blind to:

- **Emergent behaviors** — patterns that arise from the interaction between the thing and its users that nobody specified. (A new feature doesn't just get used; it reshapes what users do around it.)
- **Cross-cutting effects** — consequences that ripple through the system in directions the artifact wasn't built to produce. (A technical decision that quietly changes team dynamics; an API change that reshapes a third-party ecosystem.)
- **Relational patterns** — how the thing changes relationships between its parts, or between people. (Who talks to whom; who defers to whom; who maintains informal channels.)
- **Time-shaped things** — second-order effects that unfold over months. (The migration is smooth at launch and catastrophic at month-six when the pattern-nobody-designed emerges.)
- **Pre-existing-pattern breakdowns** — the thing works fine; but some pattern that quietly did real work and was never noticed stops working because the thing displaces it.

Upstream and downstream are structurally positioned to miss these. Not because they're bad at their jobs — because their jobs aren't *this*.

## Shape

```
  operator          lateral-read                reads/YYYY-MM-DD-<slug>.md
  artifact +    →  skill (review with       →  per-persona reads, synthesis,
  "what might       lateral-heavy mix)           "what ripples outward"
   ripple?"
```

One skill (`lateral-read`), one bash call (`panel_client.py review --participants lateral:...`), one archived read per pass.

## Why `review` as the intent?

`review` = `parallel_with_main`: each participant reads independently, main persona synthesizes. Fast enough (~5–8 min) that it's usable for routine decisions. The synthesis step matters here because lateral reads tend to generate *lots* of possibilities — emergence is speculative by nature. The main persona's synthesis is what filters from "everything that might happen" down to "the patterns most likely to matter."

For a deeper read on a single high-stakes artifact, use `explore` instead (two-stage, 12–20 min). For a structured verdict on a held belief about emergent dynamics, use `challenge`.

## Quick start

1. `cp .env.example .env` — paste your `PANEL_API_KEY`
2. `python .claude/skills/panel/panel_client.py setup` — propose defaults; apply the printed `state set` commands
3. `python .claude/skills/panel/panel_client.py discover` — see which lateral personas your team has
4. In Claude Code from this directory, describe the artifact/decision and the system it lives in. The `lateral-read` skill handles the rest.

## Example output

See [`reads/2026-04-22-api-rate-limits.md`](reads/2026-04-22-api-rate-limits.md) — a lateral-heavy read of *"we're adding API rate limits to our public endpoints."* Three reads showing what emerges, what ripples, and what pre-existing pattern quietly breaks — none of which a standard upstream (reliability/cost) or downstream (DX/error UX) read would have caught.

## Forking this demo

| Type | What it is | When you fork |
|---|---|---|
| **Skeleton** (keep) | The skill's two-input shape (artifact + system context); the lateral-heavy participant selection; the read file structure | Copy and keep — this is the pattern |
| **Scaffolding** (delete) | The worked example; the vendored panel skill if you have it globally | Delete after reading |
| **Pedagogy** (keep, then trim) | The "what lateral catches" list and the three-branches table | Keep while internalizing; compress in your own voice later |

## Use this when

- You're making a decision that touches a system with people, time, or relationships in it (so: most non-trivial decisions).
- You've heard upstream ("does this fit the plan?") and downstream ("will users like it?") and something still feels unexamined.
- You're anticipating a multi-month unfold — launches that go well at T+1 week and fail at T+6 months.
- Something you noticed feels "off" but you can't name it, and the off-ness isn't about the artifact itself.

## Don't use this when

- The question is about the artifact's intrinsic quality — use `review` with upstream for that.
- The question is about how it lands with a specific audience — use `panel-audience-read` with downstream.
- You're stress-testing a held belief — use `panel-challenge-belief`.
- You're looking for a recommendation — lateral reads surface possibility space, not prescriptions. They're inputs to a decision, not decisions.

> The worked example labels attribution by branch vantage (lateral / upstream) rather than by specific persona names. Real panel runs show your own team's persona names in those slots. Run `panel_client.py discover` to see yours. If your team has no lateral personas, that's the adaptation pointed at: add some at panel.humx.ai → Profile → Personas, since without a lateral branch the panel is blind to an entire dimension.

## Limits

- **Lateral reads are speculative by nature.** Emergence is hard to predict; some reads will miss. Treat them as *possibility mapping*, not forecasting. The value is naming things you hadn't named yet, not ranking them.
- **`review` takes 5–8 min.** Worth it for decisions that touch a system; overkill for isolated technical choices.
- **One artifact per read.** Batch different artifacts into separate runs; lateral is easy to blur if the prompt covers too much.
- **This demo doesn't produce a decision.** It produces a map of what might ripple. The decision is still yours, informed by the map.
