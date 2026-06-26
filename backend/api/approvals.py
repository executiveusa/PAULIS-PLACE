from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from models.base import get_db
from models.product import Product, ProductStatus
from services.etsy_service import etsy_service
from services.printify_service import printify_service
from services.fiverr_service import fiverr_service

router = APIRouter()


class ApprovalAction(BaseModel):
    product_ids: List[int]
    action: str  # "approve", "reject", "publish"


@router.get("/queue")
def get_approval_queue(db: Session = Depends(get_db)):
    """Get products pending approval"""
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
def process_approval(action: ApprovalAction, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Process approval actions"""
    results = []

    for product_id in action.product_ids:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            results.append({"id": product_id, "status": "error", "message": "Not found"})
            continue

        if action.action == "approve":
            product.status = ProductStatus.APPROVED
            product.approved_at = datetime.now(timezone.utc)
            product.approved_by = "user"
            results.append({"id": product_id, "status": "approved"})

        elif action.action == "reject":
            product.status = ProductStatus.FAILED
            results.append({"id": product_id, "status": "rejected"})

        elif action.action == "publish":
            if product.status != ProductStatus.APPROVED:
                results.append({"id": product_id, "status": "error", "message": "Must be approved first"})
                continue

            # Queue publish task
            background_tasks.add_task(publish_product, product.id)
            results.append({"id": product_id, "status": "publishing"})

    db.commit()
    return {"results": results}


async def publish_product(product_id: int):
    """Publish product to its platform"""
    from models.base import SessionLocal
    db = SessionLocal()

    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return

        if product.platform.value == "etsy":
            # Create listing on Etsy
            result = await etsy_service.create_listing(
                title=product.title,
                description=product.description,
                price=product.price,
                tags=product.tags,
                category_id=689  # Would need proper category mapping
            )
            product.external_id = str(result.get('listing_id', ''))

        elif product.platform.value == "printify":
            # Upload image and create product
            # This is simplified - would need image hosting
            result = await printify_service.create_product(
                title=product.title,
                description=product.description,
                blueprint_id=printify_service.BLUEPRINTS.get(product.product_type.value, 6),
                image_id="placeholder",  # Would need actual upload
                variant_ids=[],  # Would need to fetch variants
                price=product.price,
                tags=product.tags
            )
            product.external_id = result.get('id', '')

        elif product.platform.value == "fiverr":
            # Generate brief for manual creation
            brief = fiverr_service.generate_gig_brief(product.to_dict())
            product.research_data['fiverr_brief'] = brief
            # Can't auto-publish to Fiverr

        product.status = ProductStatus.PUBLISHED
        product.published_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        product.status = ProductStatus.FAILED
        db.commit()
        print(f"Publish error for {product_id}: {e}")
    finally:
        db.close()
