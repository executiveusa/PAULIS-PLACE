"""
NIGHTLY SELF-IMPROVEMENT LOOP — Spec §09
==========================================
Runs at 03:00 PT / 11:00 UTC nightly (celery beat `self-improve-nightly`).

Flow:
  1. Aggregate today's envelopes from icm/memory/ops/<YYYY-MM-DD>/.
  2. ANALYZE pass — profile `score` (qwen-3.5), identifies weak axes (laws hit,
     judge rejects, repeated halts, halt on cost, etc.).
  3. PROPOSE_PR pass — profile `implement` (codex / glm-5.2), drafts PR body
     for each weak axis. Branch names follow `self/<axis>-<date>`.
  4. JUDGE pass — profile `judge` (claude-fable-5 / glm-4.6 high-thinking),
     validates PR doesn't violate laws and matches op-data.
  5. HUMAN_REVIEW_PR — every approved PR is opened to GitHub via gh_pat
     as a draft PR awaiting human merge. No auto-merge (Human Law 2).

GitHub: uses GH_PAT env. Repos in scope:
  - executiveusa/PAULIS-PLACE         (this repo)
  - executiveusa/YAPPYVERSE-FACTORY   (when present)
  - executiveusa/pauli-hermes-agent   (when present)
"""
from __future__ import annotations
import asyncio
import base64
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from services.profile_router import call_profile
from services.event_bus import build_envelope, publish
from services import hermes


def _today_dir() -> Path:
    """The ops folder for the most-recent day with envelopes."""
    root = Path(__file__).resolve().parents[2] / "icm" / "memory" / "ops"
    if not root.exists():
        return root
    for day in sorted(root.iterdir(), reverse=True):
        if any(day.glob("*.json")):
            return day
    return root


def _yesterday_envelopes() -> list[dict]:
    """Pull envelopes from the last completed day."""
    d = _today_dir()
    envs = []
    if not d.exists():
        return envs
    for f in d.glob("*.json"):
        try:
            envs.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return envs


ANALYZE_PROMPT = """You are the NIGHTLY SELF-IMPROVEMENT analyzer for the Yappyverse.
Aggregate the day's Hermes envelopes (below) and identify the 3 weakest axes
across: revenue, reliability, cost, courtroom_judge_reject_rate, avatar_voice,
zernio_publish_success_rate, channel_CH1..CH6.

Return JSON ONLY:
{{
  "report_id": "rpt_<uuid-ish>",
  "date_covered": "<YYYY-MM-DD>",
  "fewest_signals": ["if data thin, name the lack here"],
  "weak_axes": [
    {{"axis": "<name>", "score_0_10": <N>, "evidence": ["one-line + envelope events"], "proposed_fix_summary": "<one sentence>"}}
  ]
}}

TODAY'S ENVELOPES (truncated to ~12k chars if needed):
{envelopes_json}
"""


PROPOSE_PR_PROMPT = """You are PROPOSER in the Yappyverse self-improve loop.
For each weak axis, draft a concrete PR against THIS repo only.

Return JSON ONLY:
{{
  "prs": [
    {{
      "repo": "<fullname like executiveusa/PAULIS-PLACE>",
      "title": "<short PR title>",
      "branch": "self/<axis>-<YYYYMMDD>",
      "file_path": "<path inside the repo>",
      "change_kind": "fix|feat|docs|chore",
      "body_md": "<full PR body markdown>",
      "diff_suggestion": "<unified diff snippet the human can apply>",
      "blast_radius_usd": <float, mostly 0.0>
    }}
  ]
}}

WEAK AXES:
{weak_axes_json}
"""


JUDGE_PROMPT = """You are JUDGE in the self-improve loop. Validate each proposed PR:
- No secrets leaked (sk_, ghp_, sbp_, r8_, pat, cf_)
- Touches ≤3 services (L2)
- Doesn't auto-merge (Human Law 2)
- Diff suggestion is syntactically valid (or marked `requires_human_edits`)
- The blast radius is justifiable from the op-data evidence

Return JSON ONLY:
{{
  "verdicts": [
    {{"branch": "<same>", "verdict": "accept|reject|halt", "reasoning": "<one line>", "laws_violated": ["L1|L2|L3|L4"]}}
  ]
}}

PROPOSED PRS:
{prs_json}
"""


