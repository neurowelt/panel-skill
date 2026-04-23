---
name: panel
command: panel
description: Multi-persona analysis. Use when the user wants a persona-driven deep dive, second opinion, adversarial pressure on a held position, debate, or side-by-side takes. Triggers on "ask the panel", "run a discussion", "get a panel take", "stress-test this", "challenge this position", etc.
argument-hint: [setup/help/discover/ask/debate/explore/challenge <question, topic, or position>]
---

# Companion Panel

## Terminology (read this first)

The word **panel** is overloaded. Three distinct things:

- **The panel skill** = this whole thing. What you invoke via `panel_client.py <intent>` (or `/panel` in Claude Code). When we say "the panel skill," we mean the tool.
- **Intent** = the CLI command you run. One of `ask` / `debate` / `explore` / `review` / `challenge` (plus the non-response intents `setup` / `help` / `discover`). Each intent is one Bash call.
- **Mode** = the server-side response shape that an intent produces. Modes: `answer`, `panel`, `discussion`, `parallel`, `parallel_with_main`, `answer_crumbs`.

The `panel` **mode** (two-stage: each participant analyzes, then re-analyzes with enriched context, then the main persona synthesizes) is what `explore` uses. It is the most expensive mode — not because the skill is expensive, but because `panel` mode runs every participant twice. "Panel mode is costly" ≠ "the panel skill is costly."

Some state key names are legacy (named after modes, not intents) — see "How state gets consumed" below.

## Intents

Each response intent is one Bash call. Start with `setup` on a new working directory.

| Intent | Mode produced | When to use | Wall time | Command shape |
|---|---|---|---|---|
| **setup** | — | First call in a new working directory (no `.claude/panel_state.json` yet) | seconds | `panel_client.py setup [hint]` |
| **help** | — | Specific topic, unsure which intent fits | seconds | `panel_client.py help "$TOPIC"` |
| **discover** | — | List teams / personas / modes / models | seconds | `panel_client.py discover` |
| **ask** | `answer` | Quick single-persona take | 1–2 min | `panel_client.py ask "$Q"` |
| **debate** | `discussion` | Back-and-forth deliberation + transcript | 10–15 min | `panel_client.py debate "$Q"` |
| **explore** | `panel` (two-stage) | Deep multi-perspective synthesis. `panel` mode is the most costly — every participant runs twice. Use only when depth matters. | 12–20 min | `panel_client.py explore "$Q"` |
| **review** | `parallel_with_main` | Each participant reads independently, main persona synthesizes. Right for "is this progress?" — especially with upstream-only participants. | 8–12 min | `panel_client.py review "$Q" [--participants upstream:...]` |
| **challenge** | adversarial (own endpoint) | Stress-test a held position. Structured verdict (holds_up / strongest_objection / would_change_mind_if). | 8–15 min | `panel_client.py challenge "$POSITION" [--evidence ...] [--decision-pending ...]` |

**`challenge` is the one to reach for mid-session** — by turn 40 the user usually has a plan, not a question. `challenge` attacks the plan and returns a structured verdict (`holds_up: bool`, `confidence: 0.0–1.0`, `strongest_objection`, `overlooked_factors`, `would_change_mind_if`) that you can branch on directly.

All commands are run from the repo root with `.venv/bin/python .claude/skills/panel/panel_client.py <intent> ...`.

## Agent rules (read before running anything)

- **One intent = one Bash call.** Map the user's request to exactly one row of the table above and run that single command. Do not chain subcommands, do not compose pipelines, do not invent flags that aren't shown.
- **If the CLI errors, relay the error verbatim.** Every intent that needs state (`ask` / `debate` / `explore` / `challenge`) prints a clear message telling the user to run `panel setup` first when `.claude/panel_state.json` is missing. Pass that through — do not try to bootstrap state yourself, do not hand-edit the JSON, do not guess values.
- **Never touch `.env` or `panel_state.json` directly.** Use `panel_client.py state set <key> <value>` / `state clear` if state genuinely needs changing. If `PANEL_API_KEY` is missing, ask the user to set it — do not read, write, or create `.env` files.
- **`setup` requires user confirmation before applying.** It prints a plan plus the exact shell commands to apply it. Show the plan, wait for an explicit yes, then run the commands.

After `setup` has been applied once, `ask` / `debate` / `explore` / `review` / `challenge` inherit team, main persona, project, and per-intent default participants from `.claude/panel_state.json` — so the minimal call shape becomes just `panel_client.py <intent> "$input"` with no flags.

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
- per-intent default participants. The setup advisor populates state keys named variously after intents or modes: `challenge_participants`, `panel_participants` (consumed by the `explore` intent, named after `panel` mode), `debate_participants`, `answer_persona` (consumed by `ask`, named after `answer` mode)

