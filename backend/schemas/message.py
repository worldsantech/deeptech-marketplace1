from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.attachment import AttachmentResponse


class MessageCreate(BaseModel):
    project_id: int = Field(..., ge=1)
    body: Optional[str] = Field(default=None, max_length=5000)
    recipient_user_id: Optional[int] = Field(default=None, ge=1)
    attachment_ids: List[int] = Field(default_factory=list)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    sender_user_id: int
    recipient_user_id: int
    body: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    attachments: List[AttachmentResponse] = Field(default_factory=list)


class ChatProjectInfo(BaseModel):
    id: int
    title: str
    status: str


class ChatUserInfo(BaseModel):
    id: int
    email: str
    role: str


class ChatLastMessageInfo(BaseModel):
    id: int
    body: Optional[str] = None
    sender_user_id: int
    created_at: datetime
    attachments_count: int = 0


class ChatListItemResponse(BaseModel):
    project: ChatProjectInfo
    other_user: ChatUserInfo
    last_message: Optional[ChatLastMessageInfo] = None
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int