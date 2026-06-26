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

    # App
    secret_key: str = "changeme"
    environment: str = "development"

    # Paths
    generated_path: Path = Path("/app/generated")

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
    max_daily_spend: float = 10.0  # AI cost guard

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


SETTINGS = get_settings()
