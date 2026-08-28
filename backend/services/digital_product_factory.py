"""Governed digital-product factory authority.

Designer/other agents create the content. This service owns provenance, immutable
artifact/package identity, quality gates, replay-safe listing drafts, and the
canonical approval boundary before any public sale activation.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from services.capability_guard import CapabilityDecision, evaluate_capability, redact_secrets


class DigitalProductError(RuntimeError):
    pass


class DigitalProductBlocked(DigitalProductError):
    pass


@dataclass(frozen=True)
class DigitalProductOperation:
    id: str
    product_key: str
    status: str
    replayed: bool


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(redact_secrets(payload), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_product_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9._-]+", "-", str(value or "").strip().lower()).strip("-._")[:80]
    if not key:
        raise DigitalProductBlocked("A stable product key is required")
    return key


def validate_provenance(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        raise DigitalProductBlocked("Research provenance is required before artifact completion")
    cleaned: list[dict[str, Any]] = []
    for item in items:
        source = str(item.get("source") or "").strip()
        claim = str(item.get("claim") or "").strip()
        retrieved_at = str(item.get("retrieved_at") or "").strip()
        if not source or not claim or not retrieved_at:
            raise DigitalProductBlocked("Each research item requires source, claim, and retrieved_at")
        cleaned.append(redact_secrets({**item, "source": source, "claim": claim, "retrieved_at": retrieved_at}))
    return cleaned


def validate_package_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    required = {"version", "files", "title", "format"}
    missing = sorted(required - set(manifest or {}))
    if missing:
        raise DigitalProductBlocked(f"Package manifest is incomplete: {', '.join(missing)}")
    if not str(manifest["version"]).strip() or not str(manifest["title"]).strip() or not str(manifest["format"]).strip():
        raise DigitalProductBlocked("Package version, title, and format must be non-empty")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise DigitalProductBlocked("Package must contain at least one real file")
    for file in files:
        if not isinstance(file, dict) or not file.get("name") or not file.get("sha256") or int(file.get("bytes", 0)) <= 0:
            raise DigitalProductBlocked("Each package file requires name, sha256, and positive byte size")
    return redact_secrets(manifest)


def _require_allowed(db, task: dict[str, Any], capability: str, *, estimated_spend_cents: int = 0) -> CapabilityDecision:
    decision = evaluate_capability(db, task, capability, estimated_spend_cents=max(0, int(estimated_spend_cents)))
    if not decision.allowed:
        raise DigitalProductBlocked(f"{capability}: {decision.decision}: {decision.reason}")
    return decision


def _receipt(db, operation: dict[str, Any], stage: str, status: str, summary: str, payload: dict[str, Any]) -> str:
    clean = redact_secrets(payload or {})
    digest = canonical_hash({"stage": stage, "status": status, "summary": summary, "payload": clean})
    db.execute(
        text(
            """
            insert into pauli.digital_product_receipts(
              organization_id,operation_id,stage,status,sha256,summary,payload
            ) values(:org,cast(:operation as uuid),:stage,:status,:sha,:summary,cast(:payload as jsonb))
            on conflict (operation_id,stage,sha256) do nothing
            """
        ),
        {"org": operation["organization_id"], "operation": str(operation["id"]), "stage": stage,
         "status": status, "sha": digest, "summary": summary[:500], "payload": json.dumps(clean)},
    )
    db.execute(
        text("update pauli.digital_product_operations set evidence=evidence || cast(:evidence as jsonb),updated_at=now() where id=:id"),
        {"id": str(operation["id"]), "evidence": json.dumps([{"stage": stage, "status": status, "sha256": digest, "summary": summary[:240]}])},
    )
    return digest


class DigitalProductFactoryService:
    def begin(
        self, db, *, task: dict[str, Any], product_key: str, product_type: str,
        audience: str, problem: str, offer: str, acceptance_criteria: list[str],
        idempotency_key: str | None = None,
    ) -> DigitalProductOperation:
        key = safe_product_key(product_key)
        if not all(str(v).strip() for v in (product_type, audience, problem, offer)) or not acceptance_criteria:
            raise DigitalProductBlocked("Product type, audience, problem, offer, and acceptance criteria are required")
        brief = {"product_key": key, "product_type": product_type, "audience": audience, "problem": problem,
                 "offer": offer, "acceptance_criteria": [str(x).strip() for x in acceptance_criteria if str(x).strip()]}
        input_hash = canonical_hash(brief)
        idem = idempotency_key or f"digital-product:{task['mission_id']}:{key}:{input_hash[:16]}"
        existing = db.execute(text("select * from pauli.digital_product_operations where organization_id=:org and idempotency_key=:key limit 1"),
                              {"org": task["organization_id"], "key": idem}).mappings().first()
        if existing:
            if existing["input_hash"] != input_hash:
                raise DigitalProductBlocked("Idempotency key is already bound to different product inputs")
            return DigitalProductOperation(str(existing["id"]), existing["product_key"], existing["status"], True)
        row = db.execute(
            text("""
            insert into pauli.digital_product_operations(
              organization_id,mission_id,task_id,idempotency_key,input_hash,product_key,product_type,status,brief
            ) values(:org,:mission,:task,:idem,:hash,:product,:type,'brief_ready',cast(:brief as jsonb)) returning *
            """),
            {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"], "idem": idem,
             "hash": input_hash, "product": key, "type": product_type, "brief": json.dumps(redact_secrets(brief))},
        ).mappings().one()
        _receipt(db, row, "brief", "passed", "Digital product brief recorded before generation.", brief)
        db.commit()
        return DigitalProductOperation(str(row["id"]), key, "brief_ready", False)

    def record_research(self, db, *, operation_id: str, provenance: list[dict[str, Any]]) -> str:
        operation = self._locked(db, operation_id)
        clean = validate_provenance(provenance)
        db.execute(text("update pauli.digital_product_operations set research_provenance=cast(:research as jsonb),status='research_ready',updated_at=now() where id=:id"),
                   {"research": json.dumps(clean), "id": operation_id})
        digest = _receipt(db, operation, "research", "passed", "Research provenance recorded.", {"sources": clean})
        db.commit()
        return digest

    def record_artifact(self, db, *, operation_id: str, artifact_manifest: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        if not operation.get("research_provenance"):
            raise DigitalProductBlocked("Research provenance must be recorded before artifact completion")
        manifest = redact_secrets(artifact_manifest or {})
        if not manifest.get("artifact_type") or not manifest.get("path") or int(manifest.get("bytes", 0)) <= 0:
            raise DigitalProductBlocked("Artifact manifest requires artifact_type, path, and positive byte size")
        digest = canonical_hash(manifest)
        db.execute(text("update pauli.digital_product_operations set artifact_manifest=cast(:manifest as jsonb),artifact_sha256=:sha,status='artifact_ready',updated_at=now() where id=:id"),
                   {"manifest": json.dumps(manifest), "sha": digest, "id": operation_id})
        _receipt(db, operation, "artifact", "passed", "Real artifact manifest recorded.", {**manifest, "sha256": digest})
        db.commit()
        return digest

    def record_package(self, db, *, operation_id: str, package_manifest: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        if not operation.get("artifact_sha256"):
            raise DigitalProductBlocked("Artifact must exist before packaging")
        manifest = validate_package_manifest(package_manifest)
        digest = canonical_hash(manifest)
        db.execute(text("update pauli.digital_product_operations set package_manifest=cast(:manifest as jsonb),package_sha256=:sha,status='package_validating',updated_at=now() where id=:id"),
                   {"manifest": json.dumps(manifest), "sha": digest, "id": operation_id})
        _receipt(db, operation, "package", "passed", "Versioned package manifest recorded.", {**manifest, "package_sha256": digest})
        db.commit()
        return digest

    def record_quality(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        if not operation.get("package_sha256"):
            raise DigitalProductBlocked("Package must exist before quality validation")
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and bool(clean.get("checks"))
        db.execute(text("update pauli.digital_product_operations set quality_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
                   {"receipt": json.dumps(clean), "status": "quality_verified" if passed else "repairing", "id": operation_id})
        digest = _receipt(db, operation, "quality", "passed" if passed else "failed", "Package quality checks passed." if passed else "Package quality failed; repair required.", clean)
        db.commit()
        return digest

    def record_critic(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        self._require_quality(operation)
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and bool(clean.get("evidence"))
        db.execute(text("update pauli.digital_product_operations set critic_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
                   {"receipt": json.dumps(clean), "status": "quality_verified" if passed else "repairing", "id": operation_id})
        digest = _receipt(db, operation, "critic", "passed" if passed else "failed", "Independent critic accepted the packaged artifact." if passed else "Critic rejected package; repair required.", clean)
        db.commit()
        return digest

    def record_guardian(self, db, *, operation_id: str, receipt: dict[str, Any]) -> str:
        operation = self._locked(db, operation_id)
        self._require_quality(operation)
        clean = redact_secrets(receipt or {})
        passed = clean.get("passed") is True and bool(clean.get("evidence"))
        db.execute(text("update pauli.digital_product_operations set guardian_receipt=cast(:receipt as jsonb),status=:status,updated_at=now() where id=:id"),
                   {"receipt": json.dumps(clean), "status": "quality_verified" if passed else "repairing", "id": operation_id})
        digest = _receipt(db, operation, "guardian", "passed" if passed else "failed", "Guardian accepted sell-ready evidence." if passed else "Guardian blocked completion.", clean)
        db.commit()
        return digest

    def record_listing_draft(
        self, db, *, task: dict[str, Any], operation_id: str, provider: str,
        draft_id: str, distribution_ref: str, estimated_spend_cents: int = 0,
    ) -> dict[str, Any]:
        operation = self._locked(db, operation_id)
        if operation.get("distribution_draft_id"):
            return {"draft_id": operation["distribution_draft_id"], "distribution_ref": operation.get("distribution_ref"), "replayed": True}
        self._require_sell_ready(operation)
        _require_allowed(db, task, "digital.listing.prepare", estimated_spend_cents=estimated_spend_cents)
        if not provider or not draft_id or not distribution_ref:
            raise DigitalProductBlocked("Distribution provider, draft id, and reference are required")
        payload = {"provider": provider, "draft_id": draft_id, "distribution_ref": distribution_ref}
        db.execute(text("""
            update pauli.digital_product_operations
               set distribution_provider=:provider,distribution_draft_id=:draft,distribution_ref=:ref,
                   status='listing_draft_ready',updated_at=now() where id=:id
        """), {"provider": provider, "draft": draft_id, "ref": distribution_ref, "id": operation_id})
        _receipt(db, operation, "listing_draft", "passed", "Sell-ready distribution draft recorded without public activation.", payload)
        db.commit()
        return {**payload, "replayed": False}

    def request_publish_approval(self, db, *, task: dict[str, Any], operation_id: str) -> str:
        operation = self._locked(db, operation_id)
        if operation.get("status") != "listing_draft_ready" or not operation.get("distribution_draft_id"):
            raise DigitalProductBlocked("A verified listing/delivery draft is required before publish approval")
        existing = db.execute(text("""
            select id::text from pauli.approvals
             where organization_id=:org and mission_id=:mission and task_id=:task
               and action_class='digital.publish.activate' and status in ('pending','approved','consumed')
             order by created_at desc limit 1
        """), {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"]}).scalar_one_or_none()
        if not existing:
            existing = db.execute(text("""
                insert into pauli.approvals(
                  organization_id,mission_id,task_id,requested_by_agent_id,action_class,risk_class,
                  scope,max_uses,status,rationale
                ) values(:org,:mission,:task,:agent,'digital.publish.activate','DANGEROUS',cast(:scope as jsonb),1,'pending',
                  'Human approval required before a digital product becomes publicly purchasable.') returning id::text
            """), {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"],
                     "agent": task.get("assigned_agent_id"), "scope": json.dumps({"digital_product_operation_id": operation_id,
                     "distribution_draft_id": operation["distribution_draft_id"]})}).scalar_one()
        db.execute(text("update pauli.digital_product_operations set publish_approval_id=cast(:approval as uuid),status='waiting_publish_approval',updated_at=now() where id=:id"),
                   {"approval": existing, "id": operation_id})
        db.commit()
        return str(existing)

    def _locked(self, db, operation_id: str):
        row = db.execute(text("select * from pauli.digital_product_operations where id=cast(:id as uuid) for update"), {"id": operation_id}).mappings().first()
        if not row:
            raise DigitalProductError("Digital product operation was not found")
        return row

    @staticmethod
    def _require_quality(operation: dict[str, Any]) -> None:
        receipt = operation.get("quality_receipt") or {}
        if receipt.get("passed") is not True or not receipt.get("checks"):
            raise DigitalProductBlocked("Objective package quality checks have not passed")

    @classmethod
    def _require_sell_ready(cls, operation: dict[str, Any]) -> None:
        cls._require_quality(operation)
        critic = operation.get("critic_receipt") or {}
        guardian = operation.get("guardian_receipt") or {}
        if critic.get("passed") is not True or not critic.get("evidence"):
            raise DigitalProductBlocked("Independent critic has not accepted the package")
        if guardian.get("passed") is not True or not guardian.get("evidence"):
            raise DigitalProductBlocked("Guardian has not accepted the package")
        if not operation.get("package_sha256"):
            raise DigitalProductBlocked("Versioned package identity is missing")


digital_product_factory_service = DigitalProductFactoryService()
