---
name: panel
command: panel
description: Multi-persona analysis. Use when the user wants a persona-driven deep dive, second opinion, adversarial pressure on a held position, debate, or side-by-side takes. Triggers on "ask the panel", "run a discussion", "get a panel take", "stress-test this", "challenge this position", etc.
argument-hint: [setup/help/discover/ask/debate/explore/challenge <question, topic, or position>]
---

# Companion Panel

Seven intents, one Bash call each. **First-time users start with `setup`.** After that, pick the intent that matches what the user actually wants.

| Intent | When to use | Wall time | Command shape |
|---|---|---|---|
| **setup** | First call in a new working directory (or when the user has no `.claude/panel_state.json`) | seconds | `panel_client.py setup [optional one-line hint]` |
| **help** | User has a specific topic and is unsure which intent fits | seconds | `panel_client.py help "$TOPIC"` |
| **discover** | User wants to see which teams, personas (with short guides when available), modes, and models are usable | seconds | `panel_client.py discover` |
| **ask** | Quick single-persona take | 1–2 min | `panel_client.py ask "$Q"` |
| **debate** | Back-and-forth deliberation + transcript | 10–15 min | `panel_client.py debate "$Q"` |
| **explore** | Deep multi-perspective synthesis | 12–20 min | `panel_client.py explore "$Q"` |
| **challenge** | User has a position — stress-test it adversarially (verdict: holds_up / strongest_objection / would_change_mind_if) | 8–15 min | `panel_client.py challenge "$POSITION" [--evidence ...] [--decision-pending ...]` |

**`challenge` is the one to reach for mid-session** — by turn 40 the user usually has a plan, not a question. `challenge` attacks the plan and returns a structured verdict (`holds_up: bool`, `confidence: 0.0–1.0`, `strongest_objection`, `overlooked_factors`, `would_change_mind_if`) that you can branch on directly.

All commands are run from the repo root with `.venv/bin/python .claude/skills/panel/panel_client.py <intent> ...`.

## Agent rules (read before running anything)

- **One intent = one Bash call.** Map the user's request to exactly one row of the table above and run that single command. Do not chain subcommands, do not compose pipelines, do not invent flags that aren't shown.
- **If the CLI errors, relay the error verbatim.** Every intent that needs state (`ask` / `debate` / `explore` / `challenge`) prints a clear message telling the user to run `panel setup` first when `.claude/panel_state.json` is missing. Pass that through — do not try to bootstrap state yourself, do not hand-edit the JSON, do not guess values.
- **Never touch `.env` or `panel_state.json` directly.** Use `panel_client.py state set <key> <value>` / `state clear` if state genuinely needs changing. If `PANEL_API_KEY` is missing, ask the user to set it — do not read, write, or create `.env` files.
- **`setup` requires user confirmation before applying.** It prints a plan plus the exact shell commands to apply it. Show the plan, wait for an explicit yes, then run the commands.

After `setup` has been applied once, `ask` / `debate` / `explore` / `challenge` inherit team, main persona, project, and per-intent default participants from `.claude/panel_state.json` — so the minimal call shape becomes just `panel_client.py <intent> "$input"` with no flags.

**Long runs** (`debate`, `explore`): invoke the Bash tool with `run_in_background: true`. The client blocks internally on polling; you get notified when it finishes. No bash poll loops needed — the client handles timeout and transient-failure retries on its own.

**Short runs** (`help`, `ask`): invoke normally; they return quickly.

## Enabling web search (`--search`)

`ask` / `debate` / `explore` / `challenge` all accept `--search`. When passed, the turn runs with the model's live web search enabled — the persona still shapes interpretation, it just gets fresh data to reason over. Omit the flag and the turn runs without search (default).

**Two sources of decision — use either or both:**

