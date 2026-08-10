from celery import Celery
from celery.schedules import crontab
from config import SETTINGS

app = Celery("paulis_place")
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
    imports=(
        'workers.tasks',
        'workers.boot_task',
        'workers.channel_ticks',
        'workers.mission_control',
        'workers.task_execution',
    ),
)

# Mission Control owns durable state. Task Execution claims only ready bounded
# work and requires provider evidence for actuator work.
app.conf.beat_schedule = {
    'pauli-mission-control': {
        'task': 'workers.mission_control.tick',
        'schedule': 5.0,
    },
    'pauli-task-execution': {
        'task': 'workers.task_execution.tick',
        'schedule': 3.0,
    },
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
    'score-hot-trends': {
        'task': 'workers.tasks.score_hot_trends',
        'schedule': crontab(hour='*/6', minute=30),
    },
    'weekly-niche-research': {
        'task': 'workers.tasks.research_all_niches',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),
    },
    'auto-create-products': {
        'task': 'workers.tasks.create_products_from_trends',
        'schedule': crontab(hour='*/3', minute=0),
    },
    'sync-metrics': {
        'task': 'workers.tasks.sync_product_metrics',
        'schedule': crontab(hour=3, minute=0),
    },
    'cost-guard': {
        'task': 'workers.tasks.check_daily_cost',
        'schedule': crontab(hour='*/1', minute=0),
    },
    'watcher-observation': {
        'task': 'workers.tasks.watcher_observation',
        'schedule': 30.0,
    },
    'watcher-analysis': {
        'task': 'workers.tasks.watcher_analysis',
        'schedule': 300.0,
    },
    'watcher-improvement': {
        'task': 'workers.tasks.watcher_improvement',
        'schedule': 3600.0,
    },
    'ch1-affiliate-morning': {
        'task': 'workers.channel_ticks.ch1_tick_task',
        'schedule': crontab(hour=8, minute=15),
    },
    'ch2-domains-daily': {
        'task': 'workers.channel_ticks.ch2_tick_task',
        'schedule': crontab(hour=9, minute=0),
    },
    'ch3-services-morning': {
        'task': 'workers.channel_ticks.ch3_tick_task',
        'schedule': crontab(hour=10, minute=30),
    },
    'ch4-microapps-afternoon': {
        'task': 'workers.channel_ticks.ch4_tick_task',
        'schedule': crontab(hour=13, minute=0),
    },
    'ch5-ebooks-evening': {
        'task': 'workers.channel_ticks.ch5_tick_task',
        'schedule': crontab(hour=17, minute=0),
    },
    'ch6-thrift-night': {
        'task': 'workers.channel_ticks.ch6_tick_task',
        'schedule': crontab(hour=21, minute=0),
    },
    'self-improve-nightly': {
        'task': 'workers.channel_ticks.self_improve_task',
        'schedule': crontab(hour=3, minute=0),
    },
}

if __name__ == '__main__':
    app.start()
