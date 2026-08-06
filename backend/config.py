import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://digifactory:changeme@localhost:5432/digifactory"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI
    openai_api_key: str = ""
    replicate_api_token: str = ""
    anthropic_api_key: str = ""
    glm_api_key: str = ""
    deepseek_api_key: str = ""
    groq_api_key: str = ""
    moonshot_ai_api: str = ""
    huggingface_api_key: str = ""
    venice_api_key: str = ""
    minimax_api_key: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""

    # Model routing
    openrouter_api_key: str = ""
    omniroute_api_token: str = ""
    omniroute_base_url: str = ""
    litellm_base_url: str = ""
    litellm_master_key: str = ""

    # Yappyverse hard laws
    yappy_daily_spend_cap_usd: float = 25.0
    yappy_per_channel_cap_usd: float = 0.50
    yappy_human_approval_blast_radius_usd: float = 10.00

    # Trend / research
    firecrawl_api_token: str = ""
    bright_data_api: str = ""
    apify_api_key: str = ""
    trends_proxy: str = ""

    # Printify
    printify_shop_id: str = ""
    printify_token: str = ""

    # Etsy
    etsy_api_key: str = ""
    etsy_secret: str = ""
    etsy_access_token: str = ""
    etsy_refresh_token: str = ""
    etsy_shop_url: str = ""

    # Fiverr
    fiverr_access_token: str = ""

    # Payments
    creem_api_key: str = ""
    btcpay_api_url: str = ""
    btcpay_store_id: str = ""
    btcpay_api_key: str = ""
    stripe_secret_key: str = ""
    stripe_publishable: str = ""

    # Zernio
    zernio_api_token: str = ""

    # Self-improvement PR generation
    gh_pat: str = ""

    # Ops alerts
    telegram_bot_token: str = ""

    # Lounge / 3D world
    next_public_lounge_ws_url: str = "ws://localhost:8000/ws"
    readyplayerme_token: str = ""

    # Vercel
    vercel_api_key: str = ""
    vercel_token: str = ""

    # Hermes god agent (VPS)
    hermes_agent_api: str = ""
    hermes_vps_host: str = ""

    # Open Brain / memory
    open_brain_supabase_url: str = ""
    open_brain_supabase_key: str = ""

    # Extras
    fal_ai_api: str = ""
    eleven_labs_api: str = ""
    resend_api_token: str = ""

    app_url: str = "http://localhost:3000"

    # App
    secret_key: str = "changeme"
    environment: str = "development"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

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
    max_daily_spend: float = 25.0  # raised for finish run per human

    # Research settings
    max_research_iterations: int = 3
    max_searches_per_research: int = 15

    # Cost guards (more aggressive)
    max_cost_per_idea: float = 0.10
    max_cost_per_product: float = 0.25

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


SETTINGS = get_settings()
