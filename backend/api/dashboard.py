from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from models.base import get_db
from models.product import Product, Platform, ProductStatus
from models.task import Task, TaskStatus, TaskType
from models.trend import Trend
from models.research import NicheInsight
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregate dashboard statistics"""

    # Product stats
    total_products = db.query(func.count(Product.id)).scalar()
    published_products = db.query(func.count(Product.id)).filter(
        Product.status == ProductStatus.PUBLISHED
    ).scalar()
    pending_approval = db.query(func.count(Product.id)).filter(
        Product.status == ProductStatus.PENDING_APPROVAL
    ).scalar()

    # Revenue
    total_revenue = db.query(func.sum(Product.revenue)).scalar() or 0
    total_sales = db.query(func.sum(Product.sales)).scalar() or 0

    # Revenue by platform
    revenue_by_platform = db.query(
        Platform,
        func.sum(Product.revenue).label('revenue'),
        func.count(Product.id).label('count')
    ).group_by(Platform).all()

    # Recent sales (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_revenue = db.query(func.sum(Product.revenue)).filter(
        Product.published_at >= seven_days_ago
    ).scalar() or 0

    # Trend stats
    hot_trends = db.query(func.count(Trend.id)).filter(
        Trend.opportunity_score >= 60
    ).scalar()
    breakout_trends = db.query(func.count(Trend.id)).filter(
        Trend.is_breakout == True
    ).scalar()

    # Task stats
    running_tasks = db.query(func.count(Task.id)).filter(
        Task.status == TaskStatus.RUNNING
    ).scalar()
    failed_tasks = db.query(func.count(Task.id)).filter(
        Task.status == TaskStatus.FAILED
    ).scalar()

    return {
        "products": {
            "total": total_products,
            "published": published_products,
            "pending_approval": pending_approval,
            "drafts": total_products - published_products - pending_approval,
        },
        "revenue": {
            "total": total_revenue,
            "last_7_days": recent_revenue,
            "total_sales": total_sales,
            "by_platform": {
                p.value: {"revenue": r, "count": c}
                for p, r, c in revenue_by_platform
            }
        },
        "trends": {
            "hot": hot_trends,
            "breakout": breakout_trends,
        },
        "tasks": {
            "running": running_tasks,
            "failed": failed_tasks,
        }
    }


@router.get("/revenue-chart")
def get_revenue_chart(days: int = 30, db: Session = Depends(get_db)):
    """Get revenue data for chart"""
    # This would need a proper sales transaction table for real data
    # Placeholder returning product counts by creation date
    start_date = datetime.utcnow() - timedelta(days=days)

    products_by_day = db.query(
        func.date(Product.created_at).label('date'),
        func.count(Product.id).label('created'),
        func.sum(Product.revenue).label('revenue')
    ).filter(
        Product.created_at >= start_date
    ).group_by(
        func.date(Product.created_at)
    ).order_by(
        func.date(Product.created_at)
    ).all()

    return [
        {
            "date": str(d),
            "products_created": c,
            "revenue": r or 0
        }
        for d, c, r in products_by_day
    ]


@router.get("/niches")
def get_niche_overview(db: Session = Depends(get_db)):
    """Get overview of all niches"""
    niches = db.query(NicheInsight).all()
    return [n.to_dict() for n in niches]
