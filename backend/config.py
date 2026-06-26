import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://digifactory:changeme@localhost:5432/digifactory"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI
    openai_api_key: str = ""
    replicate_api_token: str = ""

    # Printify
    printify_shop_id: str = ""
    printify_token: str = ""

    # Etsy
    etsy_api_key: str = ""
    etsy_secret: str = ""
    etsy_access_token: str = ""
    etsy_refresh_token: str = ""

    # Fiverr
    fiverr_access_token: str = ""

    # OpenRouter (for multi-model routing)
    openrouter_api_key: str = ""
    app_url: str = "http://localhost:3000"

    # Payments (402 flow)
    creem_api_key: str = ""
    btcpay_api_url: str = ""
    btcpay_store_id: str = ""
    btcpay_api_key: str = ""

    # App
    secret_key: str = "changeme"
    environment: str = "development"

    # Paths
    generated_path: Path = Path("./generated")

    # Niche Configuration
    niches: list = [
        "anime",
        "stickers",
        "digital_assets",
        "thumbnails",
        "kawaii",
        "gaming",
        "aesthetic",
    ]

    # Human Gates
    auto_approve_design: bool = False
    auto_approve_listing: bool = False
    auto_publish: bool = False
    max_daily_spend: float = 5.0  # $5/day max (more aggressive)

    # Research settings
    max_research_iterations: int = 3
    max_searches_per_research: int = 15

    # Cost guards (more aggressive)
    max_cost_per_idea: float = 0.10  # $0.10 per idea
    max_cost_per_product: float = 0.25  # $0.25 per product creation

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


SETTINGS = get_settings()
