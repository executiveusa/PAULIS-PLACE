"""
BOOT TASK - VPS Self-Boot Logic
================================
Programmatic boot task that can be triggered by Celery or run on startup.
Checks env, runs migrations, seeds DB, starts the money machine.
"""

import asyncio
import httpx
from datetime import datetime, timezone
from celery import shared_task
from models.base import Base, engine, SessionLocal
from models.research import NicheInsight
from config import SETTINGS
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def boot_system(self):
    """
    Zero-touch boot sequence.
    Called on VPS startup or manually via API.
    """
    logger.info("[BOOT] PAULI'S-PLACE boot sequence initiated")
    steps = []

    # Step 1: Create tables
    try:
        Base.metadata.create_all(bind=engine)
        steps.append({"step": "create_tables", "status": "ok"})
        logger.info("[BOOT] Tables created/verified")
    except Exception as e:
        steps.append({"step": "create_tables", "status": "failed", "error": str(e)})
        logger.error(f"[BOOT] Table creation failed: {e}")

    # Step 2: Seed niches
    try:
        _seed_niches()
        steps.append({"step": "seed_niches", "status": "ok"})
        logger.info("[BOOT] Niches seeded")
    except Exception as e:
        steps.append({"step": "seed_niches", "status": "failed", "error": str(e)})
        logger.error(f"[BOOT] Seed failed: {e}")

    # Step 3: Trigger first trend scan
    try:
        result = _trigger_endpoint("/api/trigger/scan-trends")
        steps.append({"step": "scan_trends", "status": "ok", "result": result})
        logger.info("[BOOT] First trend scan triggered")
    except Exception as e:
        steps.append({"step": "scan_trends", "status": "failed", "error": str(e)})
        logger.error(f"[BOOT] Trend scan trigger failed: {e}")

    # Step 4: Trigger trend scoring (after a delay)
    try:
        result = _trigger_endpoint("/api/trigger/score-trends")
        steps.append({"step": "score_trends", "status": "ok", "result": result})
        logger.info("[BOOT] Trend scoring triggered")
    except Exception as e:
        steps.append({"step": "score_trends", "status": "failed", "error": str(e)})

    logger.info("[BOOT] PAULI'S-PLACE IS LIVE. AWAITING OBSERVATION.")

    return {
        "status": "booted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": steps
    }


def _seed_niches():
    """Seed initial niche insights if not present"""
    db = SessionLocal()
    try:
        for niche in SETTINGS.niches:
            existing = db.query(NicheInsight).filter(NicheInsight.niche == niche).first()
            if not existing:
                insight = NicheInsight(
                    niche=niche,
                    avg_price=9.99,
                    total_products_analyzed=0,
                    top_keywords=[],
                    top_tags=[],
                    underserved_subniches=[],
                    product_type_distribution={}
                )
                db.add(insight)
                logger.info(f"[BOOT] Created niche: {niche}")
        db.commit()
    finally:
        db.close()


def _trigger_endpoint(path: str) -> dict:
    """Trigger a local API endpoint"""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(f"http://localhost:8000{path}")
            return response.json() if response.status_code in (200, 201) else {"error": response.status_code}
    except Exception as e:
        return {"error": str(e)}
