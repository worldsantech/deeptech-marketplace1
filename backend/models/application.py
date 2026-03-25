from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from backend.database.base import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    applicant_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    application_type = Column(String, nullable=False)  # engineer / factory
    cover_letter = Column(Text, nullable=True)
    proposed_budget = Column(Integer, nullable=True)
    estimated_timeline_days = Column(Integer, nullable=True)

    status = Column(String, nullable=False, default="submitted")  # submitted / shortlisted / accepted / rejected

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)