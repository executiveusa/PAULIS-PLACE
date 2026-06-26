import asyncio
from datetime import datetime, timedelta
from typing import Optional
from pytrends.request import TrendReq
from sqlalchemy.orm import Session
from models.trend import Trend
from config import SETTINGS


class TrendsService:
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        self.niche_keywords = {
            "anime": [
                "anime sticker", "anime wall art", "anime aesthetic", "anime girl",
                "anime poster", "kawaii anime", "dark anime", "cozy anime",
                "anime room decor", "itachi sticker", "gojo sticker", "naruto aesthetic"
            ],
            "stickers": [
                "aesthetic stickers", "laptop stickers", "water bottle stickers",
                "planner stickers", "kawaii stickers", "vintage stickers",
                "dark aesthetic stickers", "cute stickers", "funny stickers",
                "witchy stickers", "gamer stickers", "stan stickers"
            ],
            "digital_assets": [
                "digital planner", "canva template", "social media template",
                "notion template", "digital download", "printable art",
                "svg cut file", "digital paper", "procreate brush",
                "lightroom preset", "resume template"
            ],
            "thumbnails": [
                "youtube thumbnail", "gaming thumbnail", "course thumbnail",
                "podcast cover", "twitch overlay", "stream banner"
            ],
            "kawaii": [
                "kawaii aesthetic", "kawaii room", "kawaii decor", "kawaii sticker",
                "kawaii wallpaper", "pastel kawaii", "kawaii plush", "kawaii art"
            ],
            "gaming": [
                "gamer room decor", "gaming setup", "gaming wall art",
                "gamer sticker", "esports aesthetic", "retro gaming",
                "gaming mouse pad design", "streamer merch"
            ],
            "aesthetic": [
                "dark aesthetic", "cottagecore", "grunge aesthetic",
                "y2k aesthetic", "coastal grandmother", "minimalist aesthetic",
                "witchcore", "fairycore", "roycore"
            ]
        }

    async def scan_all_niches(self, db: Session) -> list[Trend]:
        """Scan all configured niches for trending keywords"""
        all_trends = []

        for niche, keywords in self.niche_keywords.items():
            # Process in batches of 5 (Google Trends limit)
            for i in range(0, len(keywords), 5):
                batch = keywords[i:i+5]
                trends = await self._scan_keywords(batch, niche, db)
                all_trends.extend(trends)
                await asyncio.sleep(1)  # Rate limiting

        return all_trends

    async def _scan_keywords(self, keywords: list, niche: str, db: Session) -> list[Trend]:
        """Scan a batch of keywords"""
        trends = []

        try:
            # Build payload
            self.pytrends.build_payload(
                kw_list=keywords,
                cat=0,
                timeframe='today 3-m',  # Last 90 days
                geo='',  # Worldwide
                gprop=''
            )

            # Get interest over time
            interest_df = self.pytrends.interest_over_time()

            # Get related queries
            related_queries = self.pytrends.related_queries()

            # Get related topics
            related_topics = self.pytrends.related_topics()

            for keyword in keywords:
                if keyword in interest_df.columns:
                    history = interest_df[keyword].tolist()
                    current = history[-1] if history else 0

                    # Calculate changes
                    change_7d = 0
                    change_30d = 0
                    if len(history) >= 7:
                        week_ago = history[-7]
                        if week_ago > 0:
                            change_7d = round((current - week_ago) / week_ago * 100, 1)
                    if len(history) >= 30:
                        month_ago = history[-30]
                        if month_ago > 0:
                            change_30d = round((current - month_ago) / month_ago * 100, 1)

                    # Get related queries for this keyword
                    rq = related_queries.get(keyword, {})
                    rising = rq.get('rising', [])
                    top = rq.get('top', [])
                    related = []
                    if rising is not None:
                        related.extend([r['query'] for r in rising.head(10).to_dict('records') if 'query' in r])
                    if top is not None:
                        related.extend([t['query'] for t in top.head(10).to_dict('records') if 'query' in t])

                    # Check for breakout
                    is_breakout = False
                    if rising is not None and len(rising) > 0:
                        is_breakout = any(r.get('value') == '<1' for r in rising.head(5).to_dict('records'))

                    # Update or create trend
                    existing = db.query(Trend).filter(
                        Trend.keyword == keyword,
                        Trend.niche == niche
                    ).first()

                    if existing:
                        existing.interest_score = current
                        existing.interest_history = history
                        existing.change_7d = change_7d
                        existing.change_30d = change_30d
                        existing.related_queries = related[:20]
                        existing.is_breakout = is_breakout
                        existing.last_scanned = datetime.utcnow()
                        trends.append(existing)
                    else:
                        trend = Trend(
                            keyword=keyword,
                            niche=niche,
                            interest_score=current,
                            interest_history=history,
                            change_7d=change_7d,
                            change_30d=change_30d,
                            related_queries=related[:20],
                            is_breakout=is_breakout
                        )
                        db.add(trend)
                        db.flush()
                        trends.append(trend)

        except Exception as e:
            print(f"Error scanning trends: {e}")
            # Wait and retry
            await asyncio.sleep(5)

        db.commit()
        return trends

    async def get_hot_trends(self, db: Session, min_score: float = 60) -> list[Trend]:
        """Get trends above opportunity score threshold"""
        return db.query(Trend).filter(
            Trend.opportunity_score >= min_score,
            Trend.products_created < 3  # Don't over-saturate
        ).order_by(Trend.opportunity_score.desc()).limit(20).all()

    async def get_breakout_trends(self, db: Session) -> list[Trend]:
        """Get newly breakout trends"""
        return db.query(Trend).filter(
            Trend.is_breakout == True,
            Trend.interest_score > 20
        ).order_by(Trend.last_scanned.desc()).limit(10).all()


trends_service = TrendsService()
