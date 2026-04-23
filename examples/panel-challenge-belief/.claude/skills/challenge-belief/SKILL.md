---
name: challenge-belief
description: Use when the operator states a held technical belief they're about to act on — an assertion about reality already shaping a decision ("RAG is sufficient", "the latency issue is network-bound", "we don't need observability yet") — and wants adversarial pressure before building on top of it. Symptoms — operator phrases it in the indicative ("X is Y", "we don't need Z") not as a question; resources (a roadmap line, a sprint, headcount, a rewrite) are about to depend on the belief being true; operator uses words like "obviously", "clearly", "enough", "we don't need". NOT for exploratory questions, option comparisons, or progress checks.
---

# challenge-belief

## What a belief is (and isn't)

A belief is a claim about reality the operator is acting on, whether they've written it down or not. It has a verb in the indicative, not a question mark or a future-tense plan.

| Is a belief | Is not a belief |
|---|---|
| "RAG is sufficient for our product." | "Should we use RAG or fine-tuning?" |
| "Our tail latency is network-bound." | "Latency is bad." |
| "We don't need LLM observability yet." | "We should look into observability." |
| "Two engineers can own this migration." | "Who should own the migration?" |

If what the operator has is a question, an observation, or an intention — redirect. `challenge` on an unformed belief returns generic objections and wastes the run.

## Before firing — verify it's a belief

`challenge` is ~10 minutes of panel work. Three checkpoints:

1. **Is there an indicative assertion?** (e.g. "X is enough" / "we don't need Y" / "Z causes W") — if the framing is still "should we?" or "what if?", redirect to `panel_client.py ask` or `debate`.
2. **Is something about to depend on the belief being true?** (a roadmap line being locked, a sprint being scoped, headcount allocated, a rewrite begun) — if nothing depends on it, the belief is idle; it can be challenged later when it matters, or redirect to `explore` if the operator wants broader perspective.
3. **Is the evidence more than one item after probing?** — single-item evidence lists mean the belief hasn't been pressure-tested internally. Probe for more before firing. If the operator can't produce more, the belief is held on vibes, not reasons; redirect to `debate` or `ask`.

All three must be yes. If any is no, **do not fire `challenge`.** Name which checkpoint failed and which intent fits instead.

## Why `challenge` specifically

Other panel intents pull a belief apart at different angles:

| Intent | Question it answers | What you get |
|---|---|---|
| `ask` | "What does one experienced voice say about this?" | One persona, quick |
| `review` | "Is this progress toward the goal?" | Upstream independent reads + synthesis, forward-looking |
| `explore` | "What are the perspectives on this space?" | Two-stage multi-angle depth |
| `debate` | "What's the tension between competing takes?" | Back-and-forth transcript |
| **`challenge`** | **"Will this belief survive real objection?"** | **Structured verdict: `holds_up` + the strongest attack** |

Use `challenge` when the operator needs an answer to *"is this belief load-bearing-grade?"* not *"how should I think about this?"* The structured return (`holds_up: bool`, `strongest_objection: string`, `would_change_mind_if: list`) is designed to be acted on directly.

## Steps

1. **Extract three things from the operator's description:**
   - **belief** — the single-sentence indicative assertion ("RAG is sufficient for our product").
   - **evidence** — specific supporting facts. One short string per item, collected as repeated `--evidence "..."` flags. Probe for multiple items before firing.
   - **what depends on the belief** — what's about to be committed on top of it ("locking the Q3 roadmap with no fine-tuning line", "scoping next sprint assuming RAG carries us"). The panel client's `--decision-pending` flag carries this — use it verbatim.

2. **Invoke `challenge`. One bash call:**

   ```bash
   python .claude/skills/panel/panel_client.py challenge \
     "<BELIEF>" \
     --evidence "<EVIDENCE ITEM 1>" \
     --evidence "<EVIDENCE ITEM 2>" \
     --decision-pending "<WHAT'S ABOUT TO DEPEND ON THIS BELIEF>"
   ```

   `--participants` is inherited from panel state (set during `panel_client.py setup`). Override **only** if this belief needs a different constellation — e.g., pull in a `downstream:<operator_translator>` for a belief with heavy adoption implications. The inherited default is right for most.

   This is a long run (8–15 min). The panel client polls internally; run the Bash tool in background mode and wait for the notification.

