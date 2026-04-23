#!/bin/bash
# run_scout.sh — autonomous loop wrapper for the panel harness scout.
#
# Walks the active goal's increments end-to-end. Each tick:
#   1. Ask the scout what's next  (`python harness/scout.py next`)
#   2. Dispatch on the reply:
#      - agent:<name>       → spawn `claude --agent <name>` and wait
#      - verdict:proceed    → `scout.py advance`   (bump to next increment)
#      - verdict:revise     → `scout.py retry`     (archive pass, restart planner)
#      - verdict:walled     → stop, notify operator
#      - verdict:unknown    → stop, notify operator
#      - no-goal            → stop, tell operator to create goal.md first
#      - done               → stop, celebrate
#
# Run synchronously. Each `claude --agent` call blocks until the agent writes
# its signal file and exits; the scout then re-reads state. Do NOT background
# the agent spawns — we race on signal files otherwise.
#
# Manual control:
#   touch harness/.scout-pause   — pause at the top of the next tick
#   rm    harness/.scout-pause   — resume
#
# Run from anywhere — this script cd's to its own directory then up one.

set -u
cd "$(dirname "$0")/.."   # → example-root/

HARNESS="$PWD/harness"
PAUSE="$HARNESS/.scout-pause"
SLEEP_SECONDS="${SLEEP_SECONDS:-10}"

# macOS ships python3 but not python. Pick whichever exists; allow override.
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then
  echo "error: neither python3 nor python found on PATH" >&2
  exit 1
fi

# Budget cap per agent spawn — prevents a runaway agent from blowing past costs.
# Claude Code 2.x no longer has --max-turns; --max-budget-usd is the replacement.
MAX_BUDGET_USD="${MAX_BUDGET_USD:-5.00}"

echo "panel-harness scout starting in $PWD"
echo "  python:              $PYTHON"
echo "  sleep between ticks: ${SLEEP_SECONDS}s"
echo "  max budget per agent: \$$MAX_BUDGET_USD"
echo "  to pause: touch $PAUSE"
echo

while true; do
  if [ -f "$PAUSE" ]; then
    echo "paused (remove $PAUSE to resume). checking again in ${SLEEP_SECONDS}s."
    sleep "$SLEEP_SECONDS"
    continue
  fi

  NEXT=$("$PYTHON" "$HARNESS/scout.py" next)
  echo "scout says: $NEXT"

  case "$NEXT" in
    agent:*)
      AGENT="${NEXT#agent:}"
      echo "→ spawning agent: $AGENT"
      # The agent's .md file (in .claude/agents/) already contains the full
      # contract — the prompt here just tells the top-level Claude session
      # to invoke that agent and wait for it to finish.
      # --print = headless / non-interactive (exit when model stops)
      # --agent = pin this session to the named sub-agent
      # --max-budget-usd = safety cap per spawn
      claude --print --agent "$AGENT" --max-budget-usd "$MAX_BUDGET_USD" \
        "Run the $AGENT agent per its contract. Write the required signal file for the current episode. Do not run any other agent. Stop when your signal file exists."
      ;;
    verdict:proceed)
      echo "→ advancing"
      "$PYTHON" "$HARNESS/scout.py" advance
      ;;
    verdict:revise)
      echo "→ retrying (archiving this pass)"
      "$PYTHON" "$HARNESS/scout.py" retry
      ;;
    verdict:walled)
      echo "scout verdict is walled — stopping. read the most recent review-signal.json and resolve manually."
      exit 0
      ;;
    verdict:unknown)
      echo "scout returned an unknown verdict — stopping."
      exit 1
      ;;
    no-goal-statement)
      echo "no goal.md — run the harness-setup-goal skill in Claude Code first (phase 1), then restart."
      exit 0
      ;;
    no-goal-plan)
      echo "goal.md present but goal.harness.json missing — run the harness-plan-goal skill in Claude Code (phase 2), then restart."
      exit 0
      ;;
    done)
      echo "goal complete. all increments advanced."
      exit 0
      ;;
    *)
      echo "unrecognized scout output: $NEXT — stopping."
      exit 1
      ;;
  esac

  echo "---sleeping ${SLEEP_SECONDS}s---"
  sleep "$SLEEP_SECONDS"
done
