from celery import Celery
from app.config.settings import settings

celery_app = Celery(
    "logistics_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker Overload Controls
    worker_concurrency=4,                # Prevent queue spikes from crashing nodes
    task_acks_late=True,                 # Requeue task if worker dies mid-execution
    worker_prefetch_multiplier=1,        # Fair distribution for slow AI tasks
    # Route specific heavy tasks to a separate AI queue
    task_routes={
        "app.workers.tasks.process_whatsapp_ai_request": {"queue": "heavy_ai"},
    }
)
