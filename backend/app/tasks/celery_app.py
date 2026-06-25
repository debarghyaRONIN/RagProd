from celery import Celery
from app.config import settings

celery_app = Celery(
    "ragqa_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Autodiscover tasks from the app.tasks package
celery_app.autodiscover_tasks(["app"])

# Config overrides
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
)
