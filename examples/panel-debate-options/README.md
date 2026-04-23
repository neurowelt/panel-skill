# panel-debate-options — example

You have two options. Both look defensible. You've been turning it over for a week. A plain LLM prompt either waffles ("it depends") or picks one confidently — and picking confidently is the wrong output, because the whole point is that the *trade-off* is the thing you need to see, not a winner.

This demo uses the `/panel` skill's **`debate`** intent to run an actual back-and-forth between personas with different vantages on the same decision. You get a transcript, then a summary. **The value isn't a recommendation. It's a clarified tension** — a sentence that names what you're actually choosing between, so your decision can be informed rather than accidental.

Self-contained. Python stdlib only. The panel skill is vendored under `.claude/skills/panel/`.

## Shape

```
  operator             debate-options              transcripts/YYYY-MM-DD-<slug>.md
  option A +       →   skill (runs `debate`)   →   back-and-forth, summary,
  option B +                                        "you're really choosing between"
  what's at stake
```

One skill (`debate-options`), one bash call (`panel_client.py debate`), one archived transcript. Panel returns a discussion-format output (each persona speaks multiple times, responding to what others said) plus a summary by the main persona.

## Why `debate` and not just `challenge` or `review`?

Each intent does a different job on a choice-shaped question:

| Intent | What it gives you | When it fits |
|---|---|---|
| `challenge` | Adversarial verdict on *one* held position | You've decided — can it survive objection? |
| `review` | Independent parallel reads + synthesis | You've shipped something — is it progress? |
| `ask` | One voice | Quick gut-check from a specific vantage |
| `explore` | Two-stage depth on open space | You don't yet have options — you have a question |
| **`debate`** | **Structured back-and-forth between vantages** | **You have two live options and need to see the tension** |

The difference from `challenge`: challenge attacks one position. Debate lets two positions attack *each other*, through the voices of personas with different stakes. That interaction — persona B responding to persona A's claim, persona A revising — is where the tension becomes visible. You can't get that from two independent reads; you need the actual back-and-forth.

## The key move: debate ends with clarified tension, not a recommendation

This is what makes `debate` different from every other decision-support pattern:

> **Debate's job is to name the trade-off sharply, not resolve it.**

A good debate ends something like: *"You're choosing between velocity-with-lock-in and control-with-ramp-up-cost. Both are defensible. Neither is cheap. The question isn't which to pick; it's which cost you'd rather pay."*

That framing is itself the deliverable. It doesn't tell you which option. It tells you *what you're really deciding between*, so that when you choose, you're choosing with eyes open instead of choosing a label.

**If a debate comes back with a confident recommendation, something went wrong** — probably a persona stepped out of their vantage, or the participant mix was too one-sided. Re-run with a different constellation.

## Quick start

1. `cp .env.example .env` — paste your `PANEL_API_KEY`
2. `python .claude/skills/panel/panel_client.py setup` — propose defaults; apply the printed `state set` commands
3. In Claude Code from this directory, describe your two options and what's at stake. The `debate-options` skill handles the rest.

## Example output

See [`transcripts/2026-04-20-in-house-eval-vs-vendor.md`](transcripts/2026-04-20-in-house-eval-vs-vendor.md) — a worked deliberation on *"build an in-house LLM eval tool (built by an external consultancy so your core team isn't pulled off product) vs. adopt a SaaS vendor."* Three vantages argue back and forth; the synthesis names the real trade-off (methodology ownership with handoff risk vs. consumed methodology with lock-in) cleanly.

## Forking this demo

| Type | What it is | When you fork |
|---|---|---|
| **Skeleton** (keep) | The skill's three-input shape (option A + option B + what's at stake); transcript file structure | Copy and keep |
| **Scaffolding** (delete) | The example transcript; the vendored panel skill if you have it globally | Delete after reading |
| **Pedagogy** (keep, then trim) | The "clarified tension not recommendation" framing; the intent-comparison table | Keep while internalizing; compress in your own voice later |

## Use this when

- You have **two** concrete options, named (not "something like X" or "some flavor of Y").
- Both options have real merit — you've been circling precisely *because* you can see both sides.
- You want the trade-off named sharply, not a recommendation.
- The choice affects a system with multiple stakeholders (engineering, product, ops) — debate naturally pulls in multiple vantages.

## Don't use this when

- You have one option and want it stress-tested — use `panel-challenge-belief`.
- You have an open question without options yet — use `ask` or `explore`.
- You want a ranked list of options — debate doesn't rank, it surfaces tension.
- The "two options" are actually the same thing in different words — first make sure the options are genuinely distinct.
- The choice is low-stakes and easily reversible — `ask` is faster.

> The worked example labels attribution by branch vantage (upstream / downstream / lateral) rather than by specific persona names. Real panel runs show your own team's persona names in those slots — run `panel_client.py discover` to see yours.

## Picking the participant constellation

For `debate`, the participant mix matters more than in other intents: each persona argues from their branch vantage, so the tension that surfaces is shaped by which vantages you pick. A good default is one upstream + one downstream + one lateral — three branches, three dimensions of the trade-off. If all three personas share a branch, you get three flavors of the same argument and miss the real tension. Mix branches.

## Limits

- **Two options, not three.** Debate scales poorly past two; a three-option debate becomes a voting pattern, not a tension-surfacing one. If you have three options, eliminate to two first (via `ask` or `challenge`), then debate the finalists.
- **Both options must be named and real.** "This vendor vs. maybe building something" is not debatable until "maybe building" is concrete enough to argue for. If one side is fuzzy, the debate is one-sided.
- **Runs 10–15 min.** Right for multi-week-consequence decisions; overkill for daily calls.
- **This demo doesn't pick a winner.** If you need a winner, pick *after* the debate with your own judgment — the transcript is your input, not your output.
