import io
import re
import uuid
from typing import List, Tuple
import pdfplumber
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.future import select

from app.config import settings
from app.database import async_session_maker
from app.models.document import Document
from app.services.embedding import embed_texts
from app.milvus.schema import get_collection, get_user_partition_name
import structlog

logger = structlog.get_logger()

def clean_text(text: str) -> str:
    """Clean whitespace and common noise from text."""
    # Consolidate multiple spaces and tabs
    text = re.sub(r'[ \t]+', ' ', text)
    # Consolidate multiple newlines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    # Remove isolated page number lines like "Page 1 of 5" or "Page 2"
    text = re.sub(r'(?i)^\s*page\s+\d+\s*(of\s+\d+)?\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def parse_pdf(file_bytes: bytes) -> List[Tuple[int, str]]:
    """Extract page number and text pairs from a PDF file."""
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                pages.append((idx, text))
    return pages

def parse_docx(file_bytes: bytes) -> List[Tuple[int, str]]:
    """Extract paragraph content from Word document as a single page."""
    doc = docx.Document(io.BytesIO(file_bytes))
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text)
    # Treat DOCX as having 1 page containing all text
    return [(1, "\n".join(full_text))]

def parse_text(file_bytes: bytes) -> List[Tuple[int, str]]:
    """Extract text from plain text or markdown document as a single page."""
    text = file_bytes.decode("utf-8", errors="ignore")
    return [(1, text)]

async def update_progress(doc_id: uuid.UUID, progress: int, status: str = "processing", error_message: str | None = None) -> None:
    """Helper to update document status and progress in PostgreSQL."""
    async with async_session_maker() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        db_doc = result.scalars().first()
        if db_doc:
            db_doc.progress = progress
            db_doc.status = status
            if error_message is not None:
                db_doc.error_message = error_message
            await db.commit()

async def process_document_ingestion(
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
    mime_type: str
) -> None:
    """
    Background worker task to parse, clean, chunk, embed, and load a document.
    Now tracks and updates progress percentage in real time.
    """
    # Fix event loop / connection pool lifecycle issues when running Celery in Windows solo mode
    from app.database import engine
    from app.milvus.client import connect_milvus, disconnect_milvus
    
    logger.info("disposing_sqlalchemy_pool_for_new_loop")
    await engine.dispose()

    logger.info("reconnecting_milvus_for_new_loop")
    try:
        disconnect_milvus()
    except Exception:
        pass
    connect_milvus()

    logger.info("starting_document_ingestion", doc_id=str(doc_id), filename=filename)
    
    # 1. Update status to 'processing' and progress to 5%
    await update_progress(doc_id, 5, "processing")

    try:
        # 2. Parse text based on mime type or file extension
        lower_filename = filename.lower()
        if lower_filename.endswith(".pdf") or mime_type == "application/pdf":
            parsed_pages = parse_pdf(file_bytes)
        elif lower_filename.endswith(".docx") or mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ):
            parsed_pages = parse_docx(file_bytes)
        else:
            # Default to text parsing
            parsed_pages = parse_text(file_bytes)

        if not parsed_pages:
            raise Exception("No text content could be extracted from this document")

        # Parsing complete, set progress to 25%
        await update_progress(doc_id, 25)

        # 3. Clean and Split text chunk-by-chunk per page
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        chunks_to_embed = []
        for page_num, text in parsed_pages:
            cleaned = clean_text(text)
            if not cleaned:
                continue
            split_chunks = splitter.split_text(cleaned)
            for chunk in split_chunks:
                chunks_to_embed.append({
                    "text": chunk,
                    "source_page": page_num
                })

        if not chunks_to_embed:
            raise Exception("Document resulted in 0 text chunks after processing")

        logger.info("document_chunked", chunks_count=len(chunks_to_embed), doc_id=str(doc_id))

        # Chunking complete, set progress to 35%
        await update_progress(doc_id, 35)

        # 4. Batch embed text chunks with incremental progress updates
        chunk_texts = [c["text"] for c in chunks_to_embed]
        total_chunks = len(chunk_texts)
        embeddings = []
        
        # Batch size for embedding progress updates
        embed_batch_size = 32
        total_batches = (total_chunks + embed_batch_size - 1) // embed_batch_size

        for batch_idx in range(total_batches):
            start_i = batch_idx * embed_batch_size
            end_i = min(start_i + embed_batch_size, total_chunks)
            batch_texts = chunk_texts[start_i:end_i]
            
            # Embed this batch
            batch_embeddings = await embed_texts(batch_texts)
            embeddings.extend(batch_embeddings)
            
            # Embedding progress scales from 35% to 85%
            progress = 35 + int(((batch_idx + 1) / total_batches) * 50)
            await update_progress(doc_id, progress)
        
        if len(embeddings) != len(chunks_to_embed):
            raise Exception(f"Mismatch in embeddings output size. Expected {len(chunks_to_embed)}, got {len(embeddings)}")

        # Embedding complete, set progress to 90%
        await update_progress(doc_id, 90)

        # 5. Insert vectors into Milvus
        milvus_data = []
        for idx, chunk in enumerate(chunks_to_embed):
            milvus_data.append({
                "doc_id": str(doc_id),
                "user_id": str(user_id),
                "chunk_index": idx,
                "text": chunk["text"],
                "source_page": chunk["source_page"],
                "filename": filename,
                "embedding": embeddings[idx]
            })

        collection = get_collection()
        partition_name = get_user_partition_name(str(user_id))
        
        # Check if the user partition exists, create if not
        if not collection.has_partition(partition_name):
            logger.info("creating_user_milvus_partition", partition_name=partition_name)
            collection.create_partition(partition_name)
            
        # Insert vectors into user specific partition
        insert_result = collection.insert(milvus_data, partition_name=partition_name)
        milvus_primary_keys = list(insert_result.primary_keys)

        # Ensure collection is loaded
        collection.flush()
        
        logger.info(
            "milvus_insertion_complete",
            doc_id=str(doc_id),
            inserted_count=len(milvus_primary_keys)
        )

        # Milvus complete, set progress to 95%
        await update_progress(doc_id, 95)

        # 6. Update document in PostgreSQL status to 'ready' and progress to 100%
        async with async_session_maker() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            db_doc = result.scalars().first()
            if db_doc:
                db_doc.status = "ready"
                db_doc.progress = 100
                db_doc.chunk_count = len(chunks_to_embed)
                db_doc.milvus_ids = milvus_primary_keys # Save keys for delete cascade
                await db.commit()
                logger.info("document_ingestion_success", doc_id=str(doc_id))

    except Exception as e:
        logger.error("document_ingestion_failed", doc_id=str(doc_id), error=str(e))
        # Update document status to 'failed' and keep/record progress at failure point
        await update_progress(doc_id, progress=0, status="failed", error_message=str(e))

