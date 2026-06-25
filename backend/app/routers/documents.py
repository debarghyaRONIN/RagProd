import uuid
import base64
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_user
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentStatusResponse
from app.tasks.ingestion import process_document_ingestion_task
from app.milvus.schema import get_collection, get_user_partition_name
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/documents", tags=["Documents"])

# Mime type detector with signature fallbacks
def detect_mime_type(data: bytes, upload_mime: str | None = None) -> str:
    try:
        import magic
        return magic.from_buffer(data, mime=True)
    except Exception:
        # Fallback signature checks
        if data.startswith(b"%PDF"):
            return "application/pdf"
        elif data.startswith(b"PK\x03\x04"):
            # Check for docx zip file header
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif upload_mime:
            return upload_mime
        return "text/plain"

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document (PDF, DOCX, TXT, MD).
    Performs server-side type checks and size validation (Max 50MB).
    Launches chunking and embedding ingestion in the background via Celery.
    """
    # 1. Size check
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > 50 * 1024 * 1024:
        raise BadRequestException("File size exceeds the 50 MB limit")

    # 2. Type validation
    mime_type = detect_mime_type(file_bytes, file.content_type)
    allowed_mimes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/markdown"
    ]
    
    # Also support file extensions
    allowed_extensions = (".pdf", ".docx", ".doc", ".txt", ".md")
    has_allowed_extension = file.filename.lower().endswith(allowed_extensions)
    
    if mime_type not in allowed_mimes and not has_allowed_extension:
        raise BadRequestException(f"Unsupported file type: {mime_type}. Supported: PDF, DOCX, TXT, MD.")

    # 3. Create document record in PostgreSQL
    db_doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_size=file_size,
        mime_type=mime_type,
        status="pending"
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)

    # 4. Trigger ingestion background task via Celery
    file_bytes_b64 = base64.b64encode(file_bytes).decode("utf-8")
    process_document_ingestion_task.delay(
        doc_id_str=str(db_doc.id),
        user_id_str=str(current_user.id),
        filename=file.filename,
        file_bytes_b64=file_bytes_b64,
        mime_type=mime_type
    )

    return db_doc

@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents owned by the current user."""
    stmt = select(Document).where(Document.user_id == current_user.id).order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Poll ingestion status of a specific document."""
    stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    result = await db.execute(stmt)
    db_doc = result.scalars().first()
    if not db_doc:
        raise NotFoundException("Document not found")
    return db_doc

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document: cleans up PostgreSQL database row and its Milvus vectors."""
    stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    result = await db.execute(stmt)
    db_doc = result.scalars().first()
    if not db_doc:
        raise NotFoundException("Document not found")

    # Clean up Milvus vectors if present
    if db_doc.milvus_ids:
        try:
            collection = get_collection()
            partition_name = get_user_partition_name(str(current_user.id))
            # Milvus delete expression using the list of primary keys
            expr = f"id in [{', '.join(str(i) for i in db_doc.milvus_ids)}]"
            logger.info("deleting_vectors_from_milvus", doc_id=str(document_id), partition_name=partition_name, count=len(db_doc.milvus_ids))
            collection.delete(expr, partition_name=partition_name)
        except Exception as e:
            logger.error("milvus_vector_cleanup_failed", doc_id=str(document_id), error=str(e))
            # Proceed with PostgreSQL deletion anyway to prevent orphan entries in DB

    # Clean up DB row
    await db.delete(db_doc)
    await db.commit()
    return None
