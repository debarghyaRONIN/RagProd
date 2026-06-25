from pydantic import BaseModel
import uuid
from datetime import datetime
from typing import List, Optional

class DocumentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: str
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
