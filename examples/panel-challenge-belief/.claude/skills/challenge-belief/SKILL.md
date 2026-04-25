---
name: challenge-belief
description: Use when the operator states a held technical belief they're about to act on — an assertion about reality already shaping a decision ("RAG is sufficient", "the latency issue is network-bound", "we don't need observability yet") — and wants adversarial pressure before building on top of it. Symptoms — operator phrases it in the indicative ("X is Y", "we don't need Z") not as a question; resources (a roadmap line, a sprint, headcount, a rewrite) are about to depend on the belief being true; operator uses words like "obviously", "clearly", "enough", "we don't need".
---

# challenge-belief

Take one belief. Challenge it. Verdict: **holds up** or **does not hold up.**

The belief is challenged by lateral personas — outside observers who don't share the operator's framing. The prompt asks each for their strongest objection, an overlooked factor, and a condition that would change the operator's mind. The main persona synthesizes the verdict.

This is not a separate API endpoint. It's a regular `panel_client.py review` call with a challenge-shaped prompt.

## Steps

1. **Get the belief and what depends on it.**
   - **belief** — the single-sentence indicative assertion ("RAG is sufficient for our product").
   - **what depends on the belief** — what's about to be committed on top of it ("locking the Q3 roadmap with no fine-tuning line", "scoping next sprint assuming RAG carries us"). This goes into the prompt as context.

2. **Pick lateral participants.** Run `panel_client.py discover` if you don't already know the team's lateral personas. Pick 2–3 of them. If the team has no lateral personas, tell the operator — lateral is the whole point. Point them at panel.humx.ai → Profile → Personas.

3. **Run the panel. One bash call:**

   ```bash
   python .claude/skills/panel/panel_client.py review \
     --participants "lateral:<persona1>,lateral:<persona2>,lateral:<persona3>" \
     "$(cat <<'PROMPT'
   Challenge the following belief. The operator is about to act on it.

   BELIEF: <THE BELIEF, VERBATIM>

   WHAT DEPENDS ON THIS BELIEF BEING TRUE:
   <what's about to be committed on top of it>

   From your vantage, answer all three:
     1. **Strongest objection** — the single most load-bearing attack on this belief.
     2. **Overlooked factor** — something the operator hasn't weighted that they should.
     3. **Would change mind if** — a concrete condition whose appearance should make the operator revise.

   Main persona synthesis: does this belief hold up? Give a clear verdict — holds up or does not hold up — and name the single most load-bearing objection.
   PROMPT
   )"
   ```

   ~8–12 min run. Run the Bash tool in background mode; the client polls internally.

4. **Write `beliefs/YYYY-MM-DD-<slug>.md`.** Slug is 2–4 words summarizing the belief (`rag-is-sufficient`, `latency-is-network-bound`).

   ```markdown
   # <belief slug rendered as title>

   **Date:** YYYY-MM-DD
   **What depends on this belief:** <what's about to rely on it being true>

   ## Belief
   <the full assertion, unedited>

   ## Verdict
   <holds up / does not hold up — your read of the main persona's synthesis>

   ## Strongest objection
   <verbatim quote from the synthesis>

   ## Overlooked factors
   - <from the reads>

   ## Would change mind if
   - <from the reads>

   ## Per-persona reads
   ### <lateral persona 1>
   <their contribution, verbatim>

   ### <lateral persona 2>
   <their contribution, verbatim>

   ## Operator note (added after acting)
   <what the operator actually did with the verdict — filled in by hand>
   ```

5. **Route the operator on the verdict:**
   - **Does not hold up** — quote the strongest objection verbatim. Ask: revise the belief, delay the commitment, or proceed anyway with the objection accepted?
   - **Holds up** — still surface the "would change mind if" conditions. Tell the operator to keep the belief file open and revisit if any condition appears.

6. **Remind the operator** to fill in the "Operator note" after they act.

## Constraints

- **One belief per invocation.** Don't batch.
- **Write only to `beliefs/`.** No other files.
- **Never hand-edit `panel_state.json` or `.env`.**
- **Relay panel errors verbatim.** If state is missing, pass through the client's message telling the operator to run `setup`.

## Related

- Panel skill rules: `.claude/skills/panel/SKILL.md`
- Sibling demos (if present in `../`):
  - `panel-lateral-read` — lateral reads for emergent / cross-cutting effects
  - `hello-panel` — 2-minute onboarding
