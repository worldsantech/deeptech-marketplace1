from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectActivityItem(BaseModel):
    event_id: str
    event_type: str
    happened_at: datetime

    actor_user_id: Optional[int] = None

    title: str
    description: Optional[str] = None

    entity_type: Optional[str] = None
    entity_id: Optional[int] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectActivityFeedResponse(BaseModel):
    project_id: int
    project_status: str
    total_events: int
    activities: List[ProjectActivityItem]