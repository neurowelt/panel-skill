# panel-challenge-belief — example

Strong technical beliefs are easy to form and hard to stress-test. You have reasons, the reasons sound good to you, the colleague you ask tomorrow agrees because they share your context. Then you build on top of the belief for six weeks and discover the one objection you never heard was load-bearing.

This demo takes one belief, puts adversarial pressure on it, and gives you a verdict: **holds up / does not hold up.** That's it.

It runs `panel_client.py review` with **lateral personas** (outside observers who don't share your framing) and a prompt shaped as a challenge — asking each persona for their strongest objection, an overlooked factor, and the condition that would change the operator's mind. The main persona synthesizes the verdict.

You archive the belief + verdict together under `beliefs/YYYY-MM-DD-<slug>.md`. Next time you're about to rely on "we don't need X" or "Y is enough for our use case," there's a trail.

Self-contained. Python stdlib only. The panel skill is vendored under `.claude/skills/panel/`.

## Shape

```
  operator               challenge-belief                      beliefs/YYYY-MM-DD-<slug>.md
  belief              →  skill (runs review + lateral)     →   belief, verdict,
  + what depends on it   with a challenge-shaped prompt        strongest objection, operator note
```

One skill (`challenge-belief`), one bash call (`panel_client.py review --participants lateral:...`), one archived markdown file per belief. The "challenge" shape comes from the prompt, not from a specialized endpoint — so it runs on the same fast `parallel_with_main` mode as every other response intent.

## Why lateral personas?

A plain LLM prompt — even "play devil's advocate on this" — simulates objection from inside your own framing. Same for asking a colleague who shares your context.

Lateral personas are outside observers — they stand next to you and see your gaps. They're **not you**. Their objections come from outside your frame, which is exactly the vantage that attacks a belief usefully.

## Quick start

1. `cp .env.example .env` — paste your `PANEL_API_KEY`
2. `python .claude/skills/panel/panel_client.py setup` — propose team/main persona defaults; apply the printed `state set` commands
3. `python .claude/skills/panel/panel_client.py discover` — see your team's lateral personas
4. In Claude Code from this directory, state a belief you're acting on. The `challenge-belief` skill handles the rest.

## Forking this demo

| Type | What it is | When you fork |
|---|---|---|
| **Skeleton** (keep) | The skill's bash-call shape (review + lateral + challenge-shaped prompt); the belief-file structure; holds-up / doesn't-hold-up routing | Copy and keep — this is the pattern |
| **Scaffolding** (delete) | The vendored `.claude/skills/panel/` if you have `panel` installed globally | Delete after reading |
| **Pedagogy** (keep to learn, delete later) | The "why lateral" prose | Keep while internalizing the pattern; rewrite in your own voice later |

## Use this when

- You're about to commit resources (a roadmap line, a sprint, headcount, a rewrite) based on a belief you haven't externally attacked.
- You notice yourself using words like "obviously," "clearly," "enough," "we don't need."
- A solo decision has been made but hasn't been challenged by anyone who doesn't share your context.

## Don't use this when

- You're looking for validation, not pressure.
- The belief is low-stakes and easily reversible.
- Your team has no lateral personas — add some at panel.humx.ai → Profile → Personas.

> Real panel runs show your own team's persona names in each slot. Run `panel_client.py discover` to see yours.

## Limits

- **One belief per invocation.** Don't batch; each belief gets its own verdict and archive.
- **~8–12 min per call.**
- **The verdict is the main persona's synthesis.** Your Claude Code session reads the synthesis and decides "holds up / does not" — not an API boolean.
- **This demo produces a diagnostic, not a replacement belief.** The next belief is your job, informed by the verdict.
