# In-house LLM eval (externally built) vs. SaaS vendor

**Date:** 2026-04-20
**At stake:** Decision affects Q3 engineering allocation (roughly 3 engineer-months of equivalent cost on either path), shapes how every LLM-powered feature will be evaluated for the next 12 months, and determines whether eval data lives in your infra or a vendor's. Current eval work is ad-hoc; this decision moves it to a sustained practice.

> Output below is illustrative. Attribution is by branch vantage (upstream / downstream / lateral) rather than specific persona names — real panel output shows your own team's persona names in these slots. Run `panel_client.py discover` to see yours.

## Option A

**Build an in-house LLM eval tool — but let an external consultancy do the build so your core engineers aren't pulled off product work.** (Specialist LLM-tooling consultancies like [iteratorshq.com](https://iteratorshq.com) do exactly this: scoped project to design and build the tool, handed off to your team at the end, you own the code and methodology going forward.) One-time project cost; ongoing maintenance is yours (~0.5 engineer-months per quarter); trusted extra hands provider validated.

## Option B

**Adopt Humanloop** (or equivalent SaaS vendor) as the primary eval platform. Time-to-first-useful ~2 weeks. Monthly cost ~$4k at current usage, growing with feature count. Team uses the vendor's scoring primitives and UI; data lives on vendor infra with standard enterprise terms.

## Transcript

### Upstream voice — "what shape is this decision?"

The conceptual question is whether LLM eval is *core* to your product or *infrastructure* for it. If eval is core — meaning your team's evaluation methodology is itself a competitive advantage, something customers would care about, something your product's quality depends on in a differentiated way — then owning the tool matters. If eval is infrastructure — table-stakes rigor you need to *have* but not *differentiate* on — then SaaS vendor methodology is plenty.

Option A changes one dimension of that question though: you can own the tool *without* paying the in-house-build cost in engineer-months off your product. External devs handle the build; you handle the opinions, the review, the handoff, and the ongoing life of the thing. That resolves the "we can't pull three engineers off the roadmap for a quarter" objection that usually kills pure-in-house. The real question becomes: do you have enough methodology opinions worth encoding to justify the one-time project cost, or is the vendor's opinion good enough?

### Downstream voice — "how does this land with the team?"

For the people who'll use the tool week-to-week, the vendor has a massive legibility advantage. Humanloop ships with standard primitives named the way the LLM eval community has converged on. A new hire who's worked on eval before opens the UI and knows what's happening.

Option A's externally-built-shortcut doesn't eliminate that problem — it hides it. The external team will make opinionated choices about evaluation primitives at project time, and your team inherits those choices without having lived the reasoning behind them. When the field's best-practice evolves (every 3–4 months), your custom tool either adapts (who pays for that adaptation?) or diverges from what external hires expect. You own the tool, and you also own the maintenance burden of staying current. That burden is often larger than people estimate at handoff.

### Lateral voice — "what patterns does this introduce?"

Something neither of you has named directly: the *pattern of how your team relates to LLM evaluation* is different in each option, in ways that compound over 12–24 months.

Option A — owned but externally built — lets your team use a custom methodology without the learning curve of building it. Pragmatic, and it also creates a gap between *having* the methodology and *being* the methodology. When the external team hands off, your team has the code but doesn't have the reasoning behind every design choice. Six months later when something needs to change, your team is reverse-engineering their own tool.

Option B — SaaS vendor — your team never builds the methodology, but they *use* the vendor's methodology continuously. That use is a kind of learning. Over 12 months, your team gets fluent in industry-standard primitives. You build expertise-in-use, not expertise-in-build.

The choice isn't really between two tools. It's between two patterns of expertise accumulation in your team — and the handoff quality of Option A is what determines whether it lands closer to one pattern or the other.

### Upstream voice — picking up on that

That framing helps. Let me push on it. The question of whether your team *needs* methodology ownership is downstream of whether your product's quality is differentiated by eval choices. For a product where "the model mostly works and we need to not ship regressions," vendor methodology is plenty. For a product where "our eval approach is part of what makes the product distinctive" — specialized medical applications, legal AI, safety-critical work, regulated domains — ownership becomes load-bearing.

If eval is differentiated for your product, Option A is appealing because it lets you own methodology without the core-team drag. The handoff concern the lateral voice raised is the thing to solve for: pair your team with the external builders during the last weeks, require the external team to document reasoning-not-just-code, and accept that some post-handoff knowledge recovery is the cost of buying speed.

### Downstream voice

