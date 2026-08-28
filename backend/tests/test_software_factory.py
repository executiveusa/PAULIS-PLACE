import pytest

from services.software_factory import (
    SoftwareFactoryBlocked,
    SoftwareFactoryService,
    canonical_hash,
    safe_branch_ref,
    validate_branch_ref,
    validate_command_argv,
)


def test_canonical_hash_is_stable_and_redacts_secrets():
    first = canonical_hash({"b": 2, "a": 1, "api_key": "secret-one"})
    second = canonical_hash({"a": 1, "api_key": "different-secret", "b": 2})
    assert first == second
    assert len(first) == 64


def test_safe_branch_is_deterministic_and_not_production():
    one = safe_branch_ref("11111111-2222-3333-4444-555555555555", "Landing Page Repair")
    two = safe_branch_ref("11111111-2222-3333-4444-555555555555", "Landing Page Repair")
    assert one == two
    assert one.startswith("pauli/")
    assert one not in {"main", "master"}


@pytest.mark.parametrize("branch", ["main", "master", "pauli/test/main", "../escape", "pauli//bad", "/pauli/bad"])
def test_protected_or_unsafe_branch_refs_are_rejected(branch):
    with pytest.raises(SoftwareFactoryBlocked):
        validate_branch_ref(branch)


def test_governed_argv_accepts_direct_process_and_rejects_shell_chaining():
    assert validate_command_argv("test", ["python", "-m", "pytest", "-q"]) == ["python", "-m", "pytest", "-q"]
    with pytest.raises(SoftwareFactoryBlocked):
        validate_command_argv("build", ["npm", "run", "build", "&&", "rm", "-rf", "/"])


def test_preview_contract_requires_all_objective_receipts():
    operation = {
        "workspace_ref": "workspace://mission/task",
        "branch_ref": "pauli/111/software-change",
        "commit_sha": "abc123",
        "build_receipt": {"passed": True, "exit_code": 0},
        "test_receipt": {"passed": True, "exit_code": 0},
        "critic_receipt": {"passed": True, "evidence": ["artifact-review"]},
        "guardian_receipt": {"passed": True, "evidence": ["acceptance-check"]},
    }
    SoftwareFactoryService._require_preview_ready(operation)

    failed = {**operation, "test_receipt": {"passed": False, "exit_code": 1}}
    with pytest.raises(SoftwareFactoryBlocked, match="Tests"):
        SoftwareFactoryService._require_preview_ready(failed)

    missing_guardian = {**operation, "guardian_receipt": {"passed": False, "evidence": []}}
    with pytest.raises(SoftwareFactoryBlocked, match="Guardian"):
        SoftwareFactoryService._require_preview_ready(missing_guardian)


def test_phase5_schema_persists_preview_and_production_approval_boundaries():
    migration = "backend/supabase/migrations/20260827_pauli_software_operations.sql"
    with open(migration, "r", encoding="utf-8") as handle:
        sql = handle.read()
    assert "preview_deployment_id" in sql
    assert "production_approval_id uuid references pauli.approvals" in sql
    assert "software_receipts" in sql
    assert "unique (organization_id, idempotency_key)" in sql


def test_production_deployment_is_a_distinct_approval_action():
    path = "backend/services/software_factory.py"
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "software.production.deploy" in source
    assert "software.preview.deploy" in source
    assert "Human approval required before a software preview becomes a production deployment." in source
