import asyncio
import base64
import uuid
import structlog
from app.tasks.celery_app import celery_app
from app.services.ingestion import process_document_ingestion

logger = structlog.get_logger()

@celery_app.task(name="app.tasks.ingestion.process_document_ingestion_task")
def process_document_ingestion_task(
    doc_id_str: str,
    user_id_str: str,
    filename: str,
    file_bytes_b64: str,
    mime_type: str
) -> None:
    """Celery task wrapper to process document text parsing, chunking, and embedding."""
    logger.info("celery_received_ingestion_task", doc_id=doc_id_str, filename=filename)
    
    doc_id = uuid.UUID(doc_id_str)
    user_id = uuid.UUID(user_id_str)
    file_bytes = base64.b64decode(file_bytes_b64)
    
    # Run the existing async service function in a new loop
    asyncio.run(process_document_ingestion(
        doc_id=doc_id,
        user_id=user_id,
        filename=filename,
        file_bytes=file_bytes,
        mime_type=mime_type
    ))