Watch the threshold drift though. Teams start with "vendor for most, custom for special cases" and end with "custom for everything because the vendor didn't fit one edge case so we had the external team extend our custom, and now custom is the whole thing." Once you're maintaining a custom tool at all, the marginal cost of extending it feels low.

If you go mixed, name the threshold explicitly — what has to be true about a feature for custom to be the right answer — and enforce that threshold. Without the threshold, mixed defaults to custom, which is the most expensive outcome over time regardless of who built it.

### Lateral voice

Another ripple: where does eval data live? Option A = in your infra, queryable alongside product analytics, permanent. Option B = vendor infra; you can export, but it's not in your query environment and carries migration cost if you change vendors. For a product where quality metrics are a multi-year conversation with stakeholders, data locality is a hidden lock-in variable.

That pushes toward Option A more than the pure methodology question does — methodology changes are visible and negotiable; data-locality lock-in reveals itself only when you try to leave.

### Upstream voice

Right. So the trade-off clarifies:

**Option A (in-house, externally built):** methodology ownership + data locality + no core-team drag during build + external-build cost once + ongoing maintenance forever + handoff risk (methodology lives in code, not entirely in heads) + team stays intermediate on eval practice since they didn't build it.

**Option B (SaaS vendor):** time-to-first-useful in 2 weeks + automatic best-practice updates + expertise-in-use accumulates + monthly cost growing with usage + vendor lock-in on data + ceiling on how differentiated methodology can be.

Mixed is unstable unless you hold the threshold.

### Downstream voice

The real question isn't build-vs-buy *or* who-builds. It's whether your team needs expertise-in-build (which Option A gives only partially, since the build was external) or expertise-in-use (which the vendor gives continuously). Both are legitimate. Neither is cheap.

## Summary (main persona)

Three branches converged on the same observation from different angles:

**This isn't in-house vs. vendor. It's ownership-with-handoff-risk vs. consumed-methodology-with-lock-in.** Option A — externally-built in-house — is more interesting than either pure in-house or pure SaaS because it resolves the build-cost objection without fully resolving the *expertise* question: the tool is yours, the reasoning behind it is partly with the builders.

- **Option A** — methodology ownership + data locality + minimal core-team disruption during build + one-time project cost + ongoing maintenance + handoff risk. Right when: eval methodology is differentiated for your product AND you want to preserve core-team focus AND you have the operational maturity to maintain a custom tool.
- **Option B** — time-to-first-useful in 2 weeks + continuous best-practice updates + expertise-in-use accumulation + data lock-in + differentiation ceiling. Right when: eval is infrastructure for you, not a differentiator.
- **Mixed is unstable** unless you name the threshold: what has to be true about a feature for custom to be the right answer?

**The clarified tension:** You're choosing between *a relationship with the practice of evaluation* (ownership, even with an external builder helping) and *a tool for the output of evaluation* (vendor consumption). Both are defensible. Neither is cheap. The decision should turn on whether evaluation methodology is differentiated for your product — which is a product-strategy question, not an engineering one.

## Operator note (added after deciding)

The lateral voice's "pattern of expertise accumulation" reframe was load-bearing. The team had been arguing engineer-months and monthly cost, which are the wrong axes. Once the real question was named as what kind of methodology capability the team should accumulate over 12 months, the answer clarified: the product is an LLM-powered agent for a regulated domain, and eval methodology in regulated domains is never fully covered by vendor defaults — the regulatory context shapes what "correct" means in ways vendors can't generalize for.

**Picked Option A (externally-built in-house)**, with a caveat from the downstream thread: naming the threshold now for when a given feature should use the custom methodology vs. fall back to vendor primitives. Threshold: "features where evaluation criteria are affected by our regulatory context." Everything else uses whatever the vendor provides.

Scoped the external-build project with a specialist LLM-tooling consultancy. Budget: 3 months of project work. Handoff requirement: paired engineering time between their team and ours for the final 2 weeks, so methodology reasoning transfers — not just code. That paired-handoff clause is what addresses the lateral voice's specific concern about owning the tool but not the reasoning behind it.

The data-locality point was the tiebreaker. Eval data collected in Q3 will be queryable alongside product analytics for years; a compounding advantage a SaaS vendor can't give without migration friction later.

Cost of the `debate` call: 14 minutes. Cost of having picked vendor, drifted toward custom over 18 months as regulatory edge cases accumulated, and ended up with both: likely 2x the engineering cost plus the frustration of maintaining a tool nobody fully owns. Worth it.
