"""Governed Printify -> Etsy POD workflow for Pauli's Place.

The workflow persists each external identifier before moving to the next stage so
Celery/runtime retries cannot silently duplicate products or listings. Every
external write is capability-gated; final publish additionally requires a
persisted approval through the canonical pauli.approvals table.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from models.product import Product, ProductStatus
from services.capability_guard import CapabilityDecision, evaluate_capability
from services.etsy_service import etsy_service
from services.printify_service import printify_service


class PODWorkflowError(RuntimeError):
    pass


class PODWorkflowBlocked(PODWorkflowError):
    pass


@dataclass(frozen=True)
class PODDraftResult:
    operation_id: str
    printify_product_id: str
    etsy_listing_id: int
    approval_id: str
    status: str
    replayed: bool


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_allowed(db, task: dict[str, Any], capability: str, *, estimated_spend_cents: int = 0) -> CapabilityDecision:
    decision = evaluate_capability(
        db,
        task,
        capability,
        estimated_spend_cents=max(0, int(estimated_spend_cents)),
    )
    if not decision.allowed:
        raise PODWorkflowBlocked(f"{capability}: {decision.decision}: {decision.reason}")
    return decision


def _operation(db, organization_id, idempotency_key: str):
    return db.execute(
        text(
            """
            select * from pauli.commerce_operations
             where organization_id=:org and idempotency_key=:key
             limit 1
            """
        ),
        {"org": organization_id, "key": idempotency_key},
    ).mappings().first()


def _append_evidence(db, operation_id, evidence: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            update pauli.commerce_operations
               set evidence = evidence || cast(:evidence as jsonb), updated_at=now()
             where id=:id
            """
        ),
        {"id": operation_id, "evidence": json.dumps([evidence])},
    )


