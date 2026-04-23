#!/usr/bin/env python3
"""scout.py — goal-aware episodic orchestrator for the panel harness example.

Walks the increments of an active **goal**, one increment at a time. Each
increment gets one or more episodes; within an episode, four phases run in
order, each ending with a ``<phase>-signal.json`` file.

Concept map:

    goal.md                  — prose. Human reads this. Agents read the
                               ``section`` of it that the active increment
                               points at.
    goal.harness.json        — machine list of increments + their current
                               ``state`` (pending / in_progress / advanced /
                               walled). Scout reads and updates this.
    harness/config.json      — { active_plan, current_episode }.
    episodes/episode-N/      — one episode dir.
      increment.json         — snapshot of WHICH increment this episode is
                               attacking. Written by scout on bootstrap.
      plan-signal.json       ← planner finished
      work-signal.json       ← worker finished + artifact written alongside
      forensics-signal.json  ← forensics finished
      review-signal.json     ← upstream-review finished. Carries ``verdict``.
      pass-K/                — archived prior attempts (on retry).

Signal verdicts (on ``review-signal.json``, written by upstream-review):

    proceed  → scout marks increment ``advanced``, bumps ``current_episode``,
               bootstraps the next pending increment whose deps are all
               advanced.
    revise   → scout archives this pass's signals to ``pass-K/``, planner
               re-runs in the same episode. Increment state stays
               ``in_progress``.
    walled   → scout stops. Operator reads the review and decides manually.

Usage:

    python harness/scout.py              status + next-action hint
                                         (auto-bootstraps the current
                                         episode's increment.json if missing)
    python harness/scout.py advance      after verdict=proceed: mark increment
                                         advanced, bootstrap next increment
    python harness/scout.py retry        after verdict=revise: archive signals
                                         → pass-K/, planner restarts in same
                                         episode
    python harness/scout.py goal         print the goal's increment ledger
    python harness/scout.py next         single machine-readable line for run_scout.sh:
                                           agent:<name> | verdict:<value> | done | no-goal

One invocation = one tick of information. The scout does not spawn agents —
the operator invokes them from Claude Code between ticks.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parent
CONFIG = HARNESS / "config.json"
EPISODES = HARNESS / "episodes"
GOAL_MD = ROOT / "goal.md"

PHASES: list[tuple[str, str, str]] = [
    ("frame-signal.json",     "episode-framer",  "reads plan section + increment → frame.md + signal"),
    ("work-signal.json",      "worker",          "reads frame.md → artifact + signal"),
    ("forensics-signal.json", "forensics",       "reads frame + artifact → forensics.md + signal"),
    ("review-signal.json",    "upstream-review", "runs panel `review` on local + goal alignment → review.md + signal"),
]


# ── io helpers ──────────────────────────────────────────────────────────────


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")


def plan_path(cfg: dict) -> Path | None:
    """Path to the active plan's .harness.json, or None if no plan is set yet."""
    active = cfg.get("active_plan")
    return (ROOT / active) if active else None


def plan_md_path(cfg: dict) -> Path | None:
    """Path to the active plan's prose .md file (derived from active_plan)."""
    p = plan_path(cfg)
    return p.with_name(p.name.replace(".harness.json", ".md")) if p else None


def load_plan(cfg: dict) -> dict:
    p = plan_path(cfg)
    if p is None:
        raise ValueError("no active plan set in config.json (active_plan is null)")
    return json.loads(p.read_text())


def save_plan(cfg: dict, plan: dict) -> None:
    p = plan_path(cfg)
    if p is None:
        raise ValueError("no active plan set in config.json (active_plan is null)")
    p.write_text(json.dumps(plan, indent=2) + "\n")


# Kept for backward compatibility with any external caller — prefer plan_* names.
goal_path = plan_path
load_goal = load_plan
save_goal = save_plan


def episode_dir(cfg: dict) -> Path:
    return EPISODES / f"episode-{cfg['current_episode']}"


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# ── goal / increment helpers ────────────────────────────────────────────────


def find_increment(goal: dict, inc_id: str) -> dict | None:
    for inc in goal["increments"]:
        if inc["id"] == inc_id:
            return inc
    return None


def next_pending_increment(goal: dict) -> dict | None:
    """First increment whose state is 'pending' and all deps are 'advanced'."""
    by_id = {inc["id"]: inc for inc in goal["increments"]}
    for inc in goal["increments"]:
        if inc["state"] != "pending":
            continue
        if all(by_id[d]["state"] == "advanced" for d in inc.get("depends_on", [])):
            return inc
    return None


