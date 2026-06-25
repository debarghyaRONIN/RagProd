import uuid
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.config import settings
from app.core.dependencies import get_db, get_current_user
from app.core.middleware import limiter
from app.core.exceptions import NotFoundException, ForbiddenException, RateLimitException
from app.models.user import User
from app.models.message import Message
from app.schemas.chat import ChatRequest
from app.services import session_service, retrieval, generation
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["Chat"])

@router.post("/{session_id}/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    session_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RAG QA Chat Endpoint.
    Retrieves relevant passages, calls local vLLM, and streams SSE response.
    Saves message history to PostgreSQL database.
    """
    # 1. Verify session belongs to current_user
    session = await session_service.get_chat_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundException("Chat session not found")

    # Get existing message count to check if this is the first message
    count_stmt = select(func.count(Message.id)).where(Message.session_id == session_id)
    count_result = await db.execute(count_stmt)
    message_count = count_result.scalar() or 0

    # 2. Save the User's question to messages DB immediately
    user_msg = await session_service.create_chat_message(
        db=db,
        session_id=session_id,
        role="user",
        content=body.message
    )

    # Auto-generate session title if this is the first user query
    if message_count == 0:
        words = body.message.split()
        title_suggestion = " ".join(words[:6])
        if len(words) > 6:
            title_suggestion += "..."
        if not title_suggestion:
            title_suggestion = "New Chat"
        await session_service.rename_chat_session(db, session_id, current_user.id, title_suggestion)
        logger.info("auto_generated_session_title", session_id=str(session_id), title=title_suggestion)

    # 3. Retrieve chunks from Milvus
    # Use config top_k retrieval value
    retrieved_chunks = await retrieval.retrieve_chunks(
        query=body.message,
        user_id=str(current_user.id),
        top_k=settings.TOP_K_RETRIEVAL,
        doc_ids=body.doc_ids
    )

    # Load last 6 history turns for context
    history_messages = await session_service.get_session_messages_paginated(
        db=db,
        session_id=session_id,
        limit=6
    )

    # Prepare response formatter generator
    async def sse_response_generator():
        accumulated_response = ""
        sources_metadata = []

        # Yield sources metadata event first so the UI can render citations immediately
        sources_list = [
            {
                "id": chunk.id,
                "filename": chunk.filename,
                "source_page": chunk.source_page,
                "text": chunk.text,
                "score": chunk.score
            }
            for chunk in retrieved_chunks
        ]
        
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_list})}\n\n"

        # Stream LLM tokens
        try:
            # Use generation service to fetch tokens from vLLM
            async for token in generation.stream_answer(
                question=body.message,
                retrieved_chunks=retrieved_chunks,
                chat_history=history_messages
            ):
                if token.startswith("[SOURCES_METADATA]"):
                    sources_metadata = json.loads(token[18:])
                    continue
                elif token.startswith("[ERROR]"):
                    yield f"data: {json.dumps({'type': 'error', 'detail': token[7:]})}\n\n"
                    return
                
                accumulated_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # 4. Save accumulated Assistant response to Postgres database
            assistant_msg = await session_service.create_chat_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=accumulated_response,
                sources=sources_metadata or sources_list
            )

            # 5. Yield final done event
            yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_msg.id)})}\n\n"

        except Exception as e:
            logger.error("sse_generator_failed", session_id=str(session_id), error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Internal server streaming error'})}\n\n"

    return StreamingResponse(
        sse_response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in Nginx proxies
        }
    )
