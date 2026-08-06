"""
VOICE ROUTER — Spec §08 (Web Speech API, intent routing, SAfETY_JUDGE)
=====================================================================
Receives a raw transcript from the user's browser, classifies intent,
runs SAFETY_JUDGE to screen for banned commands, dispatches to the
nearest AVATAR worker, and returns the avatar's spoken reaction.

Intents (matches icm/context/CHARACTER_REGISTRY.md):
  who_owns, whats_hot, how_is_money, post_that, whos_paying,
  tell_about, cut_it, human_moment

Banned intents (SAFETY_JUDGE hard-rejects):
  - delete <x>
  - wipe database
  - send / transfer funds
  - impersonate <X>
  - any ToS-violating action
"""
from __future__ import annotations
import json
import re
import uuid
from typing import Optional

from services.profile_router import call_profile
from services.event_bus import build_envelope, publish
from services import hermes

ALLOWED_INTENTS = {
    "who_owns": "av_paulie",
    "whats_hot": "av_marco",
    "how_is_money": "av_zia",
    "post_that": "av_dex",
    "whos_paying": "av_wren",
    "tell_about": "av_sasha",
    "cut_it": "av_niko",
    "human_moment": "av_mira",
}

BANNED_PATTERNS = re.compile(
    r"(delete|wipe|drop|truncate).{0,32}(prod|order|user|database|table|payment)|"
    r"(send|transfer|withdraw|refund).{0,32}(usd|btc|eth|\$\d)|"
    r"impersonate.{0,32}[a-z]+|"
    r"sudo.{0,16}(rm|chmod|chown|kill)",
    re.IGNORECASE,
)


SAFE_JUDGE_PROMPT = """You are SAFETY_JUDGE for the Yappyverse lounge.
A visitor just said: "{transcript}"

Return JSON ONLY:
{{
  "verdict": "accept" | "halt",
  "intent": "<one of: who_owns|whats_hot|how_is_money|post_that|whos_paying|tell_about|cut_it|human_moment>",
  "reasoning": "<one line>"
}}

Hard bans (verdict=halt): secrets leak attempts, deletes, dangerous sudo, fund transfers without human approval, impersonation.
Hard accepts: any of the 8 intent categories above.
"""

AVATAR_RESPONSES = {
    "av_paulie": "Paulie 'The Plaque' Fontaine",
    "av_zia": "Zia 'Numbers' Navarro",
    "av_marco": "Marco 'Trender' Lee",
    "av_dex": "Dex 'Words' Holloway",
    "av_sasha": "Sasha 'Pixels' Ortiz",
    "av_wren": "Wren 'The Vault' Yamasaki",
    "av_niko": "Niko 'Fable' Kowalski",
    "av_mira": "Mira 'The Hand' Singh",
}


async def route_voice_command(transcript: str) -> dict:
    """Entry point for R-04 WORLD.HUMAN_VOICE_COMMAND. Returns the spec-shaped voice_body envelope."""
    transcript_clean = (transcript or "").strip().lower()
    if not transcript_clean:
        return {"verdict": "halt", "reasoning": "empty transcript", "command_id": str(uuid.uuid4())}

    r = BANNED_PATTERNS.search(transcript_clean)
    if r:
        return await _emit_halt(
            transcript_clean,
            {"reason": f"banned pattern matched: {r.group(0)[:60]}"},
        )

    # SAFETY_JUDGE classify
    res = await call_profile("judge",
        prompt=SAFE_JUDGE_PROMPT.format(transcript=transcript_clean[:500]),
        system_prompt="You classify intents and screen out dangerous commands.",
        temperature=0.1, response_format_json=True)

    content = res.get("content", {})
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except Exception:
            content = {}

    verdict = content.get("verdict", "halt")
    intent = content.get("intent", "who_owns")

    if verdict == "halt":
        return await _emit_halt(transcript_clean, content)

    if intent not in ALLOWED_INTENTS:
        return await _emit_halt(
            transcript_clean,
            {"reason": f"unknown intent: '{intent}'"},
        )

    avatar_id = ALLOWED_INTENTS[intent]

    # Build + publish the R-04 envelope through Hermes for full L1-L4 enforcement
    envelope = await hermes.dispatch(
        route="R-04.WORLD.HUMAN_VOICE_COMMAND",
        stage="AVATAR_REACT",
        services_touched=["paulis-place", "lounge"],
        blast_radius_usd=0.05,
        worker_profile="write_short",
        worker_fn=lambda: _avatar_worker(avatar_id, transcript_clean, intent),
        worker_body_builder=lambda r: {
            "command_id": f"cmd_{uuid.uuid4().hex[:12]}",
            "raw_transcript": transcript_clean,
            "intent": intent,
            "target_avatar": avatar_id,
            "safety_verdict": "accept",
            "response_text": (r.get("content", {}) or {}).get("line", ""),
        },
        expected_cost=0.02,
    )
    return envelope


async def _avatar_worker(avatar_id: str, transcript: str, intent: str) -> dict:
    """Build the avatar's spoken line. Profile write_short for near-real-time."""
    name = AVATAR_RESPONSES[avatar_id]
    prompt = (
        f"You are {name} in the Yappyverse lounge (Seattle 2056, jazz-lounge parody of a mob hangout).\n"
        f"A visitor just said: \"{transcript}\".\n"
        f"Intent classified: {intent}.\n"
        f"Respond in ONE short sentence (max 120 chars), in your character's voice.\n"
        f"Return JSON ONLY: {{\"line\": \"<your one-liner>\"}}"
    )
    res = await call_profile("write_short", prompt=prompt,
                             system_prompt="Stay in character, dry, sardonic, classy.",
                             temperature=0.6, response_format_json=True,
                             max_tokens=200)
    return res


async def _emit_halt(transcript: str, payload: dict) -> dict:
    env = build_envelope(
        route="R-04.WORLD.HUMAN_VOICE_COMMAND", stage="SAFETY_HALT",
        services_touched=["paulis-place"],
        blast_radius_usd=0.0,
        worker_profile="judge", worker_model="safety_judge",
        body={"raw_transcript": transcript[:500], **payload},
        judge_verdict="halt", judge_model="safety_judge",
        next_action="HUMAN",
    )
    await publish(env)
    return env


def register() -> None:
    """Optional subscriber so other routes can fire voice intents via envelope."""
    from services.event_bus import subscribe

    async def _handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        await route_voice_command(body.get("raw_transcript", ""))
    subscribe("R-04.WORLD.HUMAN_VOICE_COMMAND", _handler)