def episode_increment(edir: Path) -> dict | None:
    p = edir / "increment.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def bootstrap_episode(cfg: dict, goal: dict, inc: dict) -> Path:
    """Create episode dir for `inc`, write increment.json snapshot, mark state."""
    edir = episode_dir(cfg)
    edir.mkdir(parents=True, exist_ok=True)
    (edir / "increment.json").write_text(json.dumps(inc, indent=2) + "\n")

    if inc["state"] == "pending":
        inc["state"] = "in_progress"
    if inc.get("first_episode") is None:
        inc["first_episode"] = cfg["current_episode"]
    inc["last_episode"] = cfg["current_episode"]

    # Persist the state change on the live increment entry in goal.
    live = find_increment(goal, inc["id"])
    if live is not None:
        live.update(inc)
    save_goal(cfg, goal)
    return edir


def next_phase(edir: Path) -> tuple[str, str, str] | None:
    for signal, agent, summary in PHASES:
        if not (edir / signal).is_file():
            return signal, agent, summary
    return None


def pass_number(edir: Path) -> int:
    n = 1
    while (edir / f"pass-{n}").is_dir():
        n += 1
    return n


# ── commands ────────────────────────────────────────────────────────────────


def cmd_status() -> None:
    cfg = load_config()
    if not GOAL_MD.is_file():
        print("phase 1 — no goal.md yet.")
        print("→ run the harness-setup-goal skill (single main persona, `ask` intent)")
        return
    p = plan_path(cfg)
    if p is None:
        print("phase 2 — goal.md present, but config.active_plan is null.")
        print("→ run the harness-plan-goal skill (`review` intent, upstream participants, parallel_with_main mode)")
        return
    if not p.is_file():
        print(f"phase 2 — config.active_plan is {cfg['active_plan']!r} but file not found.")
        print("→ run the harness-plan-goal skill, or fix the path in harness/config.json")
        return

    goal = load_plan(cfg)  # kept variable name; file is now goal-plan-N.harness.json
    edir = episode_dir(cfg)

    # Auto-bootstrap: if the current episode has no increment.json yet,
    # pick the next pending increment and create it.
    inc = episode_increment(edir)
    if inc is None:
        pending = next_pending_increment(goal)
        if pending is None:
            print(f"active plan: {cfg['active_plan']}")
            print("no pending increments. goal is complete (or walled — run `goal` to see).")
            return
        edir = bootstrap_episode(cfg, goal, pending)
        inc = episode_increment(edir)
        print(f"bootstrapped {rel(edir)} for increment {inc['id']} — {inc['name']}")
        print()

    prior_passes = pass_number(edir) - 1

    plan_md = plan_md_path(cfg)
    plan_md_rel = plan_md.name if plan_md else "—"
    print(f"active plan:      {cfg['active_plan']}")
    print(f"  goal prose:     goal.md")
    print(f"  plan prose:     {plan_md_rel}")
    print(f"current episode:  {cfg['current_episode']}  ({rel(edir)})")
    print(f"increment:        {inc['id']} — {inc['name']}  (state: {inc['state']})")
    print(f"  scope:          {inc['scope']}")
    print(f"  plan section:   {plan_md_rel} → {inc['section']}")
    print(f"  artifact name:  {inc['artifact_name']}")
    if prior_passes:
        print(f"prior passes:     {prior_passes}  (archived under pass-*/)")
    print()
    for signal, agent, summary in PHASES:
        mark = "✓" if (edir / signal).is_file() else " "
        print(f"  [{mark}] {agent:<16s}  {summary}")
    print()

    nxt = next_phase(edir)
    if nxt is None:
        review = json.loads((edir / "review-signal.json").read_text())
        verdict = review.get("verdict", "?")
        print(f"review verdict:   {verdict}  (confidence={review.get('confidence', '?')})")
        if review.get("strongest_objection"):
            print(f"strongest objection: {review['strongest_objection']}")
        print()
        if verdict == "proceed":
            print("→ run:  python harness/scout.py advance")
        elif verdict == "revise":
            print("→ run:  python harness/scout.py retry")
        elif verdict == "walled":
            print("→ walled. read review-signal.json; fix the goal or the increment, then `retry` or edit manually.")
        else:
            print("→ unknown verdict. read review-signal.json.")
        return

    _, agent, _ = nxt
    print(f"next agent:       {agent}")
    print()
    print(f"in Claude Code in this directory, ask:  run the {agent} agent")