1. **The advisor tells you.** `help "$TOPIC"` output includes a line `web search: recommended — pass --search on the follow-up ...` when the advisor judges the topic benefits from search. If you see it, add `--search` to the follow-up intent call.
2. **Your own read of the user's request.** You do not need to run `help` first. Add `--search` when the topic depends on information Claude cannot reliably know from training:
   - current events, recent releases, new library versions
   - live pricing, availability, rankings, statistics
   - specific external docs, URLs, or API references
   - named products, people, or organizations you cannot identify with confidence
   - any fact-heavy question about the present state of the world

   **Do not add `--search`** for pure reasoning, design critique, architectural debate, introspection, or self-contained topics — search costs more per turn and dilutes the persona's lens when fresh data isn't what the question needs.

**Syntax:** append `--search` to the intent, e.g.

- `panel ask --search "what changed in FastAPI 0.115?"`
- `panel explore --search "trade-offs of the new React compiler vs memo"`
- `panel challenge --search "shipping this before the Stripe PSD3 deadline is safe"`

## First-time use — always start with `setup`

**If `.claude/panel_state.json` doesn't exist in the working directory, run `panel setup` first.**

`setup` is an onboarding advisor. It walks the user's teams + personas server-side and proposes:

- a primary team + main persona to anchor work on
- an optional first project to create (so panel memory accumulates across calls)
- per-intent default participants (for `challenge`, `panel`, `debate`, `answer`)

It prints the plan PLUS the exact `panel_client.py projects create ...` + `panel_client.py state set ...` commands needed to apply it. **Do not auto-apply** — show the user the plan and the commands, let them confirm, then execute via Bash.

If the advisor returns an `overview` saying the user has no teams, they need to contact support to get a team created — the user cannot create teams themselves. Relay that message.

After applying setup, every subsequent call inherits all the context it needs from state.

## Before the first real call

- **`PANEL_API_KEY`** must be set (in the shell or in `.claude/skills/panel/.env`). **Never read, write, or create `.env` files** — ask the user to do it if the key is missing.
- **If the user wants a specific topic suggestion rather than a full setup**, use `help "$TOPIC"` instead of `setup` — `help` is topic-driven and suggests a specific mode + participants + reshaped prompt. `setup` is state-driven.
- **Inspection:** use the `discover` intent for teams/personas/modes. `panel_client.py state show` prints the current panel state. `panel_client.py state clear` starts fresh.

## How state gets consumed

Once `setup` has been applied (or state has been seeded manually), each intent reads a specific set of keys:

| Intent | Reads from state |
|---|---|
| `ask` | `team`, `answer_persona` (falls back to `main_persona`), `project` |
| `debate` | `team`, `main_persona`, `debate_participants` (falls back to `default_participants`), `project` |
| `explore` | `team`, `main_persona`, `panel_participants` (falls back to `default_participants`), `project` |
| `challenge` | `team`, `main_persona`, `challenge_participants` (falls back to `default_participants`), `project` |

Every call with a `project` in state enables expanded memory automatically — the whole point of a project is memory carrying across calls.

## After the result

The client prints a structured, human-readable result. Pass it to the user directly or summarize as they asked. The result's `payload.kind` tells you the shape:

- `answer` — one persona, one `content` block
- `parallel` — side-by-side `contributions[]`
- `synthesis` — `synthesizer` + `synthesis` + `contributions[]`
- `discussion` — `transcript[]` + `summarizer` + `summary`
- `challenge` — `holds_up: bool` + `confidence` + `strongest_objection` + `overlooked_factors[]` + `would_change_mind_if[]` + `contributions[]`

No per-mode parsing needed — the renderer already presents them appropriately.

**Special handling for `challenge`:** route on `holds_up`.

- `holds_up: false` → tell the user the plan did **not** survive the strongest objection, quote it, and ask whether they want to revise before proceeding.
- `holds_up: true` → the plan survives, but always scan `would_change_mind_if` anyway — those are the conditions to keep watching for as the user executes.

## What the user asked

$ARGUMENTS
