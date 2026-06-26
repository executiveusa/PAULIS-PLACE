from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from models.base import get_db
from models.product import Product, Platform, ProductStatus, ProductType
from typing import Optional, List

router = APIRouter()


@router.get("/")
def list_products(
    platform: Optional[Platform] = None,
    status: Optional[ProductStatus] = None,
    niche: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List products with filters"""
    query = db.query(Product)

    if platform:
        query = query.filter(Product.platform == platform)
    if status:
        query = query.filter(Product.status == status)
    if niche:
        query = query.filter(Product.niche == niche)

    total = query.count()
    products = query.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [p.to_dict() for p in products]
    }


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get single product details"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()


@router.get("/{product_id}/image")
def get_product_image(product_id: int, db: Session = Depends(get_db)):
    """Get product image as base64"""
    from pathlib import Path
    import base64

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.design_image_path:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = Path(product.design_image_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    return {
        "base64": b64,
        "content_type": "image/png"
    }
