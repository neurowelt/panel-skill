---
name: panel
command: panel
description: Multi-persona analysis. Use when the user wants a persona-driven deep dive, second opinion, adversarial pressure on a held position, side-by-side perspectives, or a synthesized panel take.
argument-hint: [setup <context> | <question>]
---

# Companion Panel

## Decision Rules

Panel is not for ordinary fact lookup or quick answers the model can handle directly.
Use it when the answer should be shaped by the user's own self-models, or when a
multi-vantage read will expose useful tension.

Before choosing a mode or persona, spend 1-2 sentences modeling who the user is
and why they are asking. The question alone rarely picks the right call; the
workflow shape does.

The main persona is a model of the user, built from a long interview. Treat panel
outputs as privileged context about the user, not as generic expert answers.

`answer` is the default. Most questions go here. Pick the responder by workflow
shape:

- User's regular work, preferences, taste, judgment, or self-model: use the main
  persona.
- Explanation, simplification, or making something legible: use an assistant
  persona when available.
- Depth, mechanism, structural read, or domain decomposition: use upstream
  personas. Read persona shorts when available to pick the best match.
- Adversarial pressure, blind spots, second-order effects, or outside-view
  critique: use lateral personas.
- Forward motion on something already mostly decided in the user's head: use a
  downstream persona matching the action shape.

If two branches plausibly fit, ask the user and explain what each would give.

Use `parallel_with_main` when multiple inputs should be synthesized into one
integrated take. It fits first contact with a complex topic, strategy, design,
planning, or high-stakes critique. The participants list contains both the input
personas and the synthesizer; the synthesizer is normally `main:<name>` or an
assistant persona.

Use `parallel` only when the user explicitly wants unintegrated side-by-side
views.

Skip `parallel_with_main` for single-voice rendering tasks such as character
sheets, copy, persona portraits, or any artifact where one coherent voice matters
more than synthesis; use `answer` instead.

Long `parallel` and `parallel_with_main` calls can take 8-15 minutes. The client
prints polling stage events such as `stage: answer: generating response`; pass
those through as live progress. If an answer drifts into philosophy or ethics
unprompted, or feels off-topic, treat that as ambiguity drift: re-prompt with
more context instead of presenting it as a clean result.

## Operating Model

There are two user-facing flows:

- `/panel setup <context>` bootstraps the working directory.
- `/panel <question>` sends the question to the panel after you classify it and
  choose CLI arguments.

For real questions, use one unified client call:

```bash
python3 .claude/skills/panel/panel_client.py call --mode <mode> --participants "<refs>" --category "<category>" "<question>"
```

The available modes are:

- `answer`: one persona gives a direct answer.
- `parallel`: multiple personas answer independently.
- `parallel_with_main`: multiple personas contribute and a main or assistant
  persona synthesizes.

## Setup

If `.claude/panel_state.json` is missing, do not force setup. For a simple
question, run a bare `answer` call without `--team`, `--main`, or
`--participants`; the client will perform lightweight discovery, choose the first
available main persona as the only participant, and write minimal no-project
state. This uses discover only and does not call the setup advisor LLM endpoint.

Full setup calls the setup advisor, calls discover, fetches persona short
descriptions when available, and writes richer state containing:

- `team` and `main_persona`.
- `project` when panel memory is enabled.
- `discover`, the raw discover payload plus persona shorts.
- `teams`, a normalized roster by team with persona refs, branches, IDs returned
  by the API, and short descriptions where available.
- `recommended_participants` for `answer`, `parallel`, and
  `parallel_with_main`.
- `history` and `category_participants`, updated by `call --category`.

If `PANEL_API_KEY` is missing, ask the user to set it. Generate it at
`<PANEL_BASE_URL>/profile -> API Access`; the default base URL is
`https://panel.humx.ai`. Do not read, write, or create `.env`.

Setup may recommend a project so panel memory can accumulate. Ask the user for
confirmation before creating it:

```bash
python3 .claude/skills/panel/panel_client.py setup --create-project "<context>"
```

If the user does not want memory:

```bash
python3 .claude/skills/panel/panel_client.py setup --no-project "<context>"
```

If state already has `project`, keep using it. When a project is present, pass
`--memory basic` on panel calls. If there is no project, do not pass `--memory`.

## Handling A Question

For any `/panel <question>` that is not `setup`:

1. Read state:

```bash
python3 .claude/skills/panel/panel_client.py state show --json
```

2. If state is missing and the request is a simple `answer`, run without setup:
   do not pass `--memory`, `--project`, `--team`, `--main`, or `--participants`.
   The client will call discover, pick the first main persona, and save minimal
   state. For `parallel` or `parallel_with_main`, ask whether to run full setup
   first.

3. Decide whether Panel is useful. Skip it for fact lookup, single-line answers,
   or work the model can do directly without persona depth.

4. Classify the question into `answer`, `parallel`, or `parallel_with_main` using
   the decision rules above.

5. Choose a short reusable category key. Prefer stable keys over one-off labels
   so `category_participants` can learn across calls.

6. Choose participants:

- First check `category_participants[category]` for a similar prior task.
- Otherwise use `recommended_participants[mode]`.
- For `parallel` or `parallel_with_main`, inspect `teams[team].personas` if you
  need a more tailored mix.
- Use refs exactly as `branch:name`, for example `main:alex`,
  `upstream:systems_reviewer`, `lateral:outside_operator`.
- For a no-state simple `answer`, omit participants; the client will discover
  the first available main persona and use `main:<name>`.

7. Run exactly one `call`.

Examples:

No-state simple answer:

```bash
python3 .claude/skills/panel/panel_client.py call --mode answer --category "quick-answer" "What is your read on this?"
```

```bash
python3 .claude/skills/panel/panel_client.py call --mode answer --participants "main:alex" --category "quick-judgment" "Is this API shape too complex?"
```

```bash
python3 .claude/skills/panel/panel_client.py call --mode parallel --participants "upstream:reviewer,lateral:operator,downstream:translator" --category "side-by-side-critique" "Give independent reads on this launch plan."
```

```bash
python3 .claude/skills/panel/panel_client.py call --mode parallel_with_main --participants "upstream:reviewer,lateral:operator,main:alex" --category "architecture-review" --memory basic "Stress-test this rewrite plan and synthesize the best path."
```

## Result Handling

The client renders results in a human-readable form. Pass through the result
directly or summarize according to the user's request.

Long `parallel` and `parallel_with_main` calls can take several minutes. Let the
client poll normally unless you explicitly need to submit and return with
`--no-poll`, then use:

```bash
python3 .claude/skills/panel/panel_client.py status --job-id <id>
```

## Knobs

| Flag | When to use |
|---|---|
| `--search` | Only when the question needs current or external facts, or the user asks for search. |
| `--memory basic` | Use when state has a project. Do not pass memory if there is no project. |
| `--no-poll` | Automation/dev use only; normally let the client poll and pass stage updates through. |

## Rules

- Use exactly one `call` per user question.
- Do not hand-edit `.claude/panel_state.json`; use `setup`, `state show`, and
  `call --category`.
- If the API returns `HTTP 429` with a running job ID, poll that job with
  `status --job-id <id>` before submitting another panel call.
- Participants for non-main branches must include branch prefixes. A bare name is
  treated as a main persona.

## What The User Asked

$ARGUMENTS
