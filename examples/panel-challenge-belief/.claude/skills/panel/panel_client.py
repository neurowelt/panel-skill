"""Companion Panel — public API v1 CLI.

Zero-dependency command-line client for the ``/api/v1/*`` surface.

Subcommands
-----------
    setup [HINT]              Onboarding advisor — proposes team / project / defaults
    help [TOPIC]              Stream advice for a topic (mode / participants / prompt)
    discover                  List teams, modes, models, and short persona guides
    ask TOPIC                 Single-persona answer
    debate TOPIC              2-4 personas in discussion with transcript
    explore TOPIC             Two-stage panel with synthesis
    review TOPIC              Parallel upstream reads + main synthesis (progress/alignment)
    challenge POSITION        Adversarial verdict on a held position
    balance                   Print wallet balance
    projects list | create    Project management
    state show | set | clear  Inspect/manage the working-directory state file
    status --job-id ID        Fetch status/result of a previously submitted job

Environment
-----------
    PANEL_API_KEY   Required. Generate at Profile -> API Access.
    PANEL_BASE_URL  Optional. Defaults to https://panel.humx.ai.

A ``.env`` is loaded automatically from the first of these locations
that exists (earlier wins; shell env always wins over all files):

    1. next to this script
    2. nearest repo root (first ancestor of CWD with ``.git`` or ``.claude``)
    3. ``~/.claude/skills/panel/.env``  (user-global; useful when the skill
       is installed globally via the marketplace and you don't want to
       edit files inside the plugin install dir)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


# ── Configuration ───────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://panel.humx.ai"
DEFAULT_POLL_INTERVAL = 30.0
DEFAULT_POLL_TIMEOUT = 1200.0
DEFAULT_POLL_MAX_CONSECUTIVE_FAILURES = 5
DEFAULT_LLM = "qwen/qwen3-max"

PANEL_STATE_FILENAME = "panel_state.json"
PANEL_STATE_DIRNAME = ".claude"


# ── .env loader ────────────────────────────────────────────────────────────


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` to find the nearest dir containing .git or .claude."""
    for p in [start, *start.parents]:
        if (p / ".git").exists() or (p / ".claude").exists():
            return p
    return None


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from candidate .env files into os.environ.

    Search order (first wins, shell env always wins via the not-in-environ guard):
      1. <script_dir>/.env          (explicit, per-skill)
      2. <repo_root>/.env           (repo root = nearest ancestor of cwd with .git/.claude)
      3. ~/.claude/skills/panel/.env (user-global; works when the skill is
                                     installed globally via the marketplace)
    """
    candidates: list[Path] = [Path(__file__).resolve().parent / ".env"]
    repo_root = _find_repo_root(Path.cwd().resolve())
    if repo_root is not None:
        root_env = repo_root / ".env"
        if root_env not in candidates:
            candidates.append(root_env)
    user_env = Path.home() / ".claude" / "skills" / "panel" / ".env"
    if user_env not in candidates:
        candidates.append(user_env)

    for env_path in candidates:
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


def _env_base_url() -> str:
    return os.environ.get("PANEL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _env_api_key() -> str:
    key = os.environ.get("PANEL_API_KEY", "")
    if not key:
        print(
            "error: PANEL_API_KEY is not set.\n"
            "Generate one at Profile -> API Access, then either:\n"
            "  - export PANEL_API_KEY in your shell, or\n"
            "  - put it in <repo-root>/.env, or\n"
            "  - put it in .env next to this script, or\n"
            "  - put it in ~/.claude/skills/panel/.env (user-global).",
            file=sys.stderr,
        )
        sys.exit(2)
    return key


# ── Panel state file ────────────────────────────────────────────────────────
#
# `.claude/panel_state.json` in CWD binds this directory to team + main
# persona + project + per-intent participants so every subsequent call
# inherits them. Written by `panel setup` / `projects create --set-active`,
# read by every intent subcommand.


def _find_panel_state_path() -> Path:
    """Walk up from CWD looking for an existing .claude/ directory."""
    cwd = Path.cwd().resolve()
    for parent in (cwd, *cwd.parents):
        candidate = parent / PANEL_STATE_DIRNAME
        if candidate.is_dir():
            return candidate / PANEL_STATE_FILENAME
    return cwd / PANEL_STATE_DIRNAME / PANEL_STATE_FILENAME


def _load_panel_state() -> dict:
    path = _find_panel_state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_panel_state(patch: dict) -> Path:
    path = _find_panel_state_path()
    current = _load_panel_state()
    for k, v in patch.items():
        if v is None:
            current.pop(k, None)
        else:
            current[k] = v
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _clear_panel_state() -> Path | None:
    path = _find_panel_state_path()
    if path.is_file():
        path.unlink()
        return path
    return None


def _state_fallback(args: argparse.Namespace, attr: str, state_key: str):
    """CLI arg wins; fall back to state file value; else None."""
    val = getattr(args, attr, None)
    if val is not None and val != "":
        return val
    return _load_panel_state().get(state_key)


# ── HTTP ────────────────────────────────────────────────────────────────────


class APIError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body}")


def _headers(api_key: str, idempotency_key: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {api_key}"}
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict | None = None,
    timeout: float = 15,
) -> dict:
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise APIError(e.code, body) from e


def _pretty(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── API endpoints ──────────────────────────────────────────────────────────


def api_discover(base_url: str, api_key: str) -> dict:
    return _request("GET", f"{base_url}/api/v1/discover", headers=_headers(api_key))


def api_get_forensics_short(base_url: str, api_key: str, persona: str) -> dict:
    path = f"/api/v1/forensics/{quote(persona, safe='')}?short=true"
    return _request("GET", f"{base_url}{path}", headers=_headers(api_key))


def api_balance(base_url: str, api_key: str) -> dict:
    return _request("GET", f"{base_url}/api/v1/balance", headers=_headers(api_key))


def api_list_projects(base_url: str, api_key: str) -> list[str]:
    data = _request("GET", f"{base_url}/api/v1/projects", headers=_headers(api_key))
    return data.get("projects", [])


def api_create_project(base_url: str, api_key: str, name: str) -> dict:
    try:
        return _request(
            "POST",
            f"{base_url}/api/v1/projects",
            headers=_headers(api_key),
            json_body={"name": name},
        )
    except APIError as e:
        if e.status_code == 409:
            return {"name": name, "created": False, "detail": "already exists"}
        raise


def _settings_dict(
    *, model=None, temperature=None, memory=None, use_search=None,
) -> dict:
    out: dict = {}
    if model is not None:
        out["model"] = model
    if temperature is not None:
        out["temperature"] = temperature
    if memory is not None:
        out["memory"] = memory
    if use_search is not None:
        out["use_search"] = use_search
    return out


def api_submit_turn(
    base_url: str,
    api_key: str,
    *,
    team: str | None,
    main_persona: str | None,
    participants: list[dict],
    mode: str,
    prompt: str,
    project: str | None,
    session_id: str | None,
    idempotency_key: str,
    **settings,
) -> dict:
    body: dict = {"participants": participants, "mode": mode, "prompt": prompt}
    if session_id is None:
        body["team"] = team
        body["main_persona"] = main_persona
    else:
        body["session_id"] = session_id
    if project:
        body["project"] = project
    s = _settings_dict(**settings)
    if s:
        body["settings"] = s
    return _request(
        "POST",
        f"{base_url}/api/v1/turn",
        headers=_headers(api_key, idempotency_key),
        json_body=body,
        timeout=30,
    )


def api_submit_challenge(
    base_url: str,
    api_key: str,
    *,
    position: str,
    evidence: list[str],
    decision_pending: str | None,
    team: str,
    main_persona: str,
    participants: list[dict],
    project: str | None,
    **settings,
) -> dict:
    body: dict = {
        "position": position,
        "evidence": evidence or [],
        "team": team,
        "main_persona": main_persona,
        "participants": participants,
    }
    if decision_pending:
        body["decision_pending"] = decision_pending
    if project:
        body["project"] = project
    s = _settings_dict(**settings)
    if s:
        body["settings"] = s
    return _request(
        "POST",
        f"{base_url}/api/v1/challenge",
        headers=_headers(api_key),
        json_body=body,
        timeout=30,
    )


def _stream_ndjson(
    base_url: str,
    api_key: str,
    path: str,
    payload: dict,
    final_key: str,
    *,
    on_token=None,
    timeout: float = 120,
) -> dict:
    """POST NDJSON-returning endpoint and collect tokens until final event."""
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url}{path}",
        data=body,
        headers={
            **_headers(api_key),
            "Content-Type": "application/json",
            "Accept": "application/x-ndjson",
        },
        method="POST",
    )
    try:
        resp = urlopen(req, timeout=timeout)
    except HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise APIError(e.code, err_body) from e

    final: dict | None = None
    with resp:
        for raw_line in resp:
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            kind = event.get("event")
            if kind == "token":
                text = event.get("text") or ""
                if on_token and text:
                    on_token(text)
            elif kind == "final":
                final = event.get(final_key) or {}
                break
            elif kind == "error":
                raise RuntimeError(event.get("message") or f"{path} error")

    if final is None:
        raise RuntimeError(f"{path} stream closed without a final event")
    return final


def api_stream_advise(base_url, api_key, *, topic, on_token=None) -> dict:
    return _stream_ndjson(
        base_url, api_key, "/api/v1/advise", {"topic": topic}, "advice",
        on_token=on_token,
    )


def api_stream_advise_setup(base_url, api_key, *, hint, on_token=None) -> dict:
    payload = {"hint": hint} if hint else {}
    return _stream_ndjson(
        base_url, api_key, "/api/v1/advise/setup", payload, "setup",
        on_token=on_token,
    )


def api_poll_job(
    base_url: str,
    api_key: str,
    job_id: str,
    *,
    interval: float,
    timeout: float,
    quiet: bool = False,
    max_consecutive_failures: int = DEFAULT_POLL_MAX_CONSECUTIVE_FAILURES,
) -> dict:
    """Poll /api/v1/jobs/{id} until done or error. Retries transient failures."""
    deadline = time.monotonic() + timeout
    last_stage: str | None = None
    consecutive_failures = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            data = _request(
                "GET",
                f"{base_url}/api/v1/jobs/{job_id}",
                headers=_headers(api_key),
            )
        except (APIError, URLError) as e:
            transient = isinstance(e, URLError) or (
                isinstance(e, APIError) and 500 <= e.status_code < 600
            )
            if not transient:
                raise
            consecutive_failures += 1
            last_error = e
            if consecutive_failures >= max_consecutive_failures:
                raise RuntimeError(
                    f"panel API returned repeated transient errors "
                    f"({consecutive_failures} in a row); last: {e}"
                ) from e
            if not quiet:
                print(
                    f"  (transient error {consecutive_failures}/"
                    f"{max_consecutive_failures}, retrying)"
                )
            time.sleep(interval)
            continue

        consecutive_failures = 0
        status = data.get("status")
        if status == "running":
            stage = data.get("stage") or ""
            if not quiet and stage and stage != last_stage:
                print(f"  stage: {stage}")
                last_stage = stage
            time.sleep(interval)
            continue
        return data
    msg = f"job {job_id} did not finish within {timeout:.0f}s"
    if last_error is not None:
        msg += f" (last transient error: {last_error})"
    raise TimeoutError(msg)


def _fetch_shorts(
    base_url: str, api_key: str, persona_names: list[str],
) -> dict[str, str]:
    """Fetch short forensics for personas in parallel, dropping missing."""
    def _one(name: str) -> tuple[str, str | None]:
        try:
            resp = api_get_forensics_short(base_url, api_key, name)
        except Exception:
            return (name, None)
        if resp.get("available") and resp.get("guide"):
            return (name, resp["guide"])
        return (name, None)

    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for f in as_completed(pool.submit(_one, n) for n in persona_names):
            name, content = f.result()
            if content:
                out[name] = content
    return out


# ── Rendering ───────────────────────────────────────────────────────────────


def _print_turn_result(data: dict) -> None:
    """Dispatch on payload.kind and render the turn result."""
    status = data.get("status")
    if status == "error":
        print(f"\nerror: {data.get('error', '')}", file=sys.stderr)
        return
    result = data.get("result") or {}
    mode = result.get("mode", "")
    payload = result.get("payload") or {}
    kind = payload.get("kind", "")

    print(f"\n── result (mode={mode}, kind={kind}) ──")

    if kind == "answer":
        print(f"\n[{payload.get('persona', '')}]")
        print(f"  {(payload.get('content') or '').strip()}")
        return

    if kind == "parallel":
        for c in payload.get("contributions", []):
            print(f"\n[{c.get('persona', '')}]")
            print(f"  {(c.get('content') or '').strip()}")
        return

    if kind == "synthesis":
        contributions = payload.get("contributions", [])
        if contributions:
            print("\n── contributions ──")
            for c in contributions:
                print(f"\n[{c.get('persona', '')}]")
                print(f"  {(c.get('content') or '').strip()}")
        print(f"\n── synthesis by {payload.get('synthesizer', '')} ──")
        print(f"  {(payload.get('synthesis') or '').strip()}")
        return

    if kind == "discussion":
        transcript = payload.get("transcript", [])
        if transcript:
            print("\n── transcript ──")
            for entry in transcript:
                print(f"\n  {entry.get('speaker', '')}:")
                print(f"    {(entry.get('text') or '').strip()}")
        print(f"\n── summary by {payload.get('summarizer', '')} ──")
        print(f"  {(payload.get('summary') or '').strip()}")
        return

    if kind == "challenge":
        _print_challenge_payload(payload)
        return

    print("\n(unknown payload kind — raw payload follows)")
    print(_pretty(payload))


def _print_challenge_payload(payload: dict) -> None:
    holds_up = bool(payload.get("holds_up", False))
    try:
        conf_str = f"{float(payload.get('confidence', 0.0)):.2f}"
    except (TypeError, ValueError):
        conf_str = str(payload.get("confidence", ""))
    verdict = "HOLDS UP" if holds_up else "DOES NOT HOLD UP"
    print(f"\nverdict:      {verdict}  (confidence: {conf_str})")
    objection = (payload.get("strongest_objection") or "").strip()
    if objection:
        print(f"\nstrongest objection:\n  {objection}")
    for label, key in (
        ("overlooked factors", "overlooked_factors"),
        ("would change mind if", "would_change_mind_if"),
    ):
        items = payload.get(key) or []
        if items:
            print(f"\n{label}:")
            for item in items:
                print(f"  - {item}")
    contributions = payload.get("contributions") or []
    if contributions:
        print("\n── per-persona objections ──")
        for c in contributions:
            print(f"\n[{c.get('persona', '')}]")
            print(f"  {(c.get('content') or '').strip()}")


def _format_range(source: dict, avg_key: str, fmt: str) -> str:
    """Render ``avg (range: lo-hi)`` from avg/min/max keys. ``fmt`` wraps values."""
    avg = source.get(avg_key)
    if avg is None:
        return "no data available"
    lo = source.get(f"{avg_key}_min")
    hi = source.get(f"{avg_key}_max")
    if lo is not None and hi is not None and (lo != avg or hi != avg):
        return f"{fmt.format(avg)} (range: {fmt.format(lo)}-{fmt.format(hi)})"
    return fmt.format(avg)


def _print_advice(advice: dict) -> None:
    print("\n── panel advice ──\n")
    print(f"suggested mode:          {advice.get('suggested_mode', '')}")
    parts = advice.get("suggested_participants") or []
    if parts:
        print(f"suggested participants:  {', '.join(parts)}")
    print(f"estimated time:          {_format_range(advice, 'estimated_minutes', '~{} min')}")
    print(f"estimated cost:          {_format_range(advice, 'estimated_cost_usd', '${} USD')}")
    if advice.get("use_search_suggested"):
        print(
            "web search:              recommended — pass --search on the "
            "follow-up ask/debate/explore/challenge call."
        )
    suggested_prompt = (advice.get("suggested_prompt") or "").strip()
    if suggested_prompt:
        print(f"\nreshaped prompt:\n  {suggested_prompt}")
    rationale = (advice.get("rationale") or "").strip()
    if rationale:
        print(f"\nwhy:\n  {rationale}")
    alternatives = advice.get("alternatives") or []
    if alternatives:
        print("\nalternatives:")
        for alt in alternatives:
            why = (alt.get("why") or "").strip()
            print(f"  - {alt.get('mode', '')}: {why}")
            t = _format_range(alt, "estimated_minutes", "~{} min")
            c = _format_range(alt, "estimated_cost_usd", "${} USD")
            print(f"      {t} / {c}")

    suggest = advice.get("suggest_project") or None
    if not suggest:
        return
    state = _load_panel_state()
    name = suggest.get("name", "")
    why = (suggest.get("rationale") or "").strip()
    if state.get("project"):
        print(
            f"\n(advisor proposed a project {name!r}, but this directory "
            f"is already bound to {state.get('project')!r} — ignoring)"
        )
        return
    print("\n── project suggestion ──")
    print(f"The advisor recommends creating a project: {name!r}")
    if why:
        print(f"  why: {why}")
    print(
        "\n  To create it and bind this directory, ask the user to confirm,\n"
        "  then run:\n"
        f"    panel_client.py projects create {name} --set-active"
    )
    print(
        "\n  Every subsequent panel/challenge call from this directory will\n"
        "  inherit the project and pick up accumulated memory."
    )


def _print_setup_guide(guide: dict) -> None:
    overview = (guide.get("overview") or "").strip()
    primary_team = (guide.get("primary_team") or "").strip()
    primary_main = (guide.get("primary_main_persona") or "").strip()
    suggest = guide.get("suggest_project") or None
    defaults = guide.get("default_participants") or {}

    print("\n── panel setup ──\n")
    if overview:
        print(overview)
        print()

    if not primary_team:
        print("(no apply commands — the advisor could not bootstrap state.)")
        return

    print(f"primary team:    {primary_team}")
    print(f"main persona:    {primary_main or '-'}")

    if suggest:
        name = (suggest.get("name") or "").strip()
        why = (suggest.get("rationale") or "").strip()
        if name:
            print(f"\nsuggested project:  {name}")
            if why:
                print(f"  why: {why}")

    intent_defaults = [
        ("challenge", defaults.get("challenge") or []),
        ("panel", defaults.get("panel") or []),
        ("debate", defaults.get("debate") or []),
    ]
    answer_p = (defaults.get("answer") or "").strip()

    print("\ndefault participants per intent:")
    for label, plist in intent_defaults:
        if plist:
            print(f"  {label:10} {', '.join(plist)}")
    if answer_p:
        print(f"  {'answer':10} {answer_p}")

    print("\n── to apply this setup ──\n")
    project_name = (suggest.get("name") if suggest else "") or ""
    if project_name:
        print(
            f"  panel_client.py projects create {project_name} "
            f"--set-active --team {primary_team} --main {primary_main}"
        )
    else:
        print(f"  panel_client.py state set team {primary_team}")
        print(f"  panel_client.py state set main_persona {primary_main}")
    for label, plist in intent_defaults:
        if plist:
            print(
                f"  panel_client.py state set {label}_participants "
                f"\"{','.join(plist)}\""
            )
    if answer_p:
        print(f"  panel_client.py state set answer_persona {answer_p}")


# ── Subcommand handlers ─────────────────────────────────────────────────────


def _parse_participant(raw: str) -> dict:
    """Parse ``branch:name`` or plain ``name`` into a participant dict."""
    if ":" in raw:
        branch, name = raw.split(":", 1)
        return {"name": name.strip(), "branch": branch.strip()}
    return {"name": raw.strip(), "branch": "main"}


def _parse_participants_csv(raw: str) -> list[dict]:
    return [_parse_participant(p) for p in raw.split(",") if p.strip()]


def _check_balance_or_fail(base_url: str, api_key: str, verb: str) -> int | None:
    """Return non-zero exit code if wallet is zero, else None."""
    try:
        balance = api_balance(base_url, api_key)
        if Decimal(balance.get("balance_usd", "0")) <= 0:
            print(
                f"error: wallet balance is {balance.get('balance_usd')} — "
                f"top up before submitting a {verb}.",
                file=sys.stderr,
            )
            return 3
    except APIError:
        raise
    except Exception:
        pass  # non-fatal — let the server decide
    return None


def cmd_discover(args: argparse.Namespace) -> int:
    data = api_discover(args.base_url, args.api_key)
    teams = data.get("teams", [])

    shorts: dict[str, str] = {}
    if not args.no_shorts:
        unique_names: list[str] = []
        seen: set[str] = set()
        for t in teams:
            for p in t.get("participants", []):
                name = p.get("name")
                if name and name not in seen:
                    seen.add(name)
                    unique_names.append(name)
        if unique_names:
            shorts = _fetch_shorts(args.base_url, args.api_key, unique_names)

    if args.json:
        if shorts:
            data = {**data, "shorts": shorts}
        print(_pretty(data))
        return 0

    print(f"teams ({len(teams)}):")
    for t in teams:
        print(f"  - {t.get('name')}")
        main_personas = t.get("main_personas", [])
        if main_personas:
            print(f"    main personas: {', '.join(main_personas)}")
        by_branch: dict[str, list[str]] = {}
        for p in t.get("participants", []):
            by_branch.setdefault(p["branch"], []).append(p["name"])
        for branch in ("upstream", "downstream", "lateral"):
            names = by_branch.get(branch, [])
            if names:
                print(f"    {branch}: {', '.join(names)}")
    modes = data.get("modes", [])
    print(f"\nmodes ({len(modes)}):")
    for m in modes:
        if isinstance(m, dict):
            print(f"  - {m['name']} ({m.get('participants', '')} participants)")
            print(f"    {m.get('description', '')}")
            print(f"    Best for: {m.get('best_for', '')}")
        else:
            print(f"  - {m}")
    print("\nmodels:")
    for m in data.get("models", []):
        print(f"  - {m}")
    projects = data.get("projects", [])
    if projects:
        print(f"\nprojects ({len(projects)}):")
        for p in projects:
            print(f"  - {p}")
    else:
        print("\nprojects: (none)")

    if not args.no_shorts:
        if shorts:
            print(f"\n{'=' * 60}")
            print(f"persona shorts ({len(shorts)}):")
            print(f"{'=' * 60}")
            for name in sorted(shorts):
                print(f"\n{shorts[name].rstrip()}")
        else:
            print("\npersona shorts: (none available — run short forensics to generate)")
    return 0


def cmd_balance(args: argparse.Namespace) -> int:
    data = api_balance(args.base_url, args.api_key)
    if args.json:
        print(_pretty(data))
        return 0
    print(f"{data.get('balance_usd')} {data.get('currency', 'USD')}")
    return 0


def cmd_projects_list(args: argparse.Namespace) -> int:
    projects = api_list_projects(args.base_url, args.api_key)
    if args.json:
        print(_pretty({"projects": projects}))
        return 0
    if not projects:
        print("(no projects)")
        return 0
    for name in projects:
        print(name)
    return 0


def cmd_projects_create(args: argparse.Namespace) -> int:
    data = api_create_project(args.base_url, args.api_key, args.name)
    if args.json:
        print(_pretty(data))
        return 0
    if data.get("created"):
        print(f"created project {args.name!r}")
    else:
        print(f"project {args.name!r} already exists (no change)")

    if args.set_active:
        patch: dict = {"project": args.name}
        if args.team:
            patch["team"] = args.team
        if args.main:
            patch["main_persona"] = args.main
        path = _save_panel_state(patch)
        print(f"  -> bound to {path} (active for this working directory)")
    return 0


def cmd_state_show(args: argparse.Namespace) -> int:
    state = _load_panel_state()
    path = _find_panel_state_path()
    if args.json:
        print(_pretty({"path": str(path), "state": state}))
        return 0
    if not state:
        print(f"no panel state at {path}")
        return 0
    print(f"panel state @ {path}:")
    for key, value in state.items():
        print(f"  {key}: {value}")
    return 0


def cmd_state_set(args: argparse.Namespace) -> int:
    _save_panel_state({args.key: args.value})
    print(f"set {args.key}={args.value!r}")
    return 0


def cmd_state_clear(args: argparse.Namespace) -> int:
    removed = _clear_panel_state()
    if removed is None:
        print("no panel state to clear")
    else:
        print(f"removed {removed}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        data = _request(
            "GET",
            f"{args.base_url}/api/v1/jobs/{args.job_id}",
            headers=_headers(args.api_key),
        )
    except APIError as e:
        print(f"HTTP {e.status_code}: {e.body}", file=sys.stderr)
        return 1

    if args.json:
        print(_pretty(data))
        return 0

    status = data.get("status", "unknown")
    job_id = data.get("job_id", args.job_id)
    session_id = data.get("session_id", "")

    if status == "running":
        stage = data.get("stage", "")
        print(f"job {job_id}: running" + (f" (stage: {stage})" if stage else ""))
        if session_id:
            print(f"session_id: {session_id}")
        return 0

    if status == "done":
        _print_turn_result(data)
        if session_id:
            print(f"\nsession_id: {session_id}")
        return 0

    print(f"job {job_id}: {status}", file=sys.stderr)
    error = data.get("error", "")
    if error:
        print(f"  {error}", file=sys.stderr)
    return 1


# ── Intent dispatcher (ask / debate / explore) ─────────────────────────────


def _intent_participants(
    args: argparse.Namespace, state: dict, intent_key: str,
) -> str | None:
    """Precedence: CLI --participants > {intent}_participants > default_participants."""
    cli = getattr(args, "participants", None)
    if cli:
        return cli
    return state.get(f"{intent_key}_participants") or state.get("default_participants")


def _run_intent(args: argparse.Namespace, *, mode: str, state_key: str) -> int:
    """Shared handler for ask / debate / explore intents.

    Resolves team / main / participants / project from CLI args with state
    fallback, then submits a turn and polls. Single-persona ``ask`` uses
    its own resolution path (below) before falling through here.
    """
    state = _load_panel_state()
    team = _state_fallback(args, "team", "team")
    main = _state_fallback(args, "main", "main_persona")
    participants_raw = _intent_participants(args, state, state_key)
    project = _state_fallback(args, "project", "project")

    if not team or not main or not participants_raw:
        print(
            f"error: {mode} needs --team, --main, and --participants. "
            "Run `panel_client.py setup` first to bootstrap state, or pass "
            "them explicitly.",
            file=sys.stderr,
        )
        return 2

    participants = _parse_participants_csv(participants_raw)
    if not participants:
        print("error: --participants must be a non-empty comma-separated list.", file=sys.stderr)
        return 2

    return _submit_turn_and_render(
        args, team=team, main=main, participants=participants, mode=mode,
        prompt=args.topic, project=project,
    )


def cmd_ask(args: argparse.Namespace) -> int:
    """Single-persona answer. Special-cased because the 'persona' doubles
    as both main persona and the sole participant."""
    state = _load_panel_state()
    team = _state_fallback(args, "team", "team")
    persona = (
        getattr(args, "persona", None)
        or state.get("answer_persona")
        or state.get("main_persona")
    )
    project = _state_fallback(args, "project", "project")

    if not team or not persona:
        print(
            "error: --team and --persona are required. "
            "Run `panel_client.py setup` first to bootstrap state, "
            "or pass them explicitly.",
            file=sys.stderr,
        )
        return 2

    return _submit_turn_and_render(
        args, team=team, main=persona,
        participants=[{"name": persona, "branch": "main"}],
        mode="answer", prompt=args.topic, project=project,
    )


def cmd_debate(args: argparse.Namespace) -> int:
    return _run_intent(args, mode="discussion", state_key="debate")


def cmd_explore(args: argparse.Namespace) -> int:
    return _run_intent(args, mode="panel", state_key="panel")


def cmd_review(args: argparse.Namespace) -> int:
    """Progress-and-alignment review — upstream personas each give an independent
    read, main persona synthesizes (parallel_with_main mode).

    Differs from `challenge` (adversarial attack on a position): `review` asks
    "does this feel like progress to someone modeling the user?" Use it for
    goal-alignment checks where the attack is not the right question.
    """
    return _run_intent(args, mode="parallel_with_main", state_key="review")


def _submit_turn_and_render(
    args: argparse.Namespace,
    *,
    team: str | None,
    main: str | None,
    participants: list[dict],
    mode: str,
    prompt: str,
    project: str | None,
) -> int:
    code = _check_balance_or_fail(args.base_url, args.api_key, "turn")
    if code is not None:
        return code

    idem_key = str(uuid.uuid4())
    if not args.quiet:
        print(f"submitting {mode} (idempotency_key={idem_key})")

    response = api_submit_turn(
        args.base_url,
        args.api_key,
        team=team,
        main_persona=main,
        participants=participants,
        mode=mode,
        prompt=prompt,
        project=project,
        session_id=None,
        idempotency_key=idem_key,
        model=getattr(args, "model", None) or DEFAULT_LLM,
        temperature=getattr(args, "temperature", None),
        memory=getattr(args, "memory", None),
        use_search=getattr(args, "use_search", None),
    )
    job_id = response["job_id"]
    session_id = response["session_id"]

    if not args.quiet:
        print(f"  job_id:     {job_id}")
        print(f"  session_id: {session_id}")
        print()

    if args.no_poll:
        if args.json:
            print(_pretty(response))
        return 0

    if not args.quiet:
        print("polling for result...")
    final = api_poll_job(
        args.base_url,
        args.api_key,
        job_id,
        interval=args.poll_interval,
        timeout=args.timeout,
        quiet=args.quiet,
    )

    if args.json:
        print(_pretty(final))
    else:
        _print_turn_result(final)
        print(f"\nsession_id: {session_id}")
    return 0 if final.get("status") == "done" else 1


def cmd_challenge(args: argparse.Namespace) -> int:
    """Adversarial panel on a position the caller holds."""
    state = _load_panel_state()
    team = _state_fallback(args, "team", "team")
    main = _state_fallback(args, "main", "main_persona")
    participants_raw = _intent_participants(args, state, "challenge")
    project = _state_fallback(args, "project", "project")

    if not team or not main or not participants_raw:
        print(
            "error: challenge needs --team, --main, and --participants. "
            "Run `panel_client.py setup` first to bootstrap state, or pass "
            "them explicitly.",
            file=sys.stderr,
        )
        return 2

    participants = _parse_participants_csv(participants_raw)
    if not participants:
        print("error: --participants must be a non-empty comma-separated list.", file=sys.stderr)
        return 2

    code = _check_balance_or_fail(args.base_url, args.api_key, "challenge")
    if code is not None:
        return code

    if not args.quiet:
        print("submitting challenge")
        if project:
            print(f"  project: {project} (memory defaults to expanded)")

    evidence = [e for e in (args.evidence or []) if e.strip()]
    response = api_submit_challenge(
        args.base_url,
        args.api_key,
        position=args.position,
        evidence=evidence,
        decision_pending=args.decision_pending,
        team=team,
        main_persona=main,
        participants=participants,
        project=project,
        model=args.model,
        temperature=args.temperature,
        memory=args.memory,
        use_search=args.use_search,
    )
    job_id = response["job_id"]
    session_id = response.get("session_id", "")

    if not args.quiet:
        print(f"  job_id:     {job_id}")
        print(f"  session_id: {session_id}")
        print()

    if args.no_poll:
        if args.json:
            print(_pretty(response))
        return 0

    if not args.quiet:
        print("polling for verdict...")
    final = api_poll_job(
        args.base_url,
        args.api_key,
        job_id,
        interval=args.poll_interval,
        timeout=args.timeout,
        quiet=args.quiet,
    )

    if args.json:
        print(_pretty(final))
    else:
        _print_turn_result(final)
    return 0 if final.get("status") == "done" else 1


def cmd_setup(args: argparse.Namespace) -> int:
    try:
        setup = api_stream_advise_setup(
            args.base_url,
            args.api_key,
            hint=args.hint,
            on_token=lambda t: print(t, end="", file=sys.stderr, flush=True),
        )
        print(file=sys.stderr)
    except (URLError, RuntimeError) as exc:
        print(f"error: setup endpoint failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(_pretty(setup))
    else:
        _print_setup_guide(setup)
    return 0


def cmd_help(args: argparse.Namespace) -> int:
    if not args.topic:
        print("error: topic is required.", file=sys.stderr)
        return 2
    try:
        advice = api_stream_advise(
            args.base_url,
            args.api_key,
            topic=args.topic,
            on_token=lambda t: print(t, end="", file=sys.stderr, flush=True),
        )
        print(file=sys.stderr)
    except (URLError, RuntimeError) as e:
        print(f"error: advisor endpoint failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(_pretty(advice))
    else:
        _print_advice(advice)
    return 0


# ── argparse setup ──────────────────────────────────────────────────────────


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-url",
        default=_env_base_url(),
        help="Panel base URL (default: %(default)s, or $PANEL_BASE_URL)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON instead of a human-readable summary",
    )


def _add_turn_args(parser: argparse.ArgumentParser) -> None:
    """Flags shared by ask/debate/explore/challenge (excluding participants)."""
    parser.add_argument("--project", help="Active project (inherits from panel state)")
    parser.add_argument(
        "--memory", choices=["basic", "expanded"], default=None,
        help="Override memory mode; server defaults to expanded when --project is set.",
    )
    parser.add_argument("--model", default=None, help=f"LLM model (default: {DEFAULT_LLM})")
    parser.add_argument("--temperature", type=float, default=None, help="Override the temperature")
    parser.add_argument(
        "--search", dest="use_search", action="store_true", default=None,
        help=(
            "Enable live web search for this turn. Add when the topic needs "
            "current/external facts; `help` flags it as `use_search_suggested`."
        ),
    )
    parser.add_argument(
        "--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL,
        help="Seconds between poll attempts (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_POLL_TIMEOUT,
        help="Poll timeout in seconds (default: %(default)s)",
    )
    parser.add_argument("--no-poll", action="store_true", help="Submit and return immediately")
    parser.add_argument("--quiet", action="store_true", help="Suppress stage printouts")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="panel_client.py",
        description="Companion Panel public API v1 CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Set PANEL_API_KEY in your environment or in a .env file next to this "
            "script. Generate a key at Profile -> API Access.\n\n"
            "Note for LLM agents: runs can take several minutes (panels and "
            "discussions up to 10-15 min). Use --no-poll to submit and return "
            "immediately, then check the result later with `status --job-id <id>`."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    # discover
    p_disc = sub.add_parser(
        "discover",
        help="List teams, modes, models, and short persona forensics",
    )
    _add_common_args(p_disc)
    p_disc.add_argument(
        "--no-shorts", action="store_true",
        help="Skip fetching short forensics for each persona (faster)",
    )
    p_disc.set_defaults(func=cmd_discover)

    # balance
    p_bal = sub.add_parser("balance", help="Print the caller's wallet balance")
    _add_common_args(p_bal)
    p_bal.set_defaults(func=cmd_balance)

    # projects
    p_proj = sub.add_parser("projects", help="Project management")
    proj_sub = p_proj.add_subparsers(dest="projects_command", required=True)

    p_proj_list = proj_sub.add_parser("list", help="List the caller's projects")
    _add_common_args(p_proj_list)
    p_proj_list.set_defaults(func=cmd_projects_list)

    p_proj_create = proj_sub.add_parser("create", help="Create a new project")
    _add_common_args(p_proj_create)
    p_proj_create.add_argument("name", help="Project name")
    p_proj_create.add_argument(
        "--set-active", action="store_true",
        help="Bind this working directory to the new project via `.claude/panel_state.json`.",
    )
    p_proj_create.add_argument("--team", help="Also bind a default team when --set-active is passed.")
    p_proj_create.add_argument("--main", help="Also bind a default main persona when --set-active is passed.")
    p_proj_create.set_defaults(func=cmd_projects_create)

    # state
    p_state = sub.add_parser("state", help="Inspect/manage the panel state file")
    state_sub = p_state.add_subparsers(dest="state_command", required=True)

    p_state_show = state_sub.add_parser("show", help="Print current panel state")
    _add_common_args(p_state_show)
    p_state_show.set_defaults(func=cmd_state_show)

    p_state_set = state_sub.add_parser("set", help="Set one key in the panel state")
    p_state_set.add_argument("key", help="State key (project, team, main_persona, ...)")
    p_state_set.add_argument("value", help="Value to set")
    p_state_set.set_defaults(func=cmd_state_set)

    p_state_clear = state_sub.add_parser("clear", help="Remove the panel state file")
    p_state_clear.set_defaults(func=cmd_state_clear)

    # status
    p_status = sub.add_parser("status", help="Check the status of a submitted job")
    _add_common_args(p_status)
    p_status.add_argument("--job-id", required=True, help="The job_id returned by a previous submission")
    p_status.set_defaults(func=cmd_status)

    # setup
    p_setup = sub.add_parser(
        "setup",
        help="Onboarding: propose primary team / project / per-intent defaults",
    )
    _add_common_args(p_setup)
    p_setup.add_argument(
        "hint", nargs="?", default=None,
        help="Optional one-line context about what you plan to work on.",
    )
    p_setup.set_defaults(func=cmd_setup)

    # help
    p_help = sub.add_parser(
        "help",
        help="Recommend a mode + participants for a topic (fast, no real run)",
    )
    _add_common_args(p_help)
    p_help.add_argument("topic", help="Topic to explore")
    p_help.set_defaults(func=cmd_help)

    # ask
    p_ask = sub.add_parser("ask", help="Quick single-persona take (~1-2 min)")
    _add_common_args(p_ask)
    p_ask.add_argument("topic", help="The question/prompt for the persona")
    p_ask.add_argument("--team", help="Team folder name (inherits from panel state)")
    p_ask.add_argument(
        "--persona",
        help=(
            "Persona name (inherits from panel state `answer_persona` or "
            "`main_persona`). Used as both main persona and participant."
        ),
    )
    _add_turn_args(p_ask)
    p_ask.set_defaults(func=cmd_ask)

    # debate / explore / review share the same arg shape
    for name, help_text, handler in (
        ("debate", "Back-and-forth discussion with transcript (~10-15 min)", cmd_debate),
        ("explore", "Deep multi-perspective synthesis (~12-20 min)", cmd_explore),
        ("review",  "Progress/alignment review — upstream personas + main synthesis (parallel_with_main) (~8-12 min)", cmd_review),
    ):
        parser = sub.add_parser(name, help=help_text)
        _add_common_args(parser)
        parser.add_argument("topic", help="The question/prompt for the group")
        parser.add_argument("--team", help="Team folder name (inherits from panel state)")
        parser.add_argument("--main", help="Main persona (inherits from panel state)")
        parser.add_argument(
            "--participants",
            help=(
                "Comma-separated list of personas (e.g. Alice,Bob,upstream:depth_miner). "
                "Inherits from panel state."
            ),
        )
        _add_turn_args(parser)
        parser.set_defaults(func=handler)

    # challenge
    p_chal = sub.add_parser("challenge", help="Adversarial panel on a held position (~8-15 min)")
    _add_common_args(p_chal)
    p_chal.add_argument("position", help="The position to stress-test")
    p_chal.add_argument(
        "--evidence", action="append", default=[],
        help="Supporting evidence item (repeat the flag for multiple).",
    )
    p_chal.add_argument(
        "--decision-pending", default=None,
        help="What decision is about to be made based on this position.",
    )
    p_chal.add_argument("--team", help="Team folder (inherits from panel state)")
    p_chal.add_argument("--main", help="Main persona (inherits from panel state)")
    p_chal.add_argument(
        "--participants",
        help="Comma-separated list of personas to attack the position.",
    )
    _add_turn_args(p_chal)
    p_chal.set_defaults(func=cmd_challenge)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.api_key = _env_api_key()

    try:
        return args.func(args)
    except APIError as e:
        print(f"HTTP {e.status_code}: {e.body}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
