"""Seed initial niche configurations"""
from models.base import SessionLocal
from models.research import NicheInsight
from config import SETTINGS


def seed():
    db = SessionLocal()

    # Create empty niche insights for all configured niches
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
            print(f"Created niche: {niche}")

    db.commit()
    print("Seed complete!")


if __name__ == "__main__":
    seed()
