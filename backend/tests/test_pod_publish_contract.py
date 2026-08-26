from services.pod_workflow import _canonical_hash


def test_publish_idempotency_manifest_changes_when_inputs_change():
    base = {
        "source_product_id": 7,
        "blueprint_id": 6,
        "print_provider_id": 99,
        "printify_image_id": "img-1",
        "variant_ids": [100, 101],
        "taxonomy_id": 123,
    }
    assert _canonical_hash(base) == _canonical_hash(dict(reversed(list(base.items()))))
    changed = {**base, "variant_ids": [100, 102]}
    assert _canonical_hash(base) != _canonical_hash(changed)


def test_phase4_publish_contract_persists_provider_completion_columns():
    migration = "backend/supabase/migrations/20260826_pauli_pod_operations.sql"
    with open(migration, "r", encoding="utf-8") as handle:
        sql = handle.read()
    assert "printify_published_at" in sql
    assert "etsy_published_at" in sql
    assert "approval_id uuid references pauli.approvals" in sql


def test_legacy_approval_route_has_no_direct_pod_provider_calls():
    path = "backend/api/approvals.py"
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "printify_service.create_product" not in source
    assert "etsy_service.create_listing" not in source
    assert "pod_workflow.publish" in source
