"""Spec §05 Zernio service tests (unit / mock — no network calls)."""
import asyncio
import sys
from pathlib import Path
from unittest import mock
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_zernio_module_imports():
    from services import zernio_service as zs
    assert hasattr(zs, "create_post")
    assert hasattr(zs, "publish_pipeline")
    assert hasattr(zs, "style_judge")
    assert hasattr(zs, "register")


def test_zernio_default_platforms_count():
    from services.zernio_service import DEFAULT_PLATFORMS
    assert len(DEFAULT_PLATFORMS) >= 15


def test_zernio_publish_pipeline_no_posts():
    from services.zernio_service import publish_pipeline
    res = asyncio.run(publish_pipeline(product_id="prd_test", posts=[]))
    assert res["platforms_attempted"] == []
    assert res["platforms_succeeded"] == []
    assert res["post_urls"] == {}
    assert res["product_id"] == "prd_test"


def test_zernio_publish_pipeline_one_mocked_post():
    from services import zernio_service as zs
    async def fake_create_post(**kwargs):
        return {"post_url": "https://x.com/example/123", "id": "post_1"}
    # Monkeypatch create_post and pre-flight
    real_create_post = zs.create_post
    zs.create_post = fake_create_post
    try:
        res = asyncio.run(zs.publish_pipeline(
            product_id="prd_test",
            posts=[{"platform":"x","text":"Hi","cta":"https://example.com"}],
        ))
        assert res["platforms_attempted"] == ["x"]
        assert res["platforms_succeeded"] == ["x"]
        assert res["post_urls"]["x"].endswith("/123")
        assert res["platforms_failed"] == []
    finally:
        zs.create_post = real_create_post


def test_zernio_publish_pipeline_captures_failures():
    from services import zernio_service as zs
    async def failing_create_post(**kwargs):
        raise RuntimeError("boom")
    real = zs.create_post
    zs.create_post = failing_create_post
    try:
        res = asyncio.run(zs.publish_pipeline(
            product_id="prd_test",
            posts=[{"platform":"x","text":"Hi"}],
        ))
        assert res["platforms_failed"] == [{"platform":"x","reason":"boom"}]
    finally:
        zs.create_post = real