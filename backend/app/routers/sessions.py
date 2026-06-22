import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db, get_current_user
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.session import (
    SessionResponse,
    MessageResponse,
    SessionRename,
    SessionDetailsResponse
)
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new chat session."""
    return await session_service.create_chat_session(db, current_user.id)

@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """List paginated chat sessions for the current user."""
    return await session_service.get_user_sessions(db, current_user.id, page, limit)

@router.get("/{session_id}", response_model=SessionDetailsResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get metadata and the last 50 messages for a specific session."""
    session = await session_service.get_chat_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundException("Chat session not found")
        
    messages = await session_service.get_session_messages_paginated(
        db, session_id, cursor=None, limit=50
    )
    return {"session": session, "messages": messages}

@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: uuid.UUID,
    body: SessionRename,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Rename a specific session's title."""
    session = await session_service.rename_chat_session(
        db, session_id, current_user.id, body.title
    )
    if not session:
        raise NotFoundException("Chat session not found")
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a specific session and its associated messages."""
    success = await session_service.delete_chat_session(db, session_id, current_user.id)
    if not success:
        raise NotFoundException("Chat session not found")
    return None

@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def list_session_messages(
    session_id: uuid.UUID,
    cursor: str | None = Query(None, description="Cursor timestamp (ISO format) for keyset pagination"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get cursor-based paginated message history for a specific session.
    Verifies that the session belongs to the current user before returning history.
    """
    session = await session_service.get_chat_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundException("Chat session not found")
        
    return await session_service.get_session_messages_paginated(
        db, session_id, cursor=cursor, limit=limit
    )
