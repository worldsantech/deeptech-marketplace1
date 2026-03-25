from pydantic import BaseModel
from datetime import datetime


class ConversationCreate(BaseModel):
    project_id: int
    client_user_id: int
    other_user_id: int


class ConversationResponse(BaseModel):
    id: int
    project_id: int
    client_user_id: int
    other_user_id: int
    conversation_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True