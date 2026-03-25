from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database.base import Base


class ProjectCompletionRequest(Base):
    __tablename__ = "project_completion_requests"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String, nullable=False, default="pending", index=True)

    provider_message = Column(Text, nullable=True)
    customer_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    resolved_at = Column(DateTime, nullable=True)

    project = relationship("Project")
    provider = relationship("User", foreign_keys=[provider_id])
    customer = relationship("User", foreign_keys=[customer_id])