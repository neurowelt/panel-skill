# RAG is sufficient; we don't need fine-tuning

**Date:** 2026-04-18
**What depends on this belief:** Q3 roadmap being locked next Friday with no fine-tuning line item. Engineering headcount for Q3 assumes RAG is load-bearing and fine-tuning is "later, if at all."

> Output below is illustrative. Attribution is by branch vantage (upstream / lateral) rather than specific persona names — real panel output shows your own team's persona names in these slots. Run `panel_client.py discover` to see yours.

## Belief

RAG is sufficient for our product's generation quality needs. We don't need fine-tuning. Our retrieval layer covers the domain-specific knowledge our users ask about, and the base model's general capability handles everything retrieval surfaces adequately.

## Evidence

- Current retrieval hit rate on representative user queries is 89% (internal eval set, last measured three weeks ago).
- User-reported "wrong answer" rate over the last 30 days is 4.2% — well under our 6% threshold.
- Latency for the RAG path is acceptable (p99 ~1.8s); a fine-tuned path would add ~400ms on our current infra.
- Fine-tuning infrastructure would cost roughly 2 engineer-months to stand up plus ongoing drift-management overhead.
- Our vendor's RAG tooling has matured significantly in the last two quarters; fine-tuning tooling has not.

## Verdict

- **Holds up:** false
- **Confidence:** 0.72

## Strongest objection

*from `Upstream voice — retrieval-side read`:*

> The 89% retrieval hit rate is measured on a "representative" eval set, but you haven't said how representative stays representative. If your product is growing — especially growing into new vocabulary, new industries, new user segments — the eval set's representativeness is always trailing reality by exactly the interval between refreshes. The 89% is a snapshot, not a floor. More damningly: the 4.2% user-reported "wrong answer" rate doesn't catch silent retrieval misses, where the model generates a plausible-sounding answer from retrieved docs that *are related* but don't actually answer the question. Users don't report those as wrong — they report those as "okay, I guess" and stop asking. You won't see the drift in your error metrics until a competitor does catch it.
>
> Fine-tuning isn't only — or even primarily — about covering what retrieval misses. It's about shaping *behavior*: tone, refusal patterns, answer structure, rejection of ambiguous queries. Retrieval can't touch those. If your product has any voice-of-brand or structured-output requirement, your belief conflates two problems: knowledge coverage (where RAG is genuinely strong) and behavior shaping (where it's weak).

## Overlooked factors

- The eval set is measured every ~6–8 weeks. Between refreshes, you have no signal on whether representativeness is holding.
- Silent retrieval misses (plausible-but-wrong answers from related-but-wrong docs) don't register in user-reported error rates — the most insidious failure mode for RAG.
- The 2-engineer-month fine-tuning cost is framed against infra; it's not framed against what fine-tuning would unlock (structured-output reliability, refusal behavior, brand-voice shaping) that no amount of retrieval improvement reaches.
- "Fine-tuning tooling hasn't matured" is a vendor-dependent claim. Open-weight fine-tuning has matured significantly; the belief implicitly assumes you'd fine-tune on your current vendor's closed path.
- No mention of how belief survival will be re-evaluated. If this belief is locked into Q3 roadmap, when is it legitimate to re-open? Without a pre-committed reopening criterion, "we don't need fine-tuning" becomes load-bearing indefinitely.

## Would change mind if

- Silent-miss rate analysis showed that a measurable fraction of "okay-ish" user interactions were actually retrieval failures that users didn't flag.
- The product developed any structured-output requirement (JSON shape contract, specific refusal taxonomy, brand-voice consistency) that RAG alone couldn't reliably deliver.
- The eval set's representativeness were shown to lag reality by more than ~10% on new user-segment vocabulary.
- An alternative fine-tuning path (open-weight, in-house) was shown to cost substantially less than the 2-engineer-month estimate, changing the cost side of the framing.

## Per-persona objections

### Upstream voice — retrieval-side read

The 89% retrieval hit rate is a snapshot against a sample-set that isn't being continuously validated against evolving user vocabulary. More importantly, the 4.2% "wrong answer" rate doesn't capture silent misses — the plausible-but-wrong answers generated from related-but-irrelevant retrieved context. Those are the expensive failures; users don't report them, they just lose trust.

### Upstream voice — model-behavior read

You're reasoning about RAG vs. fine-tuning as if they solve the same problem — knowledge coverage. They don't. Fine-tuning shapes *behavior*: answer structure, refusal patterns, tone, edge-case handling. Retrieval has no leverage on those. If your product has any structured output requirement or brand-voice consistency need, the belief is conflating two different problems. Check whether there are product requirements you've been informally meeting in prompt engineering that a fine-tune would make robust.

### Lateral voice — operational-ripple read

"Fine-tuning infra would add 2 engineer-months" is a framing that implicitly compares it to the cost of *not* fine-tuning — but you haven't priced the cost of *not*. If silent retrieval misses erode trust by 5% year-over-year, that's a much larger number than 2 engineer-months. Price both sides of the decision, not just the one that supports the belief. Also: locking Q3 roadmap with no fine-tuning line means the earliest re-open is Q4. Is a belief held for a minimum of 6 months load-bearing-grade-reviewed? If not, put a mid-Q3 reopening checkpoint in the roadmap as a hedge.

## Operator note (added after acting)

The silent-miss point landed hardest. We thought our 4.2% wrong-answer rate was a floor on errors. Ran a qualitative review of 200 "okay-ish" interactions (user asked, got an answer, didn't flag) and found roughly 11% were actually retrieval failures where the answer was plausible from related-but-wrong context. That's ~2.5x our reported error rate invisible in metrics.

The behavior-shaping point was the second blow. We'd been doing three rounds of prompt engineering per release to keep refusal behavior consistent; a fine-tune would make that robust instead of brittle.

**Verdict acted on:** Unlocked a fine-tuning spike for Q3 (not a full rollout — a 2-sprint evaluation budget) and added a mid-Q3 reopening checkpoint to the roadmap for this belief. If the spike shows measurable improvement on the silent-miss and refusal-consistency axes, the belief is replaced with a more specific one ("our RAG + fine-tuned behavior layer is sufficient") and fine-tuning becomes a first-class line item in Q4 planning.

Cost of the `challenge` call: 12 min. Cost of having locked Q3 on the original belief and discovering the silent-miss problem in Q4: probably two quarters of erosion before we noticed. Worth it.
