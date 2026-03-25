from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectProgressMilestoneItem(BaseModel):
    id: int
    title: str
    status: str
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    attachments_count: int = 0


class ProjectProgressSummaryResponse(BaseModel):
    project_id: int
    project_status: str

    total_milestones: int
    pending_milestones: int
    submitted_milestones: int
    approved_milestones: int
    changes_requested_milestones: int

    total_amount: float
    approved_amount: float
    remaining_amount: float

    completion_percentage: float

    has_pending_completion_request: bool
    completion_request_status: Optional[str] = None

    completed_milestones_count: int
    open_milestones_count: int

    last_milestone_activity_at: Optional[datetime] = None

    milestones: List[ProjectProgressMilestoneItem]