It prints the plan PLUS the exact `panel_client.py projects create ...` + `panel_client.py state set ...` commands needed to apply it. **Do not auto-apply** — show the user the plan and the commands, let them confirm, then execute via Bash.

If the advisor returns an `overview` saying the user has no teams, they need to contact support to get a team created — the user cannot create teams themselves. Relay that message.

After applying setup, every subsequent call inherits all the context it needs from state.

## Before the first real call

- **`PANEL_API_KEY`** must be set. The client finds it in any of: shell env, `<repo-root>/.env` (nearest ancestor of cwd with `.git` or `.claude`), or `.claude/skills/panel/.env`. First one found wins. Ask the user if it's missing — see the `.env` rule above.
- **Gitignore tip:** a bare `.env` entry (no slash, no prefix) in `.gitignore` matches `.env` at any depth, so one line covers both locations.
- **If the user wants a specific topic suggestion rather than a full setup**, use `help "$TOPIC"` instead of `setup` — `help` is topic-driven and suggests a specific mode + participants + reshaped prompt. `setup` is state-driven.
- **Inspection:** use the `discover` intent for teams/personas/modes. `panel_client.py state show` prints the current panel state. `panel_client.py state clear` starts fresh.

## How state gets consumed

Each intent reads a specific set of keys. **Key names are partly legacy** — some keys are named after the MODE they configure (e.g. `panel_participants` configures `panel` mode, used by `explore`), others after the intent itself.

| Intent | Reads from state | Key naming origin |
|---|---|---|
| `ask` | `team`, `answer_persona` (→ `main_persona`), `project` | after `answer` mode |
| `debate` | `team`, `main_persona`, `debate_participants` (→ `default_participants`), `project` | after intent |
| `explore` | `team`, `main_persona`, `panel_participants` (→ `default_participants`), `project` | **after `panel` mode** — not after the skill |
| `review` | `team`, `main_persona`, `review_participants` (→ `default_participants`), `project` | after intent |
| `challenge` | `team`, `main_persona`, `challenge_participants` (→ `default_participants`), `project` | after intent |

So `panel_participants` is *not* "participants for the panel skill" — it is "participants for `panel` mode," consumed by the `explore` intent.

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

## Common pitfalls

Three recurring issues worth catching before they bite.

### 1. Participants need branch prefixes

`--participants` values must be prefixed with the branch (`upstream:`, `downstream:`, `lateral:`):

```
--participants "upstream:scout,downstream:translator,lateral:tracker"
```

A bare name like `--participants "scout,translator"` is parsed as `{branch: "main", name: ...}` — and the server rejects it with `HTTP 400: Main persona 'scout' not found in team`, because it's checking the name against the team's main personas.

Same rule applies to state keys that hold participant lists: `challenge_participants`, `panel_participants`, `review_participants`, `debate_participants`. Each value is a comma-separated list of `<branch>:<name>`. Setting them via `state set`:

```
panel_client.py state set challenge_participants "upstream:a,upstream:b,lateral:c"
```

The single exception is `answer_persona` (consumed by `ask`) — that takes a bare main-persona name because it IS the main persona, not a side participant.

### 2. One job at a time per API key

The server enforces a single running job per caller. If you submit while another job is active (yours from another session, or a long-running call you didn't realize was still polling), you get:

```
HTTP 429: {"detail":{"message":"You already have a job running...","job_id":"<id>"}}
```

Poll the blocking job with `panel_client.py status --job-id <id>` until it finishes, then retry. Don't fan out parallel panel calls under the same key — queue them serially.

### 3. State and `.env` walkers stop at the first `.claude/` they find

Both walkers look for the nearest `.claude/` directory (for state) or the nearest dir with `.git` or `.claude` (for `.env`). The walk halts there — it does NOT keep climbing to look for `panel_state.json` or `.env` in a grandparent.

This means: if your working directory (or any ancestor on the way up) has a `.claude/` subdir that doesn't contain `panel_state.json`, state setup at a parent level is invisible. Run `setup` from the specific working directory whose `.claude/` should hold state; put `.env` alongside it.

Concrete example of the trap:

```
~/work/myrepo/.claude/panel_state.json      # setup was run here
~/work/myrepo/examples/hello/.claude/skills/panel/  # the example's vendored skill
```

Running a panel call from `examples/hello/` — the walker finds `examples/hello/.claude/` first and looks for `panel_state.json` there (doesn't exist), never reaching `myrepo/.claude/panel_state.json`. The fix is to run `setup` inside `examples/hello/` too, or `cp` the state file in.

## What the user asked

$ARGUMENTS
