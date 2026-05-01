"""Companion Panel — public API v1 CLI.

Zero-dependency command-line client for the ``/api/v1/*`` surface.

Subcommands
-----------
    setup [HINT]              Discover teams/personas and write panel_state.json
    call TOPIC                Submit one turn with explicit mode/participants
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
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Configuration ───────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://panel.humx.ai"
DEFAULT_POLL_INTERVAL = 30.0
DEFAULT_POLL_TIMEOUT = 1200.0
DEFAULT_POLL_MAX_CONSECUTIVE_FAILURES = 5
DEFAULT_LLM = "qwen/qwen3-max"
EXPENSIVE_MODEL_HINTS = ("opus",)

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
        base_url = _env_base_url()
        print(
            "error: PANEL_API_KEY is not set.\n"
            f"Generate one at {base_url}/profile -> API Access, then either:\n"
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
# persona + optional project, caches discover output, and records which
# participants have worked well for broad task categories.


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


def _write_panel_state(data: dict) -> Path:
    path = _find_panel_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
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


def _display_value(key: str, value):
    if key == "short" and value is None:
        return "Not available"
    if isinstance(value, dict):
        return {k: _display_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_display_value(key, item) for item in value]
    return value


def _display_state(state: dict) -> dict:
    return _display_value("", state)


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
        if team:
            body["team"] = team
        if main_persona:
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _participant_ref(raw: str, *, default_branch: str = "main") -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if ":" in raw:
        branch, name = raw.split(":", 1)
        return f"{branch.strip()}:{name.strip()}"
    return f"{default_branch}:{raw}"


def _participants_csv(refs: list[str]) -> str:
    return ",".join(ref for ref in refs if ref)


def _discover_with_shorts(base_url: str, api_key: str) -> dict:
    data = api_discover(base_url, api_key)
    teams = data.get("teams", [])
    unique_names: list[str] = []
    seen: set[str] = set()
    for team in teams:
        for name in team.get("main_personas", []) or []:
            if name and name not in seen:
                seen.add(name)
                unique_names.append(name)
        for participant in team.get("participants", []) or []:
            name = participant.get("name")
            if name and name not in seen:
                seen.add(name)
                unique_names.append(name)
    shorts = _fetch_shorts(base_url, api_key, unique_names) if unique_names else {}
    return {**data, "shorts": shorts}


def _normalize_team_roster(discover: dict) -> dict:
    teams: dict[str, dict] = {}
    shorts = discover.get("shorts") or {}
    for team in discover.get("teams", []) or []:
        name = team.get("name")
        if not name:
            continue
        main_personas = team.get("main_personas", []) or []
        personas: list[dict] = []
        ids: dict[str, str | None] = {}
        for main_name in main_personas:
            ref = f"main:{main_name}"
            ids[ref] = None
            personas.append({
                "ref": ref,
                "id": None,
                "name": main_name,
                "branch": "main",
                "short": shorts.get(main_name),
            })
        for p in team.get("participants", []) or []:
            pname = p.get("name")
            branch = p.get("branch") or "main"
            if not pname:
                continue
            ref = f"{branch}:{pname}"
            pid = p.get("id") or p.get("persona_id") or p.get("uuid")
            ids[ref] = pid
            personas.append({
                "ref": ref,
                "id": pid,
                "name": pname,
                "branch": branch,
                "short": shorts.get(pname),
                "raw": p,
            })
        teams[name] = {
            "id": team.get("id") or team.get("team_id") or team.get("uuid"),
            "main_personas": main_personas,
            "personas": personas,
            "persona_ids": ids,
        }
    return teams


def _fallback_participants_for_team(team_state: dict, *, max_count: int = 4) -> list[str]:
    personas = team_state.get("personas") or []
    refs = [
        p.get("ref", "")
        for p in personas
        if p.get("branch") in {"upstream", "downstream", "lateral"}
    ]
    return [ref for ref in refs if ref][:max_count]


def _recommended_participants(setup: dict, teams: dict, team: str, main_persona: str) -> dict:
    defaults = setup.get("default_participants") or {}
    team_state = teams.get(team, {})
    fallback = _fallback_participants_for_team(team_state)

    answer_raw = _as_list(defaults.get("answer"))
    answer = [_participant_ref(answer_raw[0], default_branch="main")] if answer_raw else []
    if not answer and main_persona:
        answer = [f"main:{main_persona}"]

    parallel = [
        _participant_ref(ref, default_branch="main")
        for ref in (
            _as_list(defaults.get("parallel"))
            or _as_list(defaults.get("panel"))
            or fallback
        )
    ]
    parallel_with_main = [
        _participant_ref(ref, default_branch="main")
        for ref in (
            _as_list(defaults.get("parallel_with_main"))
            or _as_list(defaults.get("panel"))
            or fallback
        )
    ]

    return {
        "answer": answer,
        "parallel": parallel,
        "parallel_with_main": parallel_with_main,
    }


def _build_panel_state(setup: dict, discover: dict, existing: dict) -> dict:
    primary_team = (setup.get("primary_team") or existing.get("team") or "").strip()
    primary_main = (
        setup.get("primary_main_persona")
        or existing.get("main_persona")
        or ""
    ).strip()
    teams = _normalize_team_roster(discover)
    recommended = _recommended_participants(setup, teams, primary_team, primary_main)

    return {
        "version": 2,
        "created_at": existing.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
        "team": primary_team,
        "main_persona": primary_main,
        "project": existing.get("project"),
        "setup": setup,
        "discover": discover,
        "teams": teams,
        "recommended_participants": recommended,
        "history": existing.get("history") or [],
        "category_participants": existing.get("category_participants") or {},
    }


def _first_main_persona(discover: dict) -> tuple[str, str] | None:
    for team in discover.get("teams", []) or []:
        team_name = (team.get("name") or "").strip()
        if not team_name:
            continue
        for main_name in team.get("main_personas", []) or []:
            main_name = str(main_name).strip()
            if main_name:
                return team_name, main_name
    return None


def _build_discovered_panel_state(discover: dict, existing: dict) -> dict:
    first = _first_main_persona(discover)
    if first is None:
        raise RuntimeError("discover returned no team with a main persona")
    primary_team, primary_main = first
    teams = _normalize_team_roster(discover)
    answer_ref = f"main:{primary_main}"

    return {
        "version": 2,
        "created_at": existing.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
        "team": primary_team,
        "main_persona": primary_main,
        "project": existing.get("project"),
        "setup": {"source": "discover"},
        "discover": discover,
        "teams": teams,
        "recommended_participants": {
            "answer": [answer_ref],
            "parallel": [],
            "parallel_with_main": [],
        },
        "history": existing.get("history") or [],
        "category_participants": existing.get("category_participants") or {},
    }


def _discover_default_state(base_url: str, api_key: str, existing: dict) -> dict:
    discover = api_discover(base_url, api_key)
    state = _build_discovered_panel_state(discover, existing)
    _write_panel_state(state)
    return state


def _record_panel_usage(
    *,
    category: str,
    mode: str,
    participants: list[dict],
    prompt: str,
    project: str | None,
    job_id: str,
    session_id: str,
) -> None:
    state = _load_panel_state()
    if not state:
        return
    refs = [f"{p.get('branch', 'main')}:{p.get('name', '')}" for p in participants]
    event = {
        "timestamp": _now_iso(),
        "category": category,
        "mode": mode,
        "participants": refs,
        "prompt": prompt,
        "project": project,
        "job_id": job_id,
        "session_id": session_id,
    }
    history = list(state.get("history") or [])
    history.append(event)
    state["history"] = history[-50:]

    categories = dict(state.get("category_participants") or {})
    previous = categories.get(category) or {}
    categories[category] = {
        "mode": mode,
        "participants": refs,
        "last_prompt": prompt,
        "last_used": event["timestamp"],
        "uses": int(previous.get("uses") or 0) + 1,
    }
    state["category_participants"] = categories
    state["updated_at"] = event["timestamp"]
    _write_panel_state(state)


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

    print("\n(unknown payload kind — raw payload follows)")
    print(_pretty(payload))


def _setup_advisor_narrative(raw: str) -> str:
    """Return the human advisor prose before the machine-readable setup block."""
    if not raw:
        return ""
    return raw.split("<setup", 1)[0].strip()


def _persona_shorts_summary(state: dict) -> str | None:
    seen: set[str] = set()
    total = 0
    available = 0
    for team in (state.get("teams") or {}).values():
        for persona in team.get("personas") or []:
            ref = persona.get("ref") or persona.get("name")
            if not ref or ref in seen:
                continue
            seen.add(ref)
            total += 1
            if persona.get("short"):
                available += 1
    if total == 0:
        return None
    if available == 0:
        return "persona shorts: Not available"
    if available < total:
        return f"persona shorts: {available}/{total} available; missing shorts show as Not available"
    return f"persona shorts: {available}/{total} available"


def _print_setup_guide(guide: dict, *, state: dict | None = None, advisor_text: str = "") -> None:
    overview = (guide.get("overview") or "").strip()
    primary_team = (guide.get("primary_team") or "").strip()
    primary_main = (guide.get("primary_main_persona") or "").strip()
    suggest = guide.get("suggest_project") or None
    narrative = _setup_advisor_narrative(advisor_text)

    print("\n── panel setup ──\n")
    if narrative:
        print(narrative)
        print()
        if overview and overview not in narrative:
            print(overview)
            print()
    elif overview:
        print(overview)
        print()

    if not primary_team:
        print("(no apply commands — the advisor could not bootstrap state.)")
        return

    print(f"primary team:    {primary_team}")
    print(f"main persona:    {primary_main or '-'}")
    if state:
        shorts = _persona_shorts_summary(state)
        if shorts:
            print(shorts)

    if suggest:
        name = (suggest.get("name") or "").strip()
        why = (suggest.get("rationale") or "").strip()
        if name:
            print(f"\nsuggested project:  {name}")
            if why:
                print(f"  why: {why}")


# ── Subcommand handlers ─────────────────────────────────────────────────────


def _parse_participant(raw: str) -> dict:
    """Parse ``branch:name`` or plain ``name`` into a participant dict."""
    if ":" in raw:
        branch, name = raw.split(":", 1)
        return {"name": name.strip(), "branch": branch.strip()}
    return {"name": raw.strip(), "branch": "main"}


def _parse_participants_csv(raw: str) -> list[dict]:
    return [_parse_participant(p) for p in raw.split(",") if p.strip()]


def _is_expensive_turn(*, mode: str, model: str | None, use_search: bool | None) -> bool:
    model_name = (model or DEFAULT_LLM).lower()
    if mode in {"parallel", "parallel_with_main"}:
        return True
    if any(hint in model_name for hint in EXPENSIVE_MODEL_HINTS):
        return True
    return bool(use_search and any(hint in model_name for hint in EXPENSIVE_MODEL_HINTS))


def _check_balance_or_fail(base_url: str, api_key: str, run_label: str) -> int | None:
    """Return non-zero exit code if wallet is zero, else None."""
    try:
        balance = api_balance(base_url, api_key)
        if Decimal(balance.get("balance_usd", "0")) <= 0:
            print(
                f"error: wallet balance is {balance.get('balance_usd')} — "
                f"top up before submitting {run_label}.",
                file=sys.stderr,
            )
            return 3
    except APIError:
        raise
    except Exception:
        pass  # non-fatal — let the server decide
    return None


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
    for key, value in _display_state(state).items():
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


# ── Unified turn runner ─────────────────────────────────────────────────────


def _state_recommended_participants(state: dict, mode: str) -> list[str]:
    recommended = state.get("recommended_participants") or {}
    refs = _as_list(recommended.get(mode))
    if refs:
        return refs
    if mode == "answer" and state.get("main_persona"):
        return [f"main:{state['main_persona']}"]
    return []

def _resolve_call_participants(args: argparse.Namespace, state: dict) -> tuple[list[dict], str | None]:
    raw = getattr(args, "participants", None)
    if raw:
        refs = [_participant_ref(part) for part in raw.split(",") if part.strip()]
    else:
        refs = _state_recommended_participants(state, args.mode)

    if args.mode == "answer":
        if not refs:
            return [], None
        first = _parse_participant(refs[0])
        if first["branch"] != "main":
            print(
                "error: answer mode needs one main persona participant "
                "(for example --participants main:my_persona).",
                file=sys.stderr,
            )
            return [], None
        return [first], first["name"]

    return _parse_participants_csv(_participants_csv(refs)), None


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
    model = getattr(args, "model", None) or DEFAULT_LLM
    use_search = getattr(args, "use_search", None)
    expensive = _is_expensive_turn(mode=mode, model=model, use_search=use_search)
    if expensive and not args.quiet:
        print("pre-flight balance check for expensive turn...")
    code = _check_balance_or_fail(
        args.base_url,
        args.api_key,
        "an expensive turn" if expensive else "a turn",
    )
    if code is not None:
        return code

    idem_key = str(uuid.uuid4())
    if not args.quiet:
        print(f"submitting {mode} (idempotency_key={idem_key})")

    memory = getattr(args, "memory", None)
    if project and memory is None:
        memory = "basic"

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
        model=model,
        temperature=getattr(args, "temperature", None),
        memory=memory,
        use_search=use_search,
    )
    job_id = response["job_id"]
    session_id = response["session_id"]

    if not args.quiet:
        print(f"  job_id:     {job_id}")
        print(f"  session_id: {session_id}")
        if project:
            print(f"  project:    {project} (memory={memory})")
        print()

    category = getattr(args, "category", None) or mode
    _record_panel_usage(
        category=category,
        mode=mode,
        participants=participants,
        prompt=prompt,
        project=project,
        job_id=job_id,
        session_id=session_id,
    )

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


def cmd_call(args: argparse.Namespace) -> int:
    state = _load_panel_state()
    if (
        not state
        and args.mode == "answer"
        and not getattr(args, "team", None)
        and not getattr(args, "main", None)
        and not getattr(args, "participants", None)
    ):
        if not args.quiet:
            print("no panel state found; running lightweight discover for default main persona")
        try:
            state = _discover_default_state(args.base_url, args.api_key, state)
        except (APIError, URLError, RuntimeError) as exc:
            print(f"error: discover endpoint failed: {exc}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(
                "  selected: "
                f"{state.get('team')} / main:{state.get('main_persona')}"
            )

    team = getattr(args, "team", None) or state.get("team")
    main = getattr(args, "main", None) or state.get("main_persona")
    project = getattr(args, "project", None) or state.get("project")
    participants, answer_main = _resolve_call_participants(args, state)

    if args.mode == "answer" and answer_main:
        main = answer_main

    if not team or not main or not participants:
        print(
            "error: call needs team, main persona, and participants. "
            "Run `panel_client.py setup`, let answer mode run lightweight "
            "discover, or pass --team, --main, and --participants explicitly.",
            file=sys.stderr,
        )
        return 2

    return _submit_turn_and_render(
        args,
        team=team,
        main=main,
        participants=participants,
        mode=args.mode,
        prompt=args.topic,
        project=project,
    )


def cmd_setup(args: argparse.Namespace) -> int:
    if args.create_project and args.no_project:
        print("error: choose only one of --create-project or --no-project.", file=sys.stderr)
        return 2

    advisor_tokens: list[str] = []

    def _show_advisor_token(token: str) -> None:
        advisor_tokens.append(token)
        print(token, end="", file=sys.stderr, flush=True)

    try:
        setup = api_stream_advise_setup(
            args.base_url,
            args.api_key,
            hint=args.hint,
            on_token=_show_advisor_token,
        )
        print(file=sys.stderr)
    except (URLError, RuntimeError) as exc:
        print(f"error: setup endpoint failed: {exc}", file=sys.stderr)
        return 1

    try:
        discover = _discover_with_shorts(args.base_url, args.api_key)
    except (APIError, URLError) as exc:
        print(f"error: discover endpoint failed: {exc}", file=sys.stderr)
        return 1

    existing = _load_panel_state()
    state = _build_panel_state(setup, discover, existing)

    suggest = setup.get("suggest_project") or {}
    suggested_name = (args.project_name or suggest.get("name") or "").strip()
    existing_project = existing.get("project")
    if existing_project:
        state["project"] = existing_project
    elif args.create_project:
        if not suggested_name:
            print(
                "error: setup did not suggest a project name; pass --project-name.",
                file=sys.stderr,
            )
            return 2
        data = api_create_project(args.base_url, args.api_key, suggested_name)
        state["project"] = suggested_name
        state["project_created"] = bool(data.get("created"))
    elif suggested_name and not args.no_project and sys.stdin.isatty():
        reply = input(
            f"Create project {suggested_name!r} to enable panel memory? [y/N] "
        ).strip().lower()
        if reply in {"y", "yes"}:
            data = api_create_project(args.base_url, args.api_key, suggested_name)
            state["project"] = suggested_name
            state["project_created"] = bool(data.get("created"))
    elif args.no_project:
        state["project"] = None

    path = _write_panel_state(state)

    if args.json:
        print(_pretty({"path": str(path), "state": state}))
    else:
        _print_setup_guide(setup, state=state, advisor_text="".join(advisor_tokens))
        print(f"\nstate written: {path}")
        if state.get("project"):
            print(f"project: {state['project']} (future calls pass memory=basic)")
        elif suggest and suggested_name and not args.no_project:
            print(
                "\nproject not created. Ask the user whether to enable panel "
                "memory, then rerun setup with --create-project or --no-project."
            )
        print("\nrecommended participants:")
        for mode, refs in (state.get("recommended_participants") or {}).items():
            print(f"  {mode}: {', '.join(refs) if refs else '-'}")
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
    """Flags shared by unified turn calls."""
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
            "current or external facts."
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
            "script. Generate a key at <PANEL_BASE_URL>/profile -> API Access "
            f"(default: {DEFAULT_BASE_URL}).\n\n"
            "Note for LLM agents: parallel runs can take several minutes. "
            "Use --no-poll to submit and return "
            "immediately, then check the result later with `status --job-id <id>`."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

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
        help="Discover teams/personas and write panel_state.json",
    )
    _add_common_args(p_setup)
    p_setup.add_argument(
        "hint", nargs="?", default=None,
        help="Optional one-line context about what you plan to work on.",
    )
    p_setup.add_argument(
        "--create-project",
        action="store_true",
        help="Create and bind the setup-recommended project for panel memory.",
    )
    p_setup.add_argument(
        "--no-project",
        action="store_true",
        help="Write state without creating a project.",
    )
    p_setup.add_argument(
        "--project-name",
        help="Project name to create when --create-project is passed.",
    )
    p_setup.set_defaults(func=cmd_setup)

    # call
    p_call = sub.add_parser(
        "call",
        help="Submit a turn with mode answer, parallel, or parallel_with_main",
    )
    _add_common_args(p_call)
    p_call.add_argument("topic", help="The question/prompt for the panel")
    p_call.add_argument(
        "--mode",
        required=True,
        choices=["answer", "parallel", "parallel_with_main"],
        help="API mode to use for this question.",
    )
    p_call.add_argument("--team", help="Team folder name (inherits from panel state)")
    p_call.add_argument("--main", help="Main persona (inherits from panel state)")
    p_call.add_argument(
        "--participants",
        help=(
            "Comma-separated persona refs. Use branch:name, e.g. "
            "main:you,upstream:reviewer,lateral:outsider. Inherits mode "
            "recommendations from panel state when omitted; no-state answer "
            "mode can also omit this to discover and use the first main persona."
        ),
    )
    p_call.add_argument(
        "--category",
        default=None,
        help="Task category key used to update panel_state history.",
    )
    _add_turn_args(p_call)
    p_call.set_defaults(func=cmd_call)

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
