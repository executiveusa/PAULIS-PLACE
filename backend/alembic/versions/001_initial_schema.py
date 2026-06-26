"""Initial schema - all tables

Revision ID: 001
Revises:
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector extension (if available)
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    except Exception:
        pass  # Not critical - keyword search works as fallback

    # Products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('external_id', sa.String(), unique=True, nullable=True),
        sa.Column('platform', sa.Enum('etsy', 'printify', 'fiverr', name='platform')),
        sa.Column('product_type', sa.Enum('sticker', 'wall_art', 't_shirt', 'mug', 'phone_case',
                                          'thumbnail', 'template', 'digital_download', 'fiverr_gig',
                                          name='producttype')),
        sa.Column('title', sa.String(500)),
        sa.Column('description', sa.Text()),
        sa.Column('tags', sa.JSON(), default=list),
        sa.Column('niche', sa.String(100)),
        sa.Column('design_prompt', sa.Text()),
        sa.Column('design_image_path', sa.String(500)),
        sa.Column('variation_paths', sa.JSON(), default=list),
        sa.Column('thumbnail_path', sa.String(500)),
        sa.Column('price', sa.Float()),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('status', sa.Enum('draft', 'pending_approval', 'approved', 'published',
                                    'delisted', 'failed', name='productstatus'), default='draft'),
        sa.Column('requires_approval', sa.Boolean(), default=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('research_data', sa.JSON(), nullable=True),
        sa.Column('competitor_refs', sa.JSON(), default=list),
        sa.Column('views', sa.Integer(), default=0),
        sa.Column('clicks', sa.Integer(), default=0),
        sa.Column('sales', sa.Integer(), default=0),
        sa.Column('revenue', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('printify_blueprint_id', sa.String(100), nullable=True),
        sa.Column('printify_variant_ids', sa.JSON(), default=list),
    )

    # Tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('celery_id', sa.String(), unique=True, nullable=True),
        sa.Column('task_type', sa.Enum('trend_scan', 'research', 'design_generation', 'copy_generation',
                                       'listing_creation', 'publish', 'metrics_sync', name='tasktype')),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled',
                                    name='taskstatus'), default='pending'),
        sa.Column('input_data', sa.JSON(), default=dict),
        sa.Column('output_data', sa.JSON(), default=dict),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ai_tokens_used', sa.Integer(), default=0),
        sa.Column('ai_cost', sa.Float(), default=0.0),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('trend_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime()),
    )

    # Trends
    op.create_table(
        'trends',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('keyword', sa.String(500), index=True),
        sa.Column('niche', sa.String(100), index=True),
        sa.Column('interest_score', sa.Integer()),
        sa.Column('interest_history', sa.JSON(), default=list),
        sa.Column('change_7d', sa.Float(), default=0.0),
        sa.Column('change_30d', sa.Float(), default=0.0),
        sa.Column('related_queries', sa.JSON(), default=list),
        sa.Column('related_topics', sa.JSON(), default=list),
        sa.Column('opportunity_score', sa.Float(), default=0.0),
        sa.Column('competition_level', sa.String(50)),
        sa.Column('product_ideas', sa.JSON(), default=list),
        sa.Column('products_created', sa.Integer(), default=0),
        sa.Column('last_actioned_at', sa.DateTime(), nullable=True),
        sa.Column('is_breakout', sa.Boolean(), default=False),
        sa.Column('is_seasonal', sa.Boolean(), default=False),
        sa.Column('is_evergreen', sa.Boolean(), default=False),
        sa.Column('first_seen', sa.DateTime()),
        sa.Column('last_scanned', sa.DateTime()),
    )

    # Competitor Products
    op.create_table(
        'competitor_products',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('platform', sa.String(50)),
        sa.Column('external_id', sa.String(200)),
        sa.Column('url', sa.String(1000)),
        sa.Column('title', sa.String(500)),
        sa.Column('price', sa.Float()),
        sa.Column('currency', sa.String(10)),
        sa.Column('estimated_sales', sa.Integer()),
        sa.Column('estimated_revenue', sa.Float()),
        sa.Column('rating', sa.Float()),
        sa.Column('review_count', sa.Integer()),
        sa.Column('tags', sa.JSON(), default=list),
        sa.Column('design_analysis', sa.JSON(), default=dict),
        sa.Column('copy_analysis', sa.JSON(), default=dict),
        sa.Column('price_analysis', sa.JSON(), default=dict),
        sa.Column('key_patterns', sa.JSON(), default=list),
        sa.Column('replication_notes', sa.JSON(), default=dict),
        sa.Column('niche', sa.String(100)),
        sa.Column('scraped_at', sa.DateTime()),
    )

    # Niche Insights
    op.create_table(
        'niche_insights',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('niche', sa.String(100), unique=True, index=True),
        sa.Column('avg_price', sa.Float()),
        sa.Column('price_range', sa.JSON(), default=list),
        sa.Column('avg_rating', sa.Float()),
        sa.Column('total_products_analyzed', sa.Integer()),
        sa.Column('top_keywords', sa.JSON(), default=list),
        sa.Column('top_tags', sa.JSON(), default=list),
        sa.Column('color_palettes', sa.JSON(), default=list),
        sa.Column('style_keywords', sa.JSON(), default=list),
        sa.Column('title_patterns', sa.JSON(), default=list),
        sa.Column('underserved_subniches', sa.JSON(), default=list),
        sa.Column('pricing_gaps', sa.JSON(), default=list),
        sa.Column('content_gaps', sa.JSON(), default=list),
        sa.Column('product_type_distribution', sa.JSON(), default=dict),
        sa.Column('updated_at', sa.DateTime()),
    )

    # Wiki Entries
    op.create_table(
        'wiki_entries',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(500), nullable=False, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.String(1000)),
        sa.Column('embedding_id', sa.String(100), unique=True),
        sa.Column('category', sa.String(100), index=True),
        sa.Column('tags', sa.JSON(), default=list),
        sa.Column('niche', sa.String(100), index=True),
        sa.Column('source_type', sa.String(50)),
        sa.Column('source_url', sa.String(1000)),
        sa.Column('source_metadata', sa.JSON(), default=dict),
        sa.Column('confidence', sa.Float(), default=0.5),
        sa.Column('verified', sa.Integer(), default=0),
        sa.Column('outdated', sa.Integer(), default=0),
        sa.Column('related_entries', sa.JSON(), default=list),
        sa.Column('parent_entry_id', sa.Integer(), nullable=True),
        sa.Column('times_accessed', sa.Integer(), default=0),
        sa.Column('times_used_in_products', sa.Integer(), default=0),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # Council Deliberations
    op.create_table(
        'council_deliberations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('topic', sa.String(100), index=True),
        sa.Column('status', sa.String(50), default='deliberating'),
        sa.Column('problem_statement', sa.Text(), nullable=False),
        sa.Column('context', sa.JSON(), default=dict),
        sa.Column('debate_log', sa.JSON(), default=list),
        sa.Column('decision', sa.JSON(), nullable=True),
        sa.Column('ruling', sa.Text(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_result', sa.JSON(), nullable=True),
        sa.Column('total_cost', sa.Float(), default=0.0),
        sa.Column('turns', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # Payments
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('payment_id', sa.String(100), unique=True, index=True),
        sa.Column('external_id', sa.String(200), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('asset_type', sa.String(50)),
        sa.Column('asset_id', sa.String(200), nullable=True),
        sa.Column('provider', sa.String(50)),
        sa.Column('amount', sa.Float()),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('btc_address', sa.String(200), nullable=True),
        sa.Column('btc_amount', sa.Float(), nullable=True),
        sa.Column('btc_invoice_url', sa.String(1000), nullable=True),
        sa.Column('creem_checkout_url', sa.String(1000), nullable=True),
        sa.Column('customer_email', sa.String(200), nullable=True),
        sa.Column('metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('payments')
    op.drop_table('council_deliberations')
    op.drop_table('wiki_entries')
    op.drop_table('niche_insights')
    op.drop_table('competitor_products')
    op.drop_table('trends')
    op.drop_table('tasks')
    op.drop_table('products')
