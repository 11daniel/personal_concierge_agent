from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class MessageCreate(BaseModel):
    text: str

class MessageResponse(BaseModel):
    id: int
    sender: str  # 'user' or 'assistant'
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatDetailResponse(SessionResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
