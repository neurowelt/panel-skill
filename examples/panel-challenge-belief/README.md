# panel-challenge-belief — example

Strong technical beliefs are easy to form and hard to stress-test. Most of them pass the solo sniff-test — you have reasons, the reasons sound good to you, and the colleague you ask tomorrow agrees because they share your context. Then you build on top of the belief for six weeks and discover the one objection you never heard was load-bearing.

This demo uses the `/panel` skill's **`challenge`** intent to put adversarial pressure on a held belief *before* you build on top of it. You submit the belief + supporting evidence + what's about to depend on it; adversarial personas attack from independent vantages and return a machine-readable verdict: `holds_up`, `confidence`, `strongest_objection`, `overlooked_factors`, `would_change_mind_if`.

You archive the belief + verdict together. Next time you're about to rely on "we don't need X" or "Y is enough for our use case," there's a trail — and, more often than you'd like, a reason to re-examine.

Self-contained. Python stdlib only. The panel skill is vendored under `.claude/skills/panel/`.

## What a belief is (and isn't)

A belief is a claim about reality you're acting on, whether or not you've written it down.

| Examples of beliefs | Examples of *not*-beliefs |
|---|---|
| "RAG is sufficient for our product; we don't need fine-tuning." | "Should we use RAG or fine-tuning?" (exploration) |
| "Our tail latency problem is network-bound, not code-bound." | "Latency is bad." (observation) |
| "Two backend engineers can own this migration." | "Who should own the migration?" (unframed) |
| "We don't need LLM observability yet." | "We should look into observability." (intention) |

A belief has a **verb in the indicative** (*"is,"* *"won't,"* *"doesn't need"*), not a question mark and not a future-tense plan. It's an assertion about what's true — and it's already shaping your decisions whether you examine it or not.

## Shape

```
  operator                challenge-belief              beliefs/YYYY-MM-DD-<slug>.md
  belief + evidence    →  skill (runs `challenge`)  →   belief, evidence, verdict,
  + what-depends-on-it                                  objections, operator note
```

One skill (`challenge-belief`), one bash call (`panel_client.py challenge`), one archived markdown file per belief. No orchestration — the demo teaches the *intent*, not scaffolding.

## Why `challenge` instead of just asking someone?

A plain LLM prompt — even "play devil's advocate on this" — simulates objection from inside your own framing. Same for asking a colleague who shares your context. Both sharpen your belief by rephrasing your assumptions, not by *not sharing* them.

`challenge` externalizes the attack to personas with fixed independent vantages. They generate objections by *not sharing your framing*, not by steelmanning it. The return is structured so you can branch on it (`holds_up: false` → re-examine; `holds_up: true` → keep watching the `would_change_mind_if` conditions as reality unfolds).

That's the difference between *sharpening a belief* and *finding the one attack that makes you re-examine it*.

## Quick start

1. `cp .env.example .env` — paste your `PANEL_API_KEY`
2. `python .claude/skills/panel/panel_client.py setup` — propose team/main persona defaults; apply the printed `state set` commands
3. In Claude Code from this directory, state a belief you're acting on. The `challenge-belief` skill handles the rest.

## Example output

See [`beliefs/2026-04-18-rag-is-sufficient.md`](beliefs/2026-04-18-rag-is-sufficient.md) — a worked entry: the belief *"RAG is sufficient for our product; we don't need fine-tuning"* stress-tested before committing the Q3 roadmap. Verdict `holds_up: false`, strongest objection quoted verbatim, operator's after-note showing what they actually did with the verdict.

## Forking this demo

| Type | What it is | When you fork |
|---|---|---|
| **Skeleton** (keep) | The skill's bash-call shape; the belief-file structure; `holds_up` routing | Copy and keep — this is the pattern |
| **Scaffolding** (delete) | The worked example in `beliefs/`; the vendored `.claude/skills/panel/` if you have `panel` installed globally | Delete after reading |
| **Pedagogy** (keep to learn, delete later) | The "what a belief is" table; the "why `challenge`" prose | Keep while internalizing the pattern; rewrite in your own voice later |

## Use this when

- You're about to commit resources (a roadmap line, a sprint, headcount, a rewrite) based on a belief you haven't externally attacked.
- You notice yourself using words like "obviously," "clearly," "enough," "we don't need" — those are belief-flavored.
- A solo decision has been made but hasn't been challenged by anyone who doesn't share your context.

## Don't use this when

- You're still exploring options — `challenge` on an unformed belief returns generic objections. Use `ask` or `debate` first.
- You're looking for validation, not pressure — this skill will find an attack if one exists. If you'd be upset by a `holds_up: false`, don't fire.
- The belief is low-stakes and easily reversible — 8–15 min of `challenge` time is worth it for load-bearing beliefs, not for casual ones.

> The worked example labels attribution by branch vantage (upstream / lateral) rather than by specific persona names. Real panel runs show your own team's persona names in those slots. Run `panel_client.py discover` to see yours. The skill itself doesn't hardcode names; `--participants` is passed per call.

## Limits

- **One belief per invocation.** Don't batch; each belief gets its own verdict and archive.
- **Archives are flat files keyed by date-slug.** No index; scan `beliefs/` by filename.
- **`challenge` takes 8–15 min** per call. Right for load-bearing beliefs you're about to commit on top of; overkill for disposable ones. For quick takes use `ask`.
- **This demo doesn't produce a replacement belief.** It produces a diagnostic. The next belief is your job, informed by the verdict.
