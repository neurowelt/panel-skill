# panel-minimize-drift — example

## The problem this solves

An LLM agent running a multi-step task doesn't drift suddenly. It drifts in small increments that each look locally reasonable and compound into the wrong direction. Classic failure mode: the agent interprets the task slightly off at T=0, builds on that interpretation at T=1, accumulates confidence in it at T=2, and by T=3 is confidently delivering something the operator didn't actually ask for. Each step was coherent with the last; the whole trajectory wasn't coherent with the original.

Retrospective review catches this at T=3, by which point the agent has spent tokens, time, and your attention on the wrong thing. The cost is the whole run.

**Periodic panel calls at checkpoint moments catch drift while it's cheap to correct.** This demo shows the pattern: four calls at four moments in an agentic task, each using a panel intent that fits the drift vector at that checkpoint.

This is not a skill with a trigger — it's a pattern you apply when setting up an agentic workflow. The vendored panel skill is here so the example is runnable; the demo itself is about *when to interrupt the agent with a panel call*, not about a fifth intent.

## Shape

```
  T=0 framing  ─→  T=1 plan  ─→  T=2 midpoint  ─→  T=3 result
      │               │               │                │
      ▼               ▼               ▼                ▼
  panel call 1    panel call 2    panel call 3    panel call 4
  (ask)           (review)        (challenge)     (review)
  "did you        "does the       "has the work   "does the output
  understand      plan deliver    drifted from    answer the
  the ask?"       the goal?"      the original?"  original ask?"
```

Four checkpoints. Four different intents, each matched to the drift vector that's actually live at that moment.

## Why four intents, not one?

Drift isn't one thing — it's different at each phase. Using the same intent at every checkpoint either over-spends (review at T=0 is overkill) or under-catches (ask at T=3 misses systemic drift).

| Checkpoint | Drift vector | Right intent | Why |
|---|---|---|---|
| **T=0: Framing** | Misinterpreted ask | `ask` (single voice, upstream) | Fast gut-check — "does this framing match what the operator actually said?" If not, abort now before anything is built on it. |
| **T=1: Plan** | Plan drifts from goal | `review` (parallel upstream reads + synthesis) | Independent reads catch blind spots in the plan the agent won't see itself. |
| **T=2: Midpoint** | Execution over-commits to early decisions | `challenge` (structured adversarial verdict) | By midpoint the agent has a direction; the question is whether that direction holds up, not whether it's on track for the plan (plan itself may be wrong). |
| **T=3: Result** | Output answers the wrong question | `review` (downstream + upstream) | Final check: does the artifact satisfy the original ask, or has scope shifted? Downstream participant makes sure the output is legible; upstream makes sure the goal is met. |

Each intent is ~1–15 minutes of panel time. Total overhead for the four calls on a multi-hour agentic task: ~20–40 min. That's significant — and it's usually a fraction of the cost of a run-gone-wrong caught only at T=3.

## When to use this pattern

- The agentic task is long enough that a full-run-redo would be expensive (more than ~30 min of agent time).
- The task has at least one phase boundary — distinct moments where the agent transitions from framing to planning to execution to output.
- The operator won't be watching the run live. If they'd catch drift by observation, the checkpoints aren't needed.
- The task has real stakes — the output will be acted on, shipped, or shown. Low-stakes exploration doesn't need this scaffolding.

## When NOT to use this pattern

- The agent's task is a single-shot retrieval or generation. No phases, no drift to catch.
- You need the output in <10 min. Four checkpoint calls add ~20–40 min of wall time; skip the pattern and just review at the end.
- The operator is available to steer as the agent runs — real-time steering dominates checkpoint-based correction.
- The run is cheap to redo. If the agent can just rerun from scratch in 2 min, retrospective review is faster than checkpoint-based drift-catching.

## Worked example: an agent researching LLM observability for your company

A realistic case where drift is common.

### The original ask

> "Research the best approach for our company to start using LLM observability. We're a 40-person B2B SaaS, one LLM feature in production (a customer-support assistant), two more LLM features planned for Q3. We have no observability today beyond basic logs. I want a recommended approach, not a vendor roundup. Budget for this work: one sprint."

