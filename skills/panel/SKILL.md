---
name: panel
command: panel
description: Multi-persona analysis. Use when the user wants a persona-driven deep dive, second opinion, adversarial pressure on a held position, side-by-side perspectives, or a synthesized panel take.
argument-hint: [setup <context> | <question>]
---

# Companion Panel

## Operating Model

There are only two user-facing flows:

- `/panel setup <context>` bootstraps the working directory.
- `/panel <question>` sends the question to the panel after you classify it and choose CLI arguments.

Do not look for old command names. For real questions, use the unified client call:

```bash
python3 .claude/skills/panel/panel_client.py call --mode <mode> --participants "<refs>" --category "<category>" "<question>"
```

The only modes to choose from are:

- `answer`: one main persona gives a direct answer. Use for quick second opinions, focused judgment, or a single expert read.
- `parallel`: multiple personas answer independently. Use when the user wants side-by-side takes without a final synthesis.
- `parallel_with_main`: multiple personas contribute and the main persona synthesizes. Use for complex decisions, design critique, strategy, adversarial pressure, or anything that benefits from integrated judgment.

## Setup

If `.claude/panel_state.json` is missing, run setup before any real panel question. Setup calls the setup advisor, calls discover, fetches persona short descriptions, and writes a rich state file containing:

- `team` and `main_persona`.
- `project` when panel memory is enabled.
- `discover`, the raw discover payload plus persona shorts.
- `teams`, a normalized roster by team with persona refs, branches, IDs returned by the API, and short descriptions.
- `recommended_participants` for `answer`, `parallel`, and `parallel_with_main`.
- `history` and `category_participants`, updated by `call --category`.

Setup may recommend a project so panel memory can accumulate. Ask the user for confirmation before creating it:

```bash
python3 .claude/skills/panel/panel_client.py setup --create-project "<context>"
```

If the user does not want memory:

```bash
python3 .claude/skills/panel/panel_client.py setup --no-project "<context>"
```

If state already has `project`, keep using it. When a project is present, pass `--memory basic` on panel calls. If there is no project, do not pass `--memory`.

## Handling A Question

For any `/panel <question>` that is not `setup`:

1. Read state:

```bash
python3 .claude/skills/panel/panel_client.py state show --json
```

2. Classify the question into `answer`, `parallel`, or `parallel_with_main`.

3. Create a short reusable category key such as `architecture-review`, `debugging`, `strategy`, `copy-critique`, or `decision-pressure`.

4. Choose participants:

- First check `category_participants[category]` for a similar prior task.
- Otherwise use `recommended_participants[mode]`.
- For `parallel` or `parallel_with_main`, inspect `teams[team].personas` if you need a more tailored mix.
- Use refs exactly as `branch:name`, for example `main:alex`, `upstream:systems_reviewer`, `lateral:outside_operator`.

5. Run one `call`.

Examples:

```bash
python3 .claude/skills/panel/panel_client.py call --mode answer --participants "main:alex" --category "quick-judgment" "Is this API shape too complex?"
```

```bash
python3 .claude/skills/panel/panel_client.py call --mode parallel --participants "upstream:reviewer,lateral:operator,downstream:translator" --category "side-by-side-critique" "Give independent reads on this launch plan."
```

```bash
python3 .claude/skills/panel/panel_client.py call --mode parallel_with_main --participants "upstream:reviewer,lateral:operator,downstream:translator" --category "architecture-review" --memory basic "Stress-test this rewrite plan and synthesize the best path."
```

Use `--search` only when the question materially depends on current or external facts: current events, recent releases, live prices, specific URLs/docs, product availability, rankings, or facts likely to have changed. Do not use search for self-contained reasoning, design critique, introspection, or code architecture unless the user asks for current external context.

## Result Handling

The client renders results in a human-readable form. Pass through the result directly or summarize according to the user’s request.

Long `parallel` and `parallel_with_main` calls can take several minutes. Let the client poll normally unless you explicitly need to submit and return with `--no-poll`, then use:

```bash
python3 .claude/skills/panel/panel_client.py status --job-id <id>
```

## Rules

- Use exactly one `call` per user question.
- Do not hand-edit `.claude/panel_state.json`; use `setup`, `state show`, and `call --category`.
- If `PANEL_API_KEY` is missing, ask the user to set it. Do not read, write, or create `.env`.
- If the API returns `HTTP 429` with a running job ID, poll that job with `status --job-id <id>` before submitting another panel call.
- Participants for non-main branches must include branch prefixes. A bare name is treated as a main persona.

## What The User Asked

$ARGUMENTS
