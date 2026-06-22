from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RetrievedChunk(BaseModel):
    id: int
    doc_id: str
    user_id: str
    chunk_index: int
    text: str
    source_page: int
    filename: str
    score: float

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query/question")
    doc_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs to scope the search to")