3. **Write `beliefs/YYYY-MM-DD-<slug>.md`.** The slug is 2–4 words summarizing the belief (e.g., `rag-is-sufficient`, `latency-is-network-bound`, `no-observability-yet`). Structure:

   ```markdown
   # <belief slug rendered as title>

   **Date:** YYYY-MM-DD
   **What depends on this belief:** <what's about to rely on it being true>

   ## Belief
   <the full indicative assertion, unedited>

   ## Evidence
   - <item 1>
   - <item 2>

   ## Verdict
   - **Holds up:** <true / false>
   - **Confidence:** <0.00–1.00>

   ## Strongest objection
   <verbatim from panel>

   ## Overlooked factors
   - <item>

   ## Would change mind if
   - <item>

   ## Per-persona objections
   ### <persona name>
   <their contribution, verbatim>

   ## Operator note (added after acting)
   <what the operator actually did with the verdict — revised the belief? kept it with the objections accepted? delayed the commitment? — filled in by hand>
   ```

4. **Route the operator on `holds_up`:**
   - **`holds_up: false`** — quote the strongest objection verbatim. Ask: revise the belief, gather more evidence, delay the commitment, or proceed anyway with the objection accepted? Do not assume.
   - **`holds_up: true`** — still surface `would_change_mind_if`. Those are the conditions to watch for as reality unfolds. Tell the operator to keep the belief file open and revisit if any of those conditions appear.

5. **Tell the operator** the file has been written and remind them to fill in the "Operator note" after they act. Without the note, the file is a verdict with no outcome — useless for revisiting the belief six months later.

## Rationalizations and counters

| Rationalization | Counter |
|---|---|
| "Operator wants a quick take — `ask` would be faster." | If they asked to challenge a belief, they want pressure on the belief, not a paraphrase of it. Don't downgrade the intent. |
| "The belief is obviously true — `challenge` is overkill." | If the belief were obviously true under scrutiny, this skill wouldn't have been triggered. "Obvious" is often the operator's blind spot, not the belief's property. |
| "Personas don't know our codebase/context — they'll miss the real objection." | `challenge` passes evidence as context. Personas are opinionated, not clueless. Their job is vantage, not local detail. The best objections come from not sharing the operator's context. |
| "I can infer evidence from conversation history — no need to ask." | Unstated evidence is often the shakiest part of the belief. Surfacing it before challenge often resolves the belief without the panel call. Make the operator list it. |
| "The belief is small / low-stakes / can be revised later." | Then this skill wasn't the right call. But if it was triggered, something *did* feel load-bearing enough to want pressure — follow through. |

## Red flags — stop and reshape

- Operator hasn't stated a belief, just described a problem or asked a question → run `ask` first.
- Operator wants to compare two beliefs / options → use `debate`, not `challenge`.
- Operator is venting or seeking reassurance, not stress-testing → no panel call needed.
- Evidence list is one item after probing → belief isn't developed enough; redirect to `debate` or `ask`.
- The belief is about the future ("we won't need X") with no falsifiable near-term test → add `would_change_mind_if` conditions explicitly, since the verdict's value depends on watchable signals.

## Constraints

- **One belief per invocation.** Don't batch.
- **Write only to `beliefs/`.** No other files.
- **Never hand-edit `panel_state.json` or `.env`.** See `.claude/skills/panel/SKILL.md`.
- **Relay panel errors verbatim.** If state is missing, the panel client tells the operator to run `setup`. Pass that through; don't bootstrap state yourself.

## Related

- Panel skill rules and all intents: `.claude/skills/panel/SKILL.md`
- Sibling demos (if present in `../`):
  - `panel-harness` — goal lifecycle (`ask` → `review` → per-increment `review`)
  - `panel-audience-read` — translating author-POV to reader-POV (`explore` with downstream personas)
  - `hello-panel` — 2-minute onboarding, two-vantage contrast
