"""
ZERNIO SOCIAL POSTING SERVICE — Spec §05
=========================================
Wraps the Zernio REST API. One call publishes to 15+ platforms.
Used by PUBLISHER worker (R-02 PUBLISH) when STYLE_JUDGE accepts.

Env: ZERNIO_API_TOKEN (already wired from Cosmos_Vault.env)

Endpoints (per Zernio docs at zernio.com / spec 05 reading):
  POST  /v1/posts           create multi-platform post from one body
  GET   /v1/accounts        list connected accounts
  GET   /v1/posts/:id       post status
  DELETE /v1/posts/:id      delete by id (human-only — never auto)

Auth: Bearer ZERNIO_API_TOKEN.

Spec §05 section 3 notes a one-browser-click auth flow to obtain the token.
For MVP we use the token already in .env. The /v1/auth/start endpoint is
exposed here so the human can re-auth when the token expires.
"""
from __future__ import annotations
import os
from typing import Optional
import httpx


_BASE_URL = os.environ.get("ZERNIO_BASE_URL", "https://api.zernio.com")
DEFAULT_PLATFORMS = [
    "x", "facebook", "instagram", "linkedin", "pinterest",
    "tiktok", "youtube_shorts", "reddit", "bluesky", "threads",
    "mastodon", "telegram", "discord", "dev_to", "medium",
]


def _headers() -> dict[str, str]:
    tok = os.environ.get("ZERNIO_API_TOKEN", "")
    if not tok:
        raise RuntimeError("ZERNIO_API_TOKEN not set — see spec 05 section 3 (browser-click auth flow)")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


async def list_accounts() -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{_BASE_URL}/v1/accounts", headers=_headers())
        r.raise_for_status()
        return r.json()


async def start_auth() -> dict:
    """Begin the one-browser-click Zernio OAuth flow (spec §05 §3)."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{_BASE_URL}/v1/auth/start", headers=_headers(),
                              json={"redirect_url": os.environ.get("APP_URL", "http://localhost:3000")})
        r.raise_for_status()
        return r.json()


async def create_post(
    *,
    text: str,
    platforms: list[str] | None = None,
    media_urls: list[str] | None = None,
    scheduled_for: Optional[str] = None,
    product_id: Optional[str] = None,
) -> dict:
    """Publish one post across multiple platforms (Zernio fans out)."""
    body = {
        "text": text,
        "platforms": platforms or DEFAULT_PLATFORMS,
    }
    if media_urls:
        body["media_urls"] = media_urls
    if scheduled_for:
        body["scheduled_for"] = scheduled_for
    if product_id:
        body["metadata"] = {"product_id": product_id}

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{_BASE_URL}/v1/posts",
                              headers=_headers(), json=body)
        r.raise_for_status()
        return r.json()


async def get_post(post_id: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{_BASE_URL}/v1/posts/{post_id}", headers=_headers())
        r.raise_for_status()
        return r.json()


async def publish_pipeline(
    *,
    product_id: str,
    posts: list[dict],  # [{platform, text, cta}, ...] from PUBLISHER worker
) -> dict:
    """Take the PUBLISHER worker output (a list of post dicts) and ship each
    to Zernio. Returns the spec-shaped envelope (publish_body)."""
    attempted = []
    succeeded = []
    failed = []
    post_urls: dict[str, str] = {}

    for post in posts:
        platform = post.get("platform")
        if not platform:
            failed.append({"platform": "?", "reason": "missing platform"})
            continue
        attempted.append(platform)
        try:
            result = await create_post(
                text=post.get("text", ""),
                platforms=[platform],
                media_urls=post.get("media_urls"),
                product_id=product_id,
            )
            succeeded.append(platform)
            if result.get("post_url"):
                post_urls[platform] = result["post_url"]
        except Exception as e:
            failed.append({"platform": platform, "reason": str(e)[:300]})

    return {
        "product_id": product_id,
        "platforms_attempted": attempted,
        "platforms_succeeded": succeeded,
        "platforms_failed": failed,
        "post_urls": post_urls,
    }


# ---- STYLE_JUDGE gate (spec §05 §3) ----

async def style_judge(copies: list[dict]) -> dict:
    """Run the STYLE_JUDGE on each post draft.

    Returns {"accept": bool, "fixes": [...]}.
    Uses the judge profile but with brand-voice specific logic.
    """
    from services.profile_router import call_profile

    text_blob = "\n\n".join(
        f"[{c.get('platform','?')}] {c.get('text','')}" for c in copies
    )

    judge_prompt = """You are STYLE_JUDGE for Paulie's Place.
Reject these posts if any of:
- spam patterns (caps lock overuse, exclamation spam, emoji overuse)
- banned phrases ("get rich quick", "make $500/day", "100% guaranteed")
- AI忏悔-confessional ("I generated this with AI", "this is AI made") when platform ToS forbids
- off-brand tone (the brand is Seattle 2056 jazz lounge parody, NOT TikTok hype)
- copy that doesn't include the affiliate link placeholder

Brand voice cheatsheet: sardonic, classy, wry. Imagine a mob front that
became a jazz lounge. Speakeasy code-switching.

Posts to review:
""" + text_blob

    res = await call_profile("judge",
                              prompt=judge_prompt,
                              system_prompt="Return ONLY JSON: {\"accept\": bool, \"fixes\": [\"...\"]}",
                              temperature=0.1, response_format_json=True)
    content = res.get("content", {})
    if isinstance(content, str):
        import json
        try: content = json.loads(content)
        except: content = {"accept": False, "fixes": ["judge returned non-JSON"]}
    content.setdefault("fixes", [])
    return content


# ---- event-bus subscriber wiring ----

def register() -> None:
    from services.event_bus import subscribe

    async def _post_publish_handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        publishes = body.get("publish_output", {})
        posts = publishes.get("posts") if isinstance(publishes, dict) else None
        if not posts:
            return

        # STYLE_JUDGE gate
        verdict = await style_judge(posts)
        if not verdict.get("accept"):
            # Don't post — re-emit a rework envelope
            from services.event_bus import build_envelope, publish
            rework = build_envelope(
                route="R-02.REVENUE.PRODUCT_CREATED", stage="STYLE_JUDGE_REJECT",
                services_touched=["paulis-place"],
                blast_radius_usd=0.02,
                worker_profile="judge", worker_model=verdict.get("judge_model",""),
                body={"fixes": verdict.get("fixes",[])},
                next_action="REWORK_PUBLISHER",
            )
            await publish(rework)
            return

        # Publish to Zernio
        product_id = body.get("design_output", {}).get("product_id") or publishes.get("product_id") or "prd_unknown"
        result = await publish_pipeline(product_id=product_id, posts=posts)

        # Emit the lounge-scene event downstream
        from services.event_bus import build_envelope, publish
        env = build_envelope(
            route="R-02.REVENUE.PRODUCT_CREATED", stage="PUBLISH_DONE",
            services_touched=["paulis-place", "zernio"],
            blast_radius_usd=0.02,
            worker_profile="write_short", worker_model="zernio",
            body=result,
            next_action="LOUNGE_SCENE",
        )
        await publish(env)

    subscribe("R-02.REVENUE.PRODUCT_CREATED.PUBLISH", _post_publish_handler)