### Checkpoint T=0 — framing check (call 1, `ask`)

**Why here:** the agent is about to spend ~4 hours researching. A minute now saves the run if the framing is off.

```bash
python .claude/skills/panel/panel_client.py ask \
  "The agent is about to research LLM observability for our company. Context: 40-person B2B SaaS, one LLM feature in production, two more planned. Original ask: 'recommended approach, not a vendor roundup, one-sprint budget.' Is the framing of this task correct, or is the agent about to research the wrong thing?" \
  --persona "<your_upstream_persona>"
```

**Illustrative output** (your persona name will differ):

> The framing is mostly right but has one risk: "LLM observability" is a category that's matured recently, and the ask is for "recommended approach" — meaning the agent should be converging on a recommendation, not surveying. Watch for the agent drifting toward "here are 20 vendors and their trade-offs" when what's needed is "given your constraints (40 people, 1 feature live, 2 planned, one sprint of work), the right shape of the initial observability practice is X, with these Y vendor options that fit X." The ask is scope-bounded; the research should be too.

**Drift caught:** the risk that the agent goes vendor-survey mode instead of approach-recommendation mode. Flag for the agent's plan phase.

### Checkpoint T=1 — plan check (call 2, `review`)

**Why here:** the agent has produced a research plan. Now's the moment to catch plan-level drift before execution starts.

Suppose the agent's plan is: *"1. Survey 12 LLM observability vendors (Langsmith, Langfuse, Helicone, Humanloop, Phoenix, TruLens, ...). 2. Build comparison matrix on features, pricing, integration cost. 3. Produce ranked recommendation."*

```bash
python .claude/skills/panel/panel_client.py review \
  "Original ask: recommended approach for LLM observability for a 40-person B2B SaaS with one LLM feature live and two planned, one sprint budget. Proposed plan: 1. Survey 12 vendors. 2. Build comparison matrix. 3. Ranked recommendation. Does this plan actually deliver the original ask?" \
  --participants "upstream:<your_upstream_a>,upstream:<your_upstream_b>"
```

**Illustrative synthesis:**

> Two reads landed in the same place: the plan drifts toward vendor-roundup, which is exactly what the original ask excluded. The plan should start with "what does observability practice at this company size with this feature count look like?" and *then* identify vendors that fit the shape. Flip steps 1 and 2: define the shape of the practice first (1 product-scoped dashboard, trace-level logging for all user-facing LLM calls, evaluation on a weekly cadence — whatever fits); then narrow to the 3–4 vendors that can deliver that shape within one sprint; then decide. A 12-vendor matrix is infrastructure for a procurement team, not infrastructure for an engineering decision.

**Drift caught:** plan-level scope drift. Agent retries planning with the flipped structure.

### Checkpoint T=2 — midpoint check (call 3, `challenge`)

**Why here:** the agent is ~60% through execution. It has a direction forming. Now's when the agent's confidence in an early finding becomes brittle — and that's the drift mode to attack adversarially.

Suppose at T=2 the agent has committed to recommending Langsmith as the primary vendor and is writing up the justification.

```bash
python .claude/skills/panel/panel_client.py challenge \
  "Agent is recommending Langsmith as the primary LLM observability tool for our company." \
  --evidence "Langsmith integrates natively with our existing LangChain-based agent" \
  --evidence "Pricing fits our scale (~$200/mo at current usage)" \
  --evidence "Dashboard covers trace-level logging and evaluation in one place" \
  --decision-pending "Finalizing the recommendation document for the sprint review tomorrow"
```

**Illustrative challenge verdict** (your persona names will differ):

