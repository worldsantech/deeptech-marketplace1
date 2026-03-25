from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    uploaded_by: int
    project_id: Optional[int] = None
    message_id: Optional[int] = None
    created_at: datetime