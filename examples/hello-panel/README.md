# hello-panel — 2-minute onboarding

This is the "hello world" for the `/panel` skill. One call, two vantages, one synthesis. You'll see the core move in ~200 words.

## What a panel is (and isn't)

A single LLM prompt gives you one confident answer shaped by whatever the model guessed you wanted. Even prompts that say "give me multiple perspectives" usually return the *same mind rephrasing itself three ways* — because it's still one context, one inference, one frame.

**A panel is not that.** It's structured disagreement: independent personas generate takes from fixed vantages they can't drop, then a main persona synthesizes across them. Not a loop. Not a chain. Not agents acting in sequence — agents *thinking* in parallel from stances they can't escape.

**That's it.** The rest of the demos show what you do with this; this one just shows it happening.

## The artifact

A recognizable, high-stakes decision many companies are making right now:

> **We're replacing our customer support team with an AI agent.**

A solo prompt on this returns a confident paragraph weighing cost savings against user experience. A panel call returns something different — because one mind can't hold both angles at once.

## The call

After `setup` (see "Run it yourself" below), one bash line:

```bash
python .claude/skills/panel/panel_client.py review \
  "We're replacing our customer support team with an AI agent. Tell me what matters." \
  --participants "upstream:<your_upstream_persona>,downstream:<your_downstream_persona>"
```

That uses the `review` intent (fastest panel intent that still shows independent reads + synthesis — ~5–8 min wall time) with two participants from different vantages. **See "Which personas?" below for picking yours.**

## The output shape

When you fire a `review` call, three things come back: an independent read from each participant, then a synthesis by the main persona. Output is attributed to the caller's personas by name — so the exact surface of the output varies team to team, even on the same prompt.

> This is an example of the output shape, not a literal transcript. Labels below are by branch (upstream / downstream) rather than by persona name, because persona names are specific to each team — the branch vantage is the thing that generalizes. When you run this, your own persona names appear where the branch labels sit below. Run `panel_client.py discover` to see your team.

Here's a representative shape for the AI-support question:

### Upstream vantage — "what shape is this decision?"

> "Replacing" and "augmenting" are two different decisions being conflated under one word. If the goal is *cost reduction*, say that — the implementation is tiered triage with humans for escalation. If the goal is *24/7 coverage*, say that — the implementation is an agent for after-hours plus existing team during business hours. If the goal is *speed-to-first-response*, say that — the implementation is a front-door deflection layer. Each of those produces a different technical spec, a different success metric, and a different risk profile. "Replace the team with an AI" obscures which of the three you're actually buying, which means you're likely to optimize for the wrong one and discover it only after committing. Name the metric first, then decide the mechanism.

### Downstream vantage — "how does this land?"

> Two audiences read this announcement and both matter. Customers: they detect AI within 2–3 turns and try to escalate. If escalation is slow, vague, or absent, trust erodes inside a single interaction — much faster than with a mediocre human. The ones who got good service from your team before feel specifically punished; churn risk spikes in that segment, not uniformly. Your support team: they read this memo and start interviewing. The strongest ones leave before the agent ships, which means you're short-handed during the transition period — the worst possible moment to have a gap. Externally: "they replaced humans with a bot" is a narrative competitors will hand to your press contacts; the announcement itself is a decision, not an implementation detail. A bad framing of a sound decision can lose you more than the decision earns.

### Synthesis (from your main persona)

Two independent reads converge on the same diagnosis from different angles: **the question isn't "can an AI handle this?" — it's "what are you actually deciding, and what will you lose by calling it replacement?"** Upstream saw a metric-fuzziness problem (three different decisions bundled); downstream saw a perception problem (replacement framing is narratively expensive, both for customers and for the team that reads the memo). Both reads point the same way: this is probably not pure replacement. It's almost certainly *tiered triage* (agent for well-understood repetitive queries; humans for escalation, edge cases, and relationally-loaded interactions) with a specific primary metric named and with careful framing both externally and internally. Name the metric. Call it what it is. Don't optimize support costs by accidentally optimizing for churn and attrition.

## What just happened

Two minds. Two concerns. Different starting points — one about what pattern fits the decision, one about how users experience it — converging on the same diagnosis from orthogonal directions.

Neither persona was told the other's take. Neither synthesized. The main persona read both and found the shared structure. **That's vantage orthogonality**, and it's why a panel catches things a solo prompt can't: a single mind can't generate a read from a vantage it doesn't hold.

## Run it yourself

Five steps from zero to your own panel output:

```bash
# 1. Paste your API key
cp .env.example .env   # then edit .env

# 2. Propose team / main persona / defaults
python .claude/skills/panel/panel_client.py setup

# 3. Apply the commands it printed (copy-paste them as-is)

# 4. See what personas you actually have
python .claude/skills/panel/panel_client.py discover

# 5. Fire a panel call — substitute your personas from step 4
python .claude/skills/panel/panel_client.py review \
  "We're replacing our customer support team with an AI agent. Tell me what matters." \
  --participants "upstream:<your_upstream>,downstream:<your_downstream>"
```

The output will be attributed to *your* personas by name. The shape — two reads + synthesis — is the same across teams; the voices doing the reading are yours.

## Which personas?

`panel_client.py discover` shows your team. Pick two participants from *different branches*:
- **One upstream** — voices that model the author's or designer's angle ("what's the shape of this decision?")
- **One downstream** — voices that model the consumer's or user's angle ("how does this land?")

The specific names don't matter. **The branch pair is the thing** — that's what makes the two reads independent rather than two flavors of the same mind.

If your team has only upstream personas, that's your first adaptation: add a downstream persona on panel.humx.ai → Profile → Personas. Most panel moves lean on upstream/downstream contrast.

## Where next

Once the "two independent minds → synthesis" shape feels intuitive, the other demos show what you do with it:

- `panel-challenge-belief/` — adversarial pressure on a held belief, holds-up verdict (`review` + lateral personas with a challenge-shaped prompt)
- `panel-lateral-read/` — surface emergent and cross-cutting effects linear reads miss (`review` + lateral)
- `panel-minimize-drift/` — the 4-call checkpoint pattern for keeping agentic runs on track
- `panel-harness/` — full goal → plan → execute lifecycle, phase-sensitive intent selection

Each demo teaches a different slice. Start there.

## Limits of this demo

- **One scenario, one participant pair.** `review` is a fine starter but it's not the whole surface — see the sibling demos for different branch mixes and prompt shapes.
- **No orchestration.** This demo is a single call. Real work usually chains calls across phases — see `panel-harness` for that shape.
- **Persona choice matters more than the example suggests.** The two vantages above happened to converge cleanly on this artifact. A poorly-matched pair can produce two reads that don't meaningfully differ. Pick branches, not just names.
