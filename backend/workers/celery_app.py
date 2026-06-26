from celery import Celery
from celery.schedules import crontab
from config import SETTINGS

app = Celery('digifactory')
app.conf.update(
    broker_url=SETTINGS.redis_url,
    result_backend=SETTINGS.redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    imports=('workers.tasks', 'workers.boot_task'),
)

# Beat schedule - automated tasks
app.conf.beat_schedule = {
    # Trend scanning - 4x daily
    'scan-trends-morning': {
        'task': 'workers.tasks.scan_all_trends',
        'schedule': crontab(hour=6, minute=0),
    },
    'scan-trends-noon': {
        'task': 'workers.tasks.scan_all_trends',
        'schedule': crontab(hour=12, minute=0),
    },
    'scan-trends-evening': {
        'task': 'workers.tasks.scan_all_trends',
        'schedule': crontab(hour=18, minute=0),
    },
    'scan-trends-night': {
        'task': 'workers.tasks.scan_all_trends',
        'schedule': crontab(hour=0, minute=0),
    },

    # Score trends - after each scan
    'score-hot-trends': {
        'task': 'workers.tasks.score_hot_trends',
        'schedule': crontab(hour='*/6', minute=30),
    },

    # Research niches - weekly deep dive
    'weekly-niche-research': {
        'task': 'workers.tasks.research_all_niches',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2am
    },

    # Auto-create products from high-scoring trends
    'auto-create-products': {
        'task': 'workers.tasks.create_products_from_trends',
        'schedule': crontab(hour='*/3', minute=0),
    },

    # Sync metrics - daily
    'sync-metrics': {
        'task': 'workers.tasks.sync_product_metrics',
        'schedule': crontab(hour=3, minute=0),
    },

    # Cost guard check
    'cost-guard': {
        'task': 'workers.tasks.check_daily_cost',
        'schedule': crontab(hour='*/1', minute=0),
    },
}

if __name__ == '__main__':
    app.start()
