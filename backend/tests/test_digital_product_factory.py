import pytest

from services.digital_product_factory import (
    DigitalProductBlocked,
    DigitalProductFactoryService,
    canonical_hash,
    safe_product_key,
    validate_package_manifest,
    validate_provenance,
)


def test_product_key_and_hash_are_deterministic_and_secret_safe():
    assert safe_product_key("Caregiver Planning Guide 2027") == "caregiver-planning-guide-2027"
    first = canonical_hash({"title": "Guide", "token": "secret-one"})
    second = canonical_hash({"token": "secret-two", "title": "Guide"})
    assert first == second
    assert len(first) == 64


def test_research_provenance_fails_closed_when_source_metadata_missing():
    valid = validate_provenance([
        {"source": "https://example.org/report", "claim": "Documented audience problem", "retrieved_at": "2026-08-27T00:00:00Z"}
    ])
    assert valid[0]["source"].startswith("https://")
    with pytest.raises(DigitalProductBlocked, match="source, claim, and retrieved_at"):
        validate_provenance([{"source": "https://example.org", "claim": "missing date"}])


def test_package_manifest_requires_real_hashed_files():
    manifest = validate_package_manifest({
        "version": "1.0.0",
        "title": "Real Guide",
        "format": "zip",
        "files": [{"name": "guide.pdf", "sha256": "a" * 64, "bytes": 1024}],
    })
    assert manifest["files"][0]["bytes"] == 1024
    with pytest.raises(DigitalProductBlocked):
        validate_package_manifest({"version": "1", "title": "Bad", "format": "zip", "files": []})


def test_sell_ready_contract_requires_quality_critic_guardian_and_package_hash():
    ready = {
        "quality_receipt": {"passed": True, "checks": ["files-open", "links-valid"]},
        "critic_receipt": {"passed": True, "evidence": ["artifact-reviewed"]},
        "guardian_receipt": {"passed": True, "evidence": ["acceptance-met"]},
        "package_sha256": "b" * 64,
    }
    DigitalProductFactoryService._require_sell_ready(ready)

    broken = {**ready, "quality_receipt": {"passed": False, "checks": ["files-open"]}}
    with pytest.raises(DigitalProductBlocked, match="quality"):
        DigitalProductFactoryService._require_sell_ready(broken)

    no_guardian = {**ready, "guardian_receipt": {"passed": False, "evidence": []}}
    with pytest.raises(DigitalProductBlocked, match="Guardian"):
        DigitalProductFactoryService._require_sell_ready(no_guardian)


def test_phase6_schema_has_replay_package_and_publish_approval_boundaries():
    path = "backend/supabase/migrations/20260827_pauli_digital_product_operations.sql"
    with open(path, "r", encoding="utf-8") as handle:
        sql = handle.read()
    assert "package_sha256" in sql
    assert "distribution_draft_id" in sql
    assert "publish_approval_id uuid references pauli.approvals" in sql
    assert "unique (organization_id, idempotency_key)" in sql


def test_public_activation_is_a_distinct_approval_action():
    path = "backend/services/digital_product_factory.py"
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "digital.listing.prepare" in source
    assert "digital.publish.activate" in source
    assert "Human approval required before a digital product becomes publicly purchasable." in source