def _ensure_publish_approval(db, task: dict[str, Any], operation_id: str, source_product_id: int) -> str:
    existing = db.execute(
        text(
            """
            select id::text from pauli.approvals
             where organization_id=:org
               and mission_id=:mission
               and task_id=:task
               and action_class='commerce.publish.pod'
               and status in ('pending','approved','consumed')
             order by created_at desc
             limit 1
            """
        ),
        {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"]},
    ).scalar_one_or_none()
    if existing:
        return str(existing)

    approval_id = db.execute(
        text(
            """
            insert into pauli.approvals(
              organization_id,mission_id,task_id,requested_by_agent_id,
              action_class,risk_class,scope,max_uses,status,rationale
            ) values(
              :org,:mission,:task,:agent,'commerce.publish.pod','DANGEROUS',
              cast(:scope as jsonb),1,'pending',
              'Human approval required before a POD listing becomes publicly purchasable.'
            ) returning id::text
            """
        ),
        {
            "org": task["organization_id"],
            "mission": task["mission_id"],
            "task": task["id"],
            "agent": task.get("assigned_agent_id"),
            "scope": json.dumps({"commerce_operation_id": operation_id, "source_product_id": source_product_id}),
        },
    ).scalar_one()
    return str(approval_id)


class PODWorkflowService:
    async def prepare_draft(
        self,
        db,
        *,
        task: dict[str, Any],
        source_product_id: int,
        print_provider_id: int,
        printify_image_id: str,
        variant_ids: list[int],
        taxonomy_id: int,
        quantity: int = 999,
        estimated_spend_cents: int = 0,
        idempotency_key: str | None = None,
    ) -> PODDraftResult:
        product = db.query(Product).filter(Product.id == int(source_product_id)).first()
        if not product:
            raise PODWorkflowError(f"Product {source_product_id} was not found")
        if product.status not in {ProductStatus.DRAFT, ProductStatus.PENDING_APPROVAL, ProductStatus.APPROVED}:
            raise PODWorkflowBlocked(f"Product status {product.status.value} cannot enter POD draft workflow")
        if not product.title or not product.description or not product.price or float(product.price) <= 0:
            raise PODWorkflowBlocked("Product must have title, description, and positive price")

        blueprint_id = int(product.printify_blueprint_id or 0)
        variants = [int(v) for v in (variant_ids or product.printify_variant_ids or [])]
        if blueprint_id <= 0 or not variants or not printify_image_id or int(print_provider_id) <= 0:
            raise PODWorkflowBlocked("Verified Printify blueprint/provider/image/variant configuration is required")
        if int(taxonomy_id) <= 0:
            raise PODWorkflowBlocked("A verified Etsy taxonomy_id is required")

        input_manifest = {
            "source_product_id": int(source_product_id),
            "title": product.title,
            "price": float(product.price),
            "blueprint_id": blueprint_id,
            "print_provider_id": int(print_provider_id),
            "printify_image_id": str(printify_image_id),
            "variant_ids": variants,
            "taxonomy_id": int(taxonomy_id),
            "quantity": int(quantity),
        }
        input_hash = _canonical_hash(input_manifest)
        key = idempotency_key or f"pod-draft:{task['mission_id']}:{source_product_id}:{input_hash[:16]}"
        operation = _operation(db, task["organization_id"], key)
        replayed = operation is not None

        if operation and operation["input_hash"] != input_hash:
            raise PODWorkflowBlocked("Idempotency key was already used with different POD inputs")

        if not operation:
            operation = db.execute(
                text(
                    """
                    insert into pauli.commerce_operations(
                      organization_id,mission_id,task_id,source_product_id,operation_type,
                      idempotency_key,status,input_hash,evidence
                    ) values(
                      :org,:mission,:task,:product,'pod_draft',:key,'started',:hash,'[]'::jsonb
                    ) returning *
                    """
                ),
                {
                    "org": task["organization_id"],
                    "mission": task["mission_id"],
                    "task": task["id"],
                    "product": int(source_product_id),
                    "key": key,
                    "hash": input_hash,
                },
            ).mappings().one()
            db.commit()

        operation_id = str(operation["id"])
        printify_product_id = operation.get("printify_product_id")
        etsy_listing_id = operation.get("etsy_listing_id")

        try:
            if not printify_product_id:
                _require_allowed(db, task, "commerce.printify.create", estimated_spend_cents=estimated_spend_cents)
                created = await printify_service.create_product(
                    title=product.title,
                    description=product.description,
                    blueprint_id=blueprint_id,
                    print_provider_id=int(print_provider_id),
                    image_id=str(printify_image_id),
                    variant_ids=variants,
                    price_cents=int(round(float(product.price) * 100)),
                )
                printify_product_id = str(created["id"])
                db.execute(
                    text(
                        """
                        update pauli.commerce_operations
                           set printify_product_id=:external,status='printify_created',updated_at=now()
                         where id=:id
                        """
                    ),
                    {"external": printify_product_id, "id": operation_id},
                )
                _append_evidence(db, operation_id, {"stage": "printify_created", "product_id": printify_product_id})
                db.commit()

            if not etsy_listing_id:
                _require_allowed(db, task, "commerce.etsy.draft")
                draft = await etsy_service.create_pod_draft_listing(
                    title=product.title,
                    description=product.description,
                    price=float(product.price),
                    quantity=int(quantity),
                    taxonomy_id=int(taxonomy_id),
                    tags=list(product.tags or []),
                )
                etsy_listing_id = int(draft["listing_id"])
                db.execute(
                    text(
                        """
                        update pauli.commerce_operations
                           set etsy_listing_id=:listing,status='etsy_draft_created',updated_at=now()
                         where id=:id
                        """
                    ),
                    {"listing": etsy_listing_id, "id": operation_id},
                )
                _append_evidence(db, operation_id, {"stage": "etsy_draft_created", "listing_id": etsy_listing_id})
                db.commit()

            approval_id = _ensure_publish_approval(db, task, operation_id, int(source_product_id))
            db.execute(
                text(
                    """
                    update pauli.commerce_operations
                       set approval_id=cast(:approval as uuid),status='waiting_approval',updated_at=now()
                     where id=:id
                    """
                ),
                {"approval": approval_id, "id": operation_id},
            )
            product.status = ProductStatus.PENDING_APPROVAL
            product.research_data = {
                **(product.research_data or {}),
                "pod_operation_id": operation_id,
                "printify_product_id": printify_product_id,
                "etsy_listing_id": etsy_listing_id,
                "pod_input_hash": input_hash,
            }
            db.commit()
            return PODDraftResult(
                operation_id=operation_id,
                printify_product_id=str(printify_product_id),
                etsy_listing_id=int(etsy_listing_id),
                approval_id=approval_id,
                status="waiting_approval",
                replayed=replayed,
            )
        except Exception as exc:
            db.rollback()
            db.execute(
                text(
                    """
                    update pauli.commerce_operations
                       set status='failed',error_class=:klass,error_message=:message,updated_at=now()
                     where id=:id
                    """
                ),
                {"klass": type(exc).__name__, "message": str(exc)[:500], "id": operation_id},
            )
            db.commit()
            raise

    async def attach_etsy_image(self, db, *, task: dict[str, Any], operation_id: str, image_bytes: bytes) -> dict[str, Any]:
        operation = db.execute(
            text("select * from pauli.commerce_operations where id=cast(:id as uuid) for update"),
            {"id": operation_id},
        ).mappings().first()
        if not operation or not operation.get("etsy_listing_id"):
            raise PODWorkflowBlocked("POD operation has no Etsy draft listing")
        if operation.get("etsy_listing_image_id"):
            return {"listing_image_id": int(operation["etsy_listing_image_id"]), "replayed": True}
        _require_allowed(db, task, "commerce.etsy.image.upload")
        uploaded = await etsy_service.upload_listing_image(int(operation["etsy_listing_id"]), image_bytes)
        image_id = int(uploaded["listing_image_id"])
        db.execute(
            text("update pauli.commerce_operations set etsy_listing_image_id=:image,status='draft_ready',updated_at=now() where id=:id"),
            {"image": image_id, "id": operation_id},
        )
        _append_evidence(db, operation_id, {"stage": "etsy_image_uploaded", "listing_image_id": image_id})
        db.commit()
        return {"listing_image_id": image_id, "replayed": False}

    async def publish(self, db, *, task: dict[str, Any], operation_id: str) -> dict[str, Any]:
        operation = db.execute(
            text("select * from pauli.commerce_operations where id=cast(:id as uuid) for update"),
            {"id": operation_id},
        ).mappings().first()
        if not operation:
            raise PODWorkflowError("POD operation was not found")
        if operation["status"] == "published":
            return {"status": "published", "replayed": True, "operation_id": operation_id}
        if not operation.get("printify_product_id") or not operation.get("etsy_listing_id") or not operation.get("etsy_listing_image_id"):
            raise PODWorkflowBlocked("Printify product, Etsy draft, and Etsy image must all be verified before publish")

        _require_allowed(db, task, "commerce.publish.pod")
        db.execute(text("update pauli.commerce_operations set status='publishing',updated_at=now() where id=:id"), {"id": operation_id})
        db.commit()

        await printify_service.publish_product(str(operation["printify_product_id"]))
        _append_evidence(db, operation_id, {"stage": "printify_publish_requested", "product_id": operation["printify_product_id"]})
        db.commit()

        etsy_published = await etsy_service.publish_listing(int(operation["etsy_listing_id"]))
        etsy_verified = await etsy_service.get_listing(int(operation["etsy_listing_id"]))
        if str(etsy_verified.get("state", "")).lower() != "active":
            raise PODWorkflowBlocked("Etsy listing did not verify as active after publish")

        printify_verified = await printify_service.get_product(str(operation["printify_product_id"]))
        evidence = {
            "stage": "published_verified",
            "printify_product_id": str(operation["printify_product_id"]),
            "etsy_listing_id": int(operation["etsy_listing_id"]),
            "etsy_state": etsy_verified.get("state"),
            "etsy_url": etsy_verified.get("url") or etsy_published.get("url"),
            "printify_visible": printify_verified.get("visible"),
        }
        _append_evidence(db, operation_id, evidence)
        db.execute(
            text("update pauli.commerce_operations set status='published',completed_at=now(),updated_at=now() where id=:id"),
            {"id": operation_id},
        )
        product = db.query(Product).filter(Product.id == int(operation["source_product_id"])).first()
        if product:
            product.status = ProductStatus.PUBLISHED
            product.external_id = str(operation["etsy_listing_id"])
            product.research_data = {**(product.research_data or {}), "etsy_url": evidence.get("etsy_url")}
        db.commit()
        return {"status": "published", "replayed": False, "operation_id": operation_id, "evidence": evidence}


pod_workflow_service = PODWorkflowService()