> **holds_up: false** (confidence: 0.68)
>
> **Strongest objection:** The decision commits you to LangChain as infrastructure, not as convenience. Langsmith's "native" integration means deep coupling — if in 6 months your team evaluates moving off LangChain (which is currently a real evaluation at companies your size, given the maturity of alternatives), Langsmith becomes a sunk-cost lock-in. The observability choice should be *framework-agnostic* unless you've committed to LangChain as a strategic choice separately. Langfuse or Phoenix decouple observability from the framework; that's the cost axis you've elided.
>
> **Would change mind if:** Explicit confirmation that LangChain is a strategic choice (not just today's tool). OR evidence that Langsmith's framework-agnostic features cover your needs without the deep integration.

**Drift caught:** the agent had locked in on Langsmith because of the existing LangChain integration — but that's an argument *for Langsmith given a LangChain commitment*, not *for committing to LangChain*. The dependency was backwards. Agent revises.

### Checkpoint T=3 — result check (call 4, `review`)

**Why here:** the output is drafted. The last drift vector is "the artifact answers the wrong question" — you want one upstream read (does it meet the goal?) and one downstream read (is it legible to the person who'll act on it?).

```bash
python .claude/skills/panel/panel_client.py review \
  "Original ask: 'recommended approach for LLM observability, not a vendor roundup, one-sprint budget.' Final output: <paste the artifact>. Does this answer the original ask? Is it usable by the operator who asked?" \
  --participants "upstream:<your_upstream>,downstream:<your_downstream>"
```

**Illustrative synthesis:**

> Upstream read: the output now leads with the approach ("for your stage, observability practice should be: trace-level logging for all LLM calls, eval on weekly cadence, one shared dashboard") and treats vendor selection as implementation of the approach. Scope fits the original ask.
>
> Downstream read: the output is legible — a team lead could read it in 10 minutes and act on it. One gap: the sprint plan for implementation isn't broken out. The operator will have to do that themselves. Consider whether that's a feature (they wanted a recommendation, not a plan) or a gap (they implicitly wanted "what to do this sprint"). The original ask says "recommended approach," which argues it's a feature — but worth flagging.
>
> Synthesis: output meets the ask. Minor addition would be to note explicitly that the sprint plan is separate work, so the operator isn't expecting it.

**Drift caught:** minor — just a framing clarification. The core output is aligned because the earlier checkpoints corrected the larger drifts.

### What the pattern prevented

Without the four checkpoints, the likely failure path:

- T=0 → T=3 uncorrected: agent would have produced a 12-vendor comparison matrix with a Langsmith recommendation coupled to LangChain. Operator reads it, spots the scope mismatch, asks for a redo. Cost: ~4 hours of agent time plus operator frustration plus a re-run.

With the four checkpoints:

- T=0: 1 minute saved the "it's a vendor roundup, not an approach" failure mode.
- T=1: 8 minutes caught the plan-level version of the same drift.
- T=2: 12 minutes caught the Langsmith-requires-LangChain coupling that would have locked in a strategic choice by accident.
- T=3: 8 minutes confirmed alignment and caught a minor framing note.

Total panel overhead: ~30 minutes. Run quality: close to first-pass correct.

## Forking this pattern

This isn't a skill to copy — it's a pattern to apply. What forks:

- **The four checkpoints.** Keep the structure (framing / plan / midpoint / result) — these are where drift vectors shift.
- **The intent mapping.** `ask` → `review` → `challenge` → `review` fits most agentic research / planning tasks. For coding tasks, the midpoint might be `review` not `challenge` (you want plan-adherence, not adversarial pressure on a half-written PR). Adapt to the task.
- **The persona mix.** Depends entirely on your team. Generic rule: at least one upstream at every checkpoint (to anchor to the task), at least one downstream at the result check (to anchor to legibility).

> Bash calls above use `<your_upstream_persona>` etc. as placeholders — substitute your actual persona names, visible via `panel_client.py discover`. General rule: keep at least one upstream participant at every checkpoint (to anchor to the task); bring a downstream in at the result check (to anchor to legibility); consider a lateral at the midpoint if your team has one, to surface drift the other branches won't see.

## Limits

- **This demo is pedagogy, not a runnable single script.** The four calls are shown with illustrative outputs; running them requires a live agentic task to checkpoint.
- **Overhead is real.** ~20–40 min of panel wall-time per task. If the task itself is <1 hour, the overhead ratio is bad — skip the pattern.
- **Four checkpoints is a heuristic, not a law.** Some tasks need two (framing + result for quick work). Some need six (multi-phase builds with multiple midpoints). Adapt.
- **This pattern assumes you're running an agent, not writing code yourself.** If you're coding, the equivalent pattern is called "TDD with review" and is better served by test suites than panel calls.
