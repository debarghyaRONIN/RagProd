import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.session import Session
from app.models.message import Message

async def create_chat_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str = "New Chat"
) -> Session:
    """Create a new chat session for a user."""
    session = Session(user_id=user_id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_user_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20
) -> List[Session]:
    """Retrieve paginated sessions for a user, sorted by updated_at descending."""
    offset = (page - 1) * limit
    stmt = (
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(desc(Session.updated_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_chat_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID
) -> Session | None:
    """Retrieve a specific chat session for a user."""
    stmt = select(Session).where(Session.id == session_id, Session.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def rename_chat_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str
) -> Session | None:
    """Rename a session's title."""
    session = await get_chat_session(db, session_id, user_id)
    if not session:
        return None
    session.title = title
    session.updated_at = datetime.now()
    await db.commit()
    await db.refresh(session)
    return session

async def delete_chat_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Delete a session (cascades to messages in Postgres)."""
    session = await get_chat_session(db, session_id, user_id)
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True

async def create_chat_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    sources: list | dict | None = None,
    token_count: int | None = None
) -> Message:
    """Save a chat message to a session and touch the session's updated_at timestamp."""
    # Create message
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources,
        token_count=token_count
    )
    db.add(message)
    
    # Touch session
    stmt = (
        update(Session)
        .where(Session.id == session_id)
        .values(updated_at=datetime.now())
    )
    await db.execute(stmt)
    
    await db.commit()
    await db.refresh(message)
    return message

async def get_session_messages_paginated(
    db: AsyncSession,
    session_id: uuid.UUID,
    cursor: str | None = None, # ISO created_at string
    limit: int = 50
) -> List[Message]:
    """
    Retrieve message history for a session using keyset (cursor-based) pagination.
    Returns messages sorted by created_at ascending.
    """
    stmt = select(Message).where(Message.session_id == session_id)
    
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(Message.created_at > cursor_dt)
        except ValueError:
            pass # Ignore invalid cursor
            
    stmt = stmt.order_by(Message.created_at.asc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
