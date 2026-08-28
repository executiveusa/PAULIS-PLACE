"""Governed software factory authority for Pauli's Place.

This module does not become a second shell/Git/deployment runtime. It owns the
persistent contract around those actuators: one mission-bound operation, one
non-production branch, objective build/test/critic/guardian receipts, replay-safe
preview identity, and a separate human-approved production boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from services.capability_guard import CapabilityDecision, evaluate_capability, redact_secrets


class SoftwareFactoryError(RuntimeError):
    pass


class SoftwareFactoryBlocked(SoftwareFactoryError):
    pass


@dataclass(frozen=True)
class SoftwareOperation:
    id: str
    repository_full_name: str
    branch_ref: str | None
    status: str
    replayed: bool


_BRANCH_SAFE = re.compile(r"[^a-z0-9._-]+")
_PROTECTED_REFS = {"main", "master", "production", "prod"}


def canonical_hash(payload: Any) -> str:
    redacted = redact_secrets(payload)
    encoded = json.dumps(redacted, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_branch_ref(mission_id: str, slug: str) -> str:
    mission = re.sub(r"[^a-fA-F0-9]", "", str(mission_id))[:12].lower() or "mission"
    clean = _BRANCH_SAFE.sub("-", str(slug).strip().lower()).strip("-._")[:48] or "software-change"
    branch = f"pauli/{mission}/{clean}"
    validate_branch_ref(branch)
    return branch


def validate_branch_ref(branch_ref: str) -> str:
    value = str(branch_ref or "").strip()
    if not value or len(value) > 120:
        raise SoftwareFactoryBlocked("A bounded branch ref is required")
    normalized = value.lower().strip("/")
    if normalized in _PROTECTED_REFS or normalized.split("/")[-1] in _PROTECTED_REFS:
        raise SoftwareFactoryBlocked("Autonomous software work may not target a protected production branch")
    if ".." in value or "\\" in value or value.startswith("/") or value.endswith("/") or "//" in value:
        raise SoftwareFactoryBlocked("Unsafe branch ref")
    if not value.startswith("pauli/"):
        raise SoftwareFactoryBlocked("Autonomous branches must live under the pauli/ namespace")
    return value


def validate_command_argv(stage: str, argv: list[str]) -> list[str]:
    """Validate a bounded executor command without invoking a shell.

    Runtime/compute providers receive argv arrays. Shell strings, chaining and
    redirection are intentionally outside this contract.
    """
    allowed = {
        "install": {"npm", "pnpm", "yarn", "pip", "python", "python3"},
        "build": {"npm", "pnpm", "yarn", "python", "python3"},
        "test": {"npm", "pnpm", "yarn", "pytest", "python", "python3"},
    }
    if stage not in allowed or not argv or argv[0] not in allowed[stage]:
        raise SoftwareFactoryBlocked(f"Command is not allowed for software stage '{stage}'")
    forbidden = {";", "&&", "||", "|", ">", ">>", "<", "`", "$("}
    for part in argv:
        if any(marker in str(part) for marker in forbidden):
            raise SoftwareFactoryBlocked("Shell control syntax is not permitted in governed argv commands")
    return [str(part) for part in argv]


def _require_allowed(
    db,
    task: dict[str, Any],
    capability: str,
    *,
    estimated_spend_cents: int = 0,
) -> CapabilityDecision:
    decision = evaluate_capability(
        db,
        task,
        capability,
        estimated_spend_cents=max(0, int(estimated_spend_cents)),
    )
    if not decision.allowed:
        raise SoftwareFactoryBlocked(f"{capability}: {decision.decision}: {decision.reason}")
    return decision


def _operation(db, organization_id, idempotency_key: str):
    return db.execute(
        text(
            """
            select * from pauli.software_operations
             where organization_id=:org and idempotency_key=:key
             limit 1
            """
        ),
        {"org": organization_id, "key": idempotency_key},
    ).mappings().first()


def _receipt(db, operation: dict[str, Any], stage: str, status: str, summary: str, payload: dict[str, Any]) -> str:
    clean_payload = redact_secrets(payload or {})
    digest = canonical_hash({"stage": stage, "status": status, "summary": summary, "payload": clean_payload})
    db.execute(
        text(
            """
            insert into pauli.software_receipts(
              organization_id,operation_id,stage,status,sha256,summary,payload
            ) values(:org,cast(:operation as uuid),:stage,:status,:sha,:summary,cast(:payload as jsonb))
            on conflict (operation_id,stage,sha256) do nothing
            """
        ),
        {
            "org": operation["organization_id"],
            "operation": str(operation["id"]),
            "stage": stage,
            "status": status,
            "sha": digest,
            "summary": summary[:500],
            "payload": json.dumps(clean_payload),
        },
    )
    db.execute(
        text(
            """
            update pauli.software_operations
               set evidence=evidence || cast(:receipt as jsonb), updated_at=now()
             where id=cast(:id as uuid)
            """
        ),
        {
            "id": str(operation["id"]),
            "receipt": json.dumps([{"stage": stage, "status": status, "sha256": digest, "summary": summary[:240]}]),
        },
    )
    return digest


def _require_passed(receipt: dict[str, Any], label: str) -> None:
    if not receipt or receipt.get("passed") is not True or int(receipt.get("exit_code", 1)) != 0:
        raise SoftwareFactoryBlocked(f"{label} has not produced an objective passing receipt")


class SoftwareFactoryService:
    def begin_operation(
        self,
        db,
        *,
        task: dict[str, Any],
        repository_full_name: str,
        objective: str,
        acceptance_criteria: list[str],
        base_ref: str = "main",
        idempotency_key: str | None = None,
    ) -> SoftwareOperation:
        repository = str(repository_full_name or "").strip()
        if repository.count("/") != 1 or any(not part.strip() for part in repository.split("/")):
            raise SoftwareFactoryBlocked("repository_full_name must be owner/repository")
        if not objective.strip() or not acceptance_criteria or not all(str(x).strip() for x in acceptance_criteria):
            raise SoftwareFactoryBlocked("A structured objective and acceptance criteria are required before coding")

        manifest = {
            "repository_full_name": repository,
            "objective": objective.strip(),
            "acceptance_criteria": [str(x).strip() for x in acceptance_criteria],
            "base_ref": str(base_ref or "main").strip(),
        }
        input_hash = canonical_hash(manifest)
        key = idempotency_key or f"software-preview:{task['mission_id']}:{input_hash[:20]}"
        existing = _operation(db, task["organization_id"], key)
        if existing:
            if existing["input_hash"] != input_hash:
                raise SoftwareFactoryBlocked("Idempotency key is already bound to different software inputs")
            return SoftwareOperation(
                id=str(existing["id"]),
                repository_full_name=existing["repository_full_name"],
                branch_ref=existing.get("branch_ref"),
                status=existing["status"],
                replayed=True,
            )

        row = db.execute(
            text(
                """
                insert into pauli.software_operations(
                  organization_id,mission_id,task_id,idempotency_key,input_hash,
                  repository_full_name,base_ref,status,spec
                ) values(
                  :org,:mission,:task,:key,:hash,:repo,:base,'spec_ready',cast(:spec as jsonb)
                ) returning *
                """
            ),
            {
                "org": task["organization_id"],
                "mission": task["mission_id"],
                "task": task["id"],
                "key": key,
                "hash": input_hash,
                "repo": repository,
                "base": manifest["base_ref"],
                "spec": json.dumps(manifest),
            },
        ).mappings().one()
        _receipt(db, row, "spec", "passed", "Structured software acceptance spec recorded.", manifest)
        db.commit()
        return SoftwareOperation(str(row["id"]), repository, None, "spec_ready", False)

    def record_workspace(self, db, *, task: dict[str, Any], operation_id: str, workspace_ref: str) -> None:
        operation = self._locked(db, operation_id)
        if not str(workspace_ref or "").strip():
            raise SoftwareFactoryBlocked("A mission-bound isolated workspace reference is required")
        _require_allowed(db, task, "software.workspace.use")
        db.execute(
            text("update pauli.software_operations set workspace_ref=:workspace,status='workspace_ready',updated_at=now() where id=:id"),
            {"workspace": str(workspace_ref)[:500], "id": operation_id},
        )
        _receipt(db, operation, "workspace", "passed", "Isolated mission workspace recorded.", {"workspace_ref": workspace_ref})
        db.commit()

    def record_branch(
        self,
        db,
        *,
        task: dict[str, Any],
        operation_id: str,
        branch_ref: str,
        base_sha: str,
    ) -> None:
        operation = self._locked(db, operation_id)
        branch = validate_branch_ref(branch_ref)
        if not str(base_sha or "").strip():
            raise SoftwareFactoryBlocked("Verified base commit SHA is required before branch work")
        _require_allowed(db, task, "software.github.branch.write")
        db.execute(
            text(
                """
                update pauli.software_operations
                   set branch_ref=:branch,base_sha=:base,status='branch_ready',updated_at=now()
                 where id=:id
                """
            ),
            {"branch": branch, "base": str(base_sha), "id": operation_id},
        )
        _receipt(db, operation, "git_branch", "passed", "Governed non-production branch recorded.", {"branch_ref": branch, "base_sha": base_sha})
        db.commit()

    def record_commit(self, db, *, operation_id: str, commit_sha: str) -> None:
        operation = self._locked(db, operation_id)
        if not operation.get("branch_ref") or not str(commit_sha or "").strip():
            raise SoftwareFactoryBlocked("Branch and commit SHA are required")
        db.execute(
            text("update pauli.software_operations set commit_sha=:commit,status='building',updated_at=now() where id=:id"),
            {"commit": str(commit_sha), "id": operation_id},
        )
        db.commit()

    def record_build(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and int(clean.get("exit_code", 1)) == 0
        status = "passed" if passed else "failed"
        next_state = "building" if passed else "repairing"
        db.execute(
            text("update pauli.software_operations set build_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
            {"receipt": json.dumps(clean), "status": next_state, "id": operation_id},
        )
        digest = _receipt(db, operation, "build", status, "Build passed." if passed else "Build failed; repair required.", clean)
        db.commit()
        return digest

    def record_tests(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        _require_passed(operation.get("build_receipt") or {}, "Build")
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and int(clean.get("exit_code", 1)) == 0
        db.execute(
            text("update pauli.software_operations set test_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
            {"receipt": json.dumps(clean), "status": "verified" if passed else "tests_failed", "id": operation_id},
        )
        digest = _receipt(db, operation, "test", "passed" if passed else "failed", "Tests passed." if passed else "Tests failed; repair required.", clean)
        db.commit()
        return digest

    def record_critic(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        _require_passed(operation.get("build_receipt") or {}, "Build")
        _require_passed(operation.get("test_receipt") or {}, "Tests")
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and bool(clean.get("evidence"))
        db.execute(
            text("update pauli.software_operations set critic_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
            {"receipt": json.dumps(clean), "status": "verified" if passed else "repairing", "id": operation_id},
        )
        digest = _receipt(db, operation, "critic", "passed" if passed else "failed", "Independent critic accepted the real artifact." if passed else "Critic rejected the artifact; repair required.", clean)
        db.commit()
        return digest

    def record_guardian(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and bool(clean.get("evidence"))
        db.execute(
            text("update pauli.software_operations set guardian_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
            {"receipt": json.dumps(clean), "status": "verified" if passed else "repairing", "id": operation_id},
        )
        digest = _receipt(db, operation, "guardian", "passed" if passed else "failed", "Guardian accepted the evidence contract." if passed else "Guardian blocked completion.", clean)
        db.commit()
        return digest

    def record_preview(
        self,
        db,
        *,
        task: dict[str, Any],
        operation_id: str,
        provider: str,
        deployment_id: str,
        preview_url: str,
        estimated_spend_cents: int = 0,
    ) -> dict[str, Any]:
        operation = self._locked(db, operation_id)
        if operation.get("preview_deployment_id"):
            return {
                "operation_id": operation_id,
                "deployment_id": operation["preview_deployment_id"],
                "preview_url": operation.get("preview_url"),
                "replayed": True,
            }
        self._require_preview_ready(operation)
        _require_allowed(db, task, "software.preview.deploy", estimated_spend_cents=estimated_spend_cents)
        if not provider or not deployment_id or not str(preview_url).startswith("https://"):
            raise SoftwareFactoryBlocked("Verified preview provider, deployment id, and HTTPS URL are required")
        payload = {"provider": provider, "deployment_id": deployment_id, "preview_url": preview_url}
        db.execute(
            text(
                """
                update pauli.software_operations
                   set preview_provider=:provider,preview_deployment_id=:deployment,
                       preview_url=:url,status='preview_ready',updated_at=now(),completed_at=now()
                 where id=:id
                """
            ),
            {"provider": provider, "deployment": deployment_id, "url": preview_url, "id": operation_id},
        )
        _receipt(db, operation, "preview", "passed", "Preview deployment recorded and ready for external verification.", payload)
        db.commit()
        return {"operation_id": operation_id, "deployment_id": deployment_id, "preview_url": preview_url, "replayed": False}

    def request_production_approval(self, db, *, task: dict[str, Any], operation_id: str) -> str:
        operation = self._locked(db, operation_id)
        if operation.get("status") != "preview_ready" or not operation.get("preview_url"):
            raise SoftwareFactoryBlocked("A verified preview is required before production approval can be requested")
        existing = db.execute(
            text(
                """
                select id::text from pauli.approvals
                 where organization_id=:org and mission_id=:mission and task_id=:task
                   and action_class='software.production.deploy'
                   and status in ('pending','approved','consumed')
                 order by created_at desc limit 1
                """
            ),
            {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"]},
        ).scalar_one_or_none()
        if not existing:
            existing = db.execute(
                text(
                    """
                    insert into pauli.approvals(
                      organization_id,mission_id,task_id,requested_by_agent_id,
                      action_class,risk_class,scope,max_uses,status,rationale
                    ) values(
                      :org,:mission,:task,:agent,'software.production.deploy','DANGEROUS',
                      cast(:scope as jsonb),1,'pending',
                      'Human approval required before a software preview becomes a production deployment.'
                    ) returning id::text
                    """
                ),
                {
                    "org": task["organization_id"],
                    "mission": task["mission_id"],
                    "task": task["id"],
                    "agent": task.get("assigned_agent_id"),
                    "scope": json.dumps({"software_operation_id": operation_id, "preview_url": operation["preview_url"]}),
                },
            ).scalar_one()
        db.execute(
            text("update pauli.software_operations set production_approval_id=cast(:approval as uuid),status='waiting_production_approval',updated_at=now() where id=:id"),
            {"approval": existing, "id": operation_id},
        )
        db.commit()
        return str(existing)

    def _locked(self, db, operation_id: str):
        row = db.execute(
            text("select * from pauli.software_operations where id=cast(:id as uuid) for update"),
            {"id": operation_id},
        ).mappings().first()
        if not row:
            raise SoftwareFactoryError("Software operation was not found")
        return row

    @staticmethod
    def _require_preview_ready(operation: dict[str, Any]) -> None:
        if not operation.get("workspace_ref") or not operation.get("branch_ref") or not operation.get("commit_sha"):
            raise SoftwareFactoryBlocked("Workspace, governed branch, and commit are required before preview")
        _require_passed(operation.get("build_receipt") or {}, "Build")
        _require_passed(operation.get("test_receipt") or {}, "Tests")
        critic = operation.get("critic_receipt") or {}
        guardian = operation.get("guardian_receipt") or {}
        if critic.get("passed") is not True or not critic.get("evidence"):
            raise SoftwareFactoryBlocked("Independent critic has not accepted the artifact")
        if guardian.get("passed") is not True or not guardian.get("evidence"):
            raise SoftwareFactoryBlocked("Guardian has not accepted the evidence contract")


software_factory_service = SoftwareFactoryService()
