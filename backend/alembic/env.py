"""Alembic environment configuration."""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.base import Base
from models.product import Product  # noqa
from models.task import Task  # noqa
from models.trend import Trend  # noqa
from models.research import CompetitorProduct, NicheInsight  # noqa
from services.wiki_service import WikiEntry  # noqa
from agents.council_agent import CouncilDeliberation  # noqa
from services.payment_service import Payment  # noqa

config = context.config

# Override sqlalchemy.url with env var
db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