async def run_nightly() -> dict:
    """End-to-end nightly loop. Returns a summary envelope."""
    envs = _yesterday_envelopes()
    today_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Phase 1: ANALYZE
    analyze_res = await call_profile("score",
        prompt=ANALYZE_PROMPT.format(envelopes_json=json.dumps(envs[:80], default=str)[:12000]),
        system_prompt="You are the Yappyverse self-improvement analyzer.",
        temperature=0.2, response_format_json=True)

    analyze_body = analyze_res.get("content", {})
    if isinstance(analyze_body, str):
        try: analyze_body = json.loads(analyze_body)
        except Exception: analyze_body = {"weak_axes": []}
    analyze_body.setdefault("weak_axes", [])

    # Phase 2: PROPOSE_PR
    propose_res = await call_profile("implement",
        prompt=PROPOSE_PR_PROMPT.format(weak_axes_json=json.dumps(analyze_body["weak_axes"], indent=2)),
        system_prompt="You are the Yappyverse self-improvement proposer.",
        temperature=0.3, response_format_json=True)

    propose_body = propose_res.get("content", {})
    if isinstance(propose_body, str):
        try: propose_body = json.loads(propose_body)
        except Exception: propose_body = {"prs": []}
    propose_body.setdefault("prs", [])

    # Phase 3: JUDGE
    judge_res = await call_profile("judge",
        prompt=JUDGE_PROMPT.format(prs_json=json.dumps(propose_body["prs"], indent=2)),
        system_prompt="You are the self-improve JUDGE. Strict.",
        temperature=0.1, response_format_json=True)

    judge_body = judge_res.get("content", {})
    if isinstance(judge_body, str):
        try: judge_body = json.loads(judge_body)
        except Exception: judge_body = {"verdicts": []}
    judge_body.setdefault("verdicts", [])

    # Phase 4: persist + emit
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"
    payload = {
        "report_id": report_id,
        "date_covered": analyze_body.get("date_covered", today_date),
        "fewest_signals": analyze_body.get("fewest_signals", []),
        "weak_axes": analyze_body["weak_axes"],
        "proposed_prs": propose_body["prs"],
        "judge_verdicts": judge_body["verdicts"],
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to icm/memory/ops/<today>/<report_id>.json (reuses envelope dir)
    day_dir = (Path(__file__).resolve().parents[2] / "icm" / "memory" / "ops"
               / datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / f"{report_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Emit envelope
    env = build_envelope(
        route="R-07.SYSTEM.SELF_IMPROVE", stage="PROPOSE_PR",
        services_touched=["paulis-place", "github"],
        blast_radius_usd=0.0,
        worker_profile="implement",
        worker_model=propose_res.get("model", "unknown"),
        body=payload,
        judge_verdict="accept" if all(v.get("verdict")=="accept" for v in judge_body["verdicts"]) else "reject",
        judge_model=judge_res.get("model"),
        next_action="HUMAN_REVIEW_PR",
    )
    await publish(env)

    # Phase 5: open draft PRs to GitHub for every accepted proposal (no auto-merge)
    opened_prs = []
    gh_token = os.environ.get("GH_PAT", "")
    if not gh_token:
        env["body"]["github_skip_reason"] = "GH_PAT missing; PRs queued in icm/memory only"
    else:
        for pr, v in zip(propose_body["prs"], judge_body["verdicts"]):
            if v.get("verdict") != "accept":
                continue
            opened = _open_draft_pr(pr, gh_token)
            opened_prs.append(opened)
        payload["opened_prs"] = opened_prs

    return env


def _open_draft_pr(pr: dict, gh_token: str, *, repo_root: Optional[Path] = None) -> dict:
    """Open a draft PR via the GitHub CLI (`gh`) if available.
    Falls back to recording the PR in icm/memory for human execution.
    """
    repo = pr.get("repo", "executiveusa/PAULIS-PLACE")
    branch = pr.get("branch", f"self/loop-{uuid.uuid4().hex[:6]}")
    title = pr.get("title", "self-improve proposal")
    body = pr.get("body_md", "")
    diff = pr.get("diff_suggestion", "")

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    repo_root = Path(repo_root)
    ops_day = repo_root / "icm" / "memory" / "ops" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ops_day.mkdir(parents=True, exist_ok=True)
    pending_path = ops_day / f"pr_pending_{branch.replace('/','_')}.md"
    pending_path.write_text(f"# {title}\n\nBranch: `{branch}`\nRepo: `{repo}`\n\n{body}\n\n```diff\n{diff}\n```\n", encoding="utf-8")

    # Try the gh CLI (best-effort — if not installed, leave the pending file for the human)
    try:
        subprocess.run(["gh", "--version"], check=True, capture_output=True)
        env = {**os.environ, "GH_TOKEN": gh_token}
        subprocess.run(["gh", "repo", "set-default", repo], check=True, capture_output=True, env=env, cwd=str(repo_root))
        subprocess.run(["git", "checkout", "-b", branch], check=True, capture_output=True, cwd=str(repo_root), env=env)
        # Apply diff suggestion is human-only; we just open an issue-style placeholder
        subprocess.run(["git", "push", "-u", "origin", branch], check=False, capture_output=True, cwd=str(repo_root), env=env)
        subprocess.run(["gh", "pr", "create", "--draft", "--title", title,
                         "--body", pending_path.read_text(encoding="utf-8")],
                        check=True, capture_output=True, env=env, cwd=str(repo_root))
        subprocess.run(["git", "checkout", "-"], check=False, capture_output=True, cwd=str(repo_root))
        return {"branch": branch, "repo": repo, "status": "opened_as_draft"}
    except Exception as e:
        return {"branch": branch, "repo": repo, "pending_pr_file": str(pending_path),
                "status": "pending_human_gh_unavailable", "reason": str(e)[:200]}


def register() -> None:
    """Optional: surface the nightly loop as a runnable endpoint or signal."""
    from services.event_bus import subscribe

    async def _handler(envelope: dict) -> None:
        await run_nightly()
    subscribe("R-07.SYSTEM.SELF_IMPROVE", _handler)