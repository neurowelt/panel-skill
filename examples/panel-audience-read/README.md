# panel-audience-read — example

You wrote a thing that's crystal clear to you — a README, a design doc, a proposal, a decision brief. You ship it. A reader who doesn't share your context opens it, gets lost in paragraph two, and closes the tab. You'll never hear about it. Your worldview stayed invisible to you the entire time.

This demo uses the `/panel` skill with a **downstream-heavy participant mix** to externalize the audience's read. Personas whose job is to model consumption rather than creation — typically downstream-branch roles like audience translation, coherence auditing, or implementation sequencing — look at your draft through the eyes of someone who *isn't you* and tell you exactly where your POV and their POV diverge.

The teaching move: **downstream personas translate from author-native to reader-native.** They don't critique your content — they report what a specific audience would actually make of it. That's a different job than upstream review, and it surfaces a different class of problems.

Self-contained. Python stdlib only. The panel skill is vendored under `.claude/skills/panel/`.

## Shape

```
  operator                audience-read                reads/YYYY-MM-DD-<slug>.md
  source doc  +       →   skill (explore with      →   per-persona reads, synthesis,
  target audience         downstream participants)     "where your POV and theirs diverge"
```

One skill (`audience-read`), one bash call (`panel_client.py explore --participants downstream:...`), one archived read per pass. The input is a piece of your own content + a description of the audience it's aimed at. The output is a brief that answers: *where does this land, where does it miss, and why.*

## Why downstream personas specifically?

Upstream personas pressure-test *your thinking* — they ask "did you see this blind spot in your goal?" That's valuable, but it's still a critique from inside the author's frame.

Downstream personas pressure-test *your communication* — they ask "what does this actually say to someone who doesn't already agree with you?" That's a different failure mode: you can have an internally coherent, well-reviewed plan that still bounces off every reader because it's written in your dialect.

Most LLM workflows conflate these. Single-prompt "please critique this doc" pulls both at once and tends to favor content over reception — the model simulates an informed reader, which is the reader *least* likely to misread you. Downstream panel personas deliberately simulate the *uninformed* reader, which is the one most of your audience actually is.

## Why `explore` as the intent?

`explore` is two-stage: each participant analyzes independently, then re-analyzes *with awareness of the others' reads*. That second stage matters here because one audience persona's read often contradicts another's — one downstream voice might say "too technical" while another says "too hand-wavy." The re-analysis is where they work out which is actually true for this audience, rather than leaving you with a contradiction to resolve by yourself.

For a quick single-angle read, use `ask` with a downstream persona as main. For depth across multiple audience-facing voices, use `explore` — it's what this demo defaults to.

## Quick start

1. `cp .env.example .env` — paste your `PANEL_API_KEY`
2. `python .claude/skills/panel/panel_client.py setup` — propose team/main persona defaults; apply the printed `state set` commands
3. In Claude Code from this directory, tell the `audience-read` skill:
   - A path to the source content (your draft)
   - A one-paragraph description of the intended audience

## Example output

See [`reads/2026-04-23-panel-harness-for-llm-tooling-engineers.md`](reads/2026-04-23-panel-harness-for-llm-tooling-engineers.md) — a worked read of the sibling `../panel-harness/README.md`, evaluated for *"an engineer who has seen a few LLM-agent demos before but has never heard of the panel skill."*

The author of panel-harness produced a README that felt crystal clear from inside. The downstream read surfaces where that internal clarity collapses for a reader who doesn't share the author's context — which is the exact failure mode this demo is designed to catch.

## Forking this demo

| Type | What it is | When you fork |
|---|---|---|
| **Skeleton** (keep) | The skill's two-input shape (source path + audience description); the downstream-heavy participant selection; the read file structure | Copy and keep — this is the pattern |
| **Scaffolding** (delete) | The example read in `reads/`; the reference to `../panel-harness/README.md`; the vendored `.claude/skills/panel/` if you have `panel` installed globally | Delete after reading |
| **Pedagogy** (keep to learn, delete later) | The "Why downstream personas" and "Why `explore`" sections of this README and the skill doc | Keep while you're internalizing the move; rewrite or trim once you have it |

> The worked example labels attribution by branch vantage (downstream / lateral) rather than by specific persona names. Real panel runs show your own team's persona names in those slots — run `panel_client.py discover` to see yours. If your team has no downstream personas, that's the adaptation pointed at: add translation-oriented personas at panel.humx.ai → Profile → Personas.

## Limits

- **The skill reads text, not multimedia.** If your content is a diagram, screenshot, or video, you're translating it to prose for the read — which is itself a lossy translation. Good for prose, decks-as-outlines, and structured docs; poor for UI or visual work.
- **Audience description quality dominates output quality.** "Our customers" is too vague; "a VP of engineering at a 200-person B2B SaaS who's skeptical of AI tooling" is usable. The clearer the audience, the sharper the read.
- **One source per run.** Don't batch. If you have a suite of docs, the skill reads one at a time; batching into one call muddles the audience read.
- **`explore` is the most expensive intent** — 12–20 min per call, every participant runs twice. Worth it for high-stakes external content (public READMEs, investor decks, customer-facing proposals); overkill for internal memos.
- **This demo doesn't produce a rewrite.** It produces a diagnostic. The rewrite is your job, informed by the read.
