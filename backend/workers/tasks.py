import asyncio
from datetime import datetime, timezone
from workers.celery_app import app
from sqlalchemy.orm import Session
from models.base import SessionLocal
from models.task import Task, TaskType, TaskStatus
from models.trend import Trend
from models.product import Product, ProductStatus, ProductType
from models.research import NicheInsight
from services.trends_service import trends_service
from services.ai_service import ai_service
from agents.research_agent import research_agent
from agents.design_agent import design_agent
from config import SETTINGS


def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def create_task_record(db: Session, task_type: TaskType, input_data: dict = None) -> Task:
    """Create a task record for tracking"""
    task = Task(task_type=task_type, input_data=input_data or {})
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.task(bind=True, max_retries=3)
def scan_all_trends(self):
    """Scan all niches for trending keywords"""
    db = SessionLocal()
    task = create_task_record(db, TaskType.TREND_SCAN)
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        trends = run_async(trends_service.scan_all_niches(db))
        task.status = TaskStatus.COMPLETED
        task.output_data = {"trends_scanned": len(trends)}
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "success", "count": len(trends)}
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise self.retry(exc=e, countdown=60)


@app.task(bind=True)
def score_hot_trends(self):
    """Score trends that have data but no opportunity score"""
    db = SessionLocal()
    task = create_task_record(db, TaskType.RESEARCH)
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        # Get trends that need scoring
        unscored = db.query(Trend).filter(
            Trend.opportunity_score == 0,
            Trend.interest_score > 10
        ).limit(50).all()

        scored = 0
        for trend in unscored:
            # Get niche context
            insight = db.query(NicheInsight).filter(
                NicheInsight.niche == trend.niche
            ).first()

            market_context = insight.to_dict() if insight else {}

            assessment = run_async(ai_service.assess_trend_opportunity(
                keyword=trend.keyword,
                niche=trend.niche,
                trends_data={
                    "interest_score": trend.interest_score,
                    "change_7d": trend.change_7d,
                    "change_30d": trend.change_30d,
                    "related_queries": trend.related_queries[:10],
                    "is_breakout": trend.is_breakout,
                },
                market_context=market_context
            ))

            trend.opportunity_score = assessment.get('opportunity_score', 0)
            trend.competition_level = assessment.get('competition_score', {}).get('level', 'medium')
            trend.product_ideas = assessment.get('product_ideas', [])
            trend.is_seasonal = assessment.get('timing_score', {}).get('is_seasonal', False)
            trend.is_evergreen = assessment.get('timing_score', {}).get('is_evergreen', False)
            scored += 1

        db.commit()

        task.status = TaskStatus.COMPLETED
        task.output_data = {"trends_scored": scored}
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "success", "scored": scored}
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise


@app.task(bind=True)
def research_all_niches(self):
    """Deep research on all configured niches"""
    db = SessionLocal()
    task = create_task_record(db, TaskType.RESEARCH, {"niches": SETTINGS.niches})
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        results = {}
        for niche in SETTINGS.niches:
            insight = run_async(research_agent.research_niche(niche, db, max_products=50))
            if insight:
                results[niche] = insight.to_dict()

        task.status = TaskStatus.COMPLETED
        task.output_data = results
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "success", "niches_researched": len(results)}
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise


@app.task(bind=True)
def create_products_from_trends(self):
    """Auto-create products from high-scoring trends"""
    db = SessionLocal()
    task = create_task_record(db, TaskType.DESIGN_GENERATION)
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        # Cost guard check
        today_cost = ai_service.get_cost_today()
        if today_cost >= SETTINGS.max_daily_spend:
            task.status = TaskStatus.FAILED
            task.error_message = f"Daily cost limit reached: ${today_cost:.2f}"
            db.commit()
            return {"status": "blocked", "reason": "cost_limit"}

        # Get hot trends that haven't been over-saturated
        hot_trends = run_async(trends_service.get_hot_trends(db, min_score=65))

        created = 0
        for trend in hot_trends[:5]:  # Max 5 products per run
            if not trend.product_ideas:
                continue

            # Get niche insight
            insight = db.query(NicheInsight).filter(
                NicheInsight.niche == trend.niche
            ).first()

            # Take first product idea
            idea = trend.product_ideas[0]
            product_type = ProductType(idea.get('type', 'sticker'))

            try:
                product = run_async(design_agent.create_product_from_trend(
                    trend=trend,
                    niche_insight=insight,
                    product_type=product_type,
                    db=db
                ))
                created += 1
            except Exception as e:
                print(f"Error creating product for {trend.keyword}: {e}")
                continue

        task.status = TaskStatus.COMPLETED
        task.output_data = {"products_created": created, "ai_cost": ai_service.get_cost_today()}
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "success", "created": created}
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise


@app.task(bind=True)
def sync_product_metrics(self):
    """Sync sales/traffic metrics from platforms"""
    db = SessionLocal()
    task = create_task_record(db, TaskType.METRICS_SYNC)
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        # This would integrate with each platform's analytics API
        # For now, placeholder
        task.status = TaskStatus.COMPLETED
        task.output_data = {"synced": 0}
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "success"}
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise


@app.task(bind=True)
def check_daily_cost(self):
    """Cost guard - halt if over limit"""
    cost = ai_service.get_cost_today()

    if cost >= SETTINGS.max_daily_spend:
        # In production, would pause all task queues
        print(f"[COST GUARD] Daily limit reached: ${cost:.2f} / ${SETTINGS.max_daily_spend}")
        return {"status": "limit_reached", "cost": cost}

    return {"status": "ok", "cost": cost}
