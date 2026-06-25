from app.tasks.celery_app import celery_app
from app.tasks.ingestion import process_document_ingestion_task

__all__ = ["celery_app", "process_document_ingestion_task"]
