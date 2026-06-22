from pydantic import BaseModel
import uuid
from datetime import datetime
from typing import List, Optional, Any

class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    sources: Optional[Any] = None
    token_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SessionRename(BaseModel):
    title: str

class SessionDetailsResponse(BaseModel):
    session: SessionResponse
    messages: List[MessageResponse]
