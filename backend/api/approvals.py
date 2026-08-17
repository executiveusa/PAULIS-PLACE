from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
from models.base import get_db
from models.product import Product, ProductStatus
from services.etsy_service import etsy_service
from services.printify_service import printify_service
from services.fiverr_service import fiverr_service
from services.approval_gate import verify_capability

router = APIRouter()


class ApprovalAction(BaseModel):
    product_ids: List[int]
    action: str  # approve | reject | publish


@router.get("/queue")
def get_approval_queue(db: Session = Depends(get_db)):
    """Read-only approval queue. Mutations require a separate scoped capability."""
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_pauli_approval: str | None = Header(default=None, alias="X-Pauli-Approval"),
):
    """Process an approval only with a server-signed, exact-scope capability.

    Caller-provided booleans or UI state are never authority. The capability is
    bound to the exact action and exact product IDs and expires quickly. If the
    server signing authority is not configured, this route fails closed.
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
            if product.status != ProductStatus.APPROVED:
                results.append({"id": product_id, "status": "error", "message": "Must be approved first"})
                continue
            background_tasks.add_task(publish_product, product.id)
            results.append({"id": product_id, "status": "publishing"})

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


async def publish_product(product_id: int):
    """Publish an already-approved product to its configured platform."""
    from models.base import SessionLocal
    db = SessionLocal()
    product = None

    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or product.status != ProductStatus.APPROVED:
            return

        if product.platform.value == "etsy":
            result = await etsy_service.create_listing(
                title=product.title,
                description=product.description,
                price=product.price,
                tags=product.tags,
                category_id=689,
            )
            product.external_id = str(result.get("listing_id", ""))

        elif product.platform.value == "printify":
            # Publishing remains intentionally fail-safe until a real uploaded
            # image and real variant selection are present. Never publish a
            # placeholder as if it were a finished commercial product.
            image_id = (product.research_data or {}).get("printify_image_id")
            variant_ids = (product.research_data or {}).get("printify_variant_ids") or []
            if not image_id or not variant_ids:
                raise RuntimeError("Printify product is missing verified image/variant configuration")
            result = await printify_service.create_product(
                title=product.title,
                description=product.description,
                blueprint_id=printify_service.BLUEPRINTS.get(product.product_type.value, 6),
                image_id=image_id,
                variant_ids=variant_ids,
                price=product.price,
                tags=product.tags,
            )
            product.external_id = result.get("id", "")

        elif product.platform.value == "fiverr":
            brief = fiverr_service.generate_gig_brief(product.to_dict())
            product.research_data = {**(product.research_data or {}), "fiverr_brief": brief}
            # Fiverr cannot be auto-published through this path; keep it approved.
            db.commit()
            return

        product.status = ProductStatus.PUBLISHED
        product.published_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        if product is not None:
            product.status = ProductStatus.FAILED
            product.research_data = {
                **(product.research_data or {}),
                "publish_error": f"{type(exc).__name__}: {str(exc)[:300]}",
            }
            db.commit()
        print(f"Publish error for {product_id}: {type(exc).__name__}: {str(exc)[:300]}")
    finally:
        db.close()