def cmd_advance() -> None:
    cfg = load_config()
    goal = load_goal(cfg)
    edir = episode_dir(cfg)
    inc = episode_increment(edir)
    if inc is None:
        sys.exit("refusing to advance: current episode has no increment.json")

    review_path = edir / "review-signal.json"
    if not review_path.is_file():
        sys.exit("refusing to advance: review-signal.json missing")

    review = json.loads(review_path.read_text())
    if review.get("verdict") != "proceed":
        sys.exit(f"refusing to advance: verdict is {review.get('verdict')!r}, not 'proceed'")

    # Mark this increment advanced.
    live = find_increment(goal, inc["id"])
    if live is None:
        sys.exit(f"increment {inc['id']!r} not found in active plan")
    live["state"] = "advanced"
    live["last_episode"] = cfg["current_episode"]

    # Find next pending increment.
    pending = next_pending_increment(goal)
    if pending is None:
        save_goal(cfg, goal)
        remaining_walled = [i["id"] for i in goal["increments"] if i["state"] == "walled"]
        if remaining_walled:
            print(f"advanced {inc['id']}. no further pending increments, but walled: {remaining_walled}.")
        else:
            print(f"advanced {inc['id']}. all increments advanced — goal complete.")
        return

    # Bootstrap next episode for the next pending increment.
    cfg["current_episode"] += 1
    save_config(cfg)
    bootstrap_episode(cfg, goal, pending)
    print(f"advanced {inc['id']}. → episode-{cfg['current_episode']} for increment {pending['id']} ({pending['name']}).")
    print("run:  python harness/scout.py")


def cmd_retry() -> None:
    cfg = load_config()
    edir = episode_dir(cfg)
    if not (edir / "increment.json").is_file():
        sys.exit("refusing to retry: current episode has no increment.json")
    n = pass_number(edir)
    pass_dir = edir / f"pass-{n}"
    pass_dir.mkdir()

    # Move everything in the episode dir EXCEPT `increment.json` (the persistent
    # scout snapshot of which increment this episode targets) and existing
    # pass-K/ subdirs. One sweep captures signal JSONs, per-phase .md reports,
    # and the worker's artifact.
    moved = []
    for entry in edir.iterdir():
        if entry.name == "increment.json":
            continue
        if entry.is_dir() and entry.name.startswith("pass-"):
            continue
        shutil.move(str(entry), str(pass_dir / entry.name))
        moved.append(entry.name)

    print(f"archived pass {n} → {rel(pass_dir)}  ({len(moved)} files)")
    print("next agent: episode-framer  (prior pass available for context under pass-*/)")


def cmd_next() -> None:
    """Print a single machine-readable line for run_scout.sh to parse.

    One of:
        no-goal-statement    — goal.md missing (run harness-setup-goal)
        no-goal-plan         — goal.md present but goal.harness.json missing
                                (run harness-plan-goal)
        agent:<name>         — next phase needs <name>
        verdict:proceed      — all signals present, ready to advance
        verdict:revise       — all signals present, ready to retry
        verdict:walled       — stop; operator action needed
        verdict:unknown      — review-signal.json has an unrecognized verdict
        done                 — goal complete (no more pending increments)
    """
    cfg = load_config()
    if not GOAL_MD.is_file():
        print("no-goal-statement")
        return
    p = plan_path(cfg)
    if p is None or not p.is_file():
        print("no-goal-plan")
        return

    goal = load_goal(cfg)
    edir = episode_dir(cfg)

    # Auto-bootstrap the increment.json if missing (same behavior as cmd_status).
    inc = episode_increment(edir)
    if inc is None:
        pending = next_pending_increment(goal)
        if pending is None:
            print("done")
            return
        bootstrap_episode(cfg, goal, pending)

    nxt = next_phase(edir)
    if nxt is None:
        review_path = edir / "review-signal.json"
        try:
            review = json.loads(review_path.read_text())
            verdict = review.get("verdict", "unknown")
        except (OSError, json.JSONDecodeError):
            verdict = "unknown"
        print(f"verdict:{verdict}")
        return

    _, agent, _ = nxt
    print(f"agent:{agent}")


def cmd_goal() -> None:
    cfg = load_config()
    goal = load_goal(cfg)
    plan_md = plan_md_path(cfg)
    print(f"active plan:  {cfg['active_plan']}  (prose: {plan_md.name if plan_md else '—'}; goal: goal.md)")
    print()
    print(f"{'id':<4}{'state':<14}{'name':<28}{'deps':<12}{'episodes'}")
    for inc in goal["increments"]:
        deps = ",".join(inc.get("depends_on", [])) or "—"
        first = inc.get("first_episode")
        last = inc.get("last_episode")
        eps = f"{first}..{last}" if first is not None else "—"
        print(f"{inc['id']:<4}{inc['state']:<14}{inc['name']:<28}{deps:<12}{eps}")


# ── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        {
            "status":  cmd_status,
            "advance": cmd_advance,
            "retry":   cmd_retry,
            "goal":    cmd_goal,
            "next":    cmd_next,
        }[cmd]()
    except KeyError:
        sys.exit(f"unknown command: {cmd!r}. known: status, advance, retry, goal, next.")


if __name__ == "__main__":
    main()
