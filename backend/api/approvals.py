from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
from models.base import get_db
from models.product import Product, ProductStatus
from services.fiverr_service import fiverr_service
from services.approval_gate import verify_capability

router = APIRouter()


class ApprovalAction(BaseModel):
    product_ids: List[int]
    action: str  # approve | reject | publish


@router.get("/queue")
def get_approval_queue(db: Session = Depends(get_db)):
    """Read-only legacy product queue.

    Canonical consequential publish authority lives in `pauli.approvals` and
    `services.pod_workflow`. This endpoint remains for the owner product UI but
    may not directly publish POD products.
    """
    pending = db.query(Product).filter(
        Product.status == ProductStatus.PENDING_APPROVAL
    ).order_by(Product.created_at).all()

    approved = db.query(Product).filter(
        Product.status == ProductStatus.APPROVED
    ).order_by(Product.created_at).all()

    return {
        "pending": [p.to_dict() for p in pending],
        "ready_to_publish": [p.to_dict() for p in approved],
    }


@router.post("/action")
def process_approval(
    action: ApprovalAction,
    db: Session = Depends(get_db),
    x_pauli_approval: str | None = Header(default=None, alias="X-Pauli-Approval"),
):
    """Mutate the legacy Product record with an exact-scope signed capability.

    `approve` and `reject` remain supported for the old Product UI. POD `publish`
    is intentionally fail-closed here: public commerce publication must go
    through the replay-safe `pauli.commerce_operations` workflow and canonical
    `pauli.approvals` capability decision at the execution boundary.
    """
    if action.action not in {"approve", "reject", "publish"}:
        raise HTTPException(status_code=400, detail="Unsupported approval action")
    if not action.product_ids:
        raise HTTPException(status_code=400, detail="At least one product is required")
    if not x_pauli_approval:
        raise HTTPException(status_code=403, detail="Scoped approval capability required")

    capability = verify_capability(
        x_pauli_approval,
        expected_action=action.action,
        expected_resource_ids=action.product_ids,
    )

    results = []
    for product_id in action.product_ids:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            results.append({"id": product_id, "status": "error", "message": "Not found"})
            continue

        if action.action == "approve":
            if product.status != ProductStatus.PENDING_APPROVAL:
                results.append({"id": product_id, "status": "error", "message": "Product is not pending approval"})
                continue
            product.status = ProductStatus.APPROVED
            product.approved_at = datetime.now(timezone.utc)
            product.approved_by = capability.actor[:120]
            results.append({"id": product_id, "status": "approved"})

        elif action.action == "reject":
            if product.status not in {ProductStatus.PENDING_APPROVAL, ProductStatus.APPROVED}:
                results.append({"id": product_id, "status": "error", "message": "Product cannot be rejected from current state"})
                continue
            product.status = ProductStatus.FAILED
            results.append({"id": product_id, "status": "rejected"})

        elif action.action == "publish":
            if product.product_type.value == "fiverr_gig":
                if product.status != ProductStatus.APPROVED:
                    results.append({"id": product_id, "status": "error", "message": "Must be approved first"})
                    continue
                brief = fiverr_service.generate_gig_brief(product.to_dict())
                product.research_data = {**(product.research_data or {}), "fiverr_brief": brief}
                results.append({"id": product_id, "status": "brief_ready", "message": "Fiverr remains manual publish"})
                continue

            operation_id = (product.research_data or {}).get("pod_operation_id")
            if not operation_id:
                results.append({
                    "id": product_id,
                    "status": "blocked",
                    "message": "POD product has no governed commerce operation. Prepare the Printify/Etsy draft workflow first.",
                })
                continue
            results.append({
                "id": product_id,
                "status": "approval_required",
                "commerce_operation_id": operation_id,
                "message": "POD publish is controlled by canonical pauli.approvals and pod_workflow.publish; legacy direct publish is disabled.",
            })

    db.commit()
    return {
        "results": results,
        "approval_receipt": {
            "actor": capability.actor,
            "action": capability.action,
            "resource_ids": list(capability.resource_ids),
            "nonce": capability.nonce,
            "expires_at_unix": capability.exp,
        },
    }
