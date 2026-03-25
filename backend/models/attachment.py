from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.database.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)

    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User")
    project = relationship("Project")
    message = relationship("Message")
    milestone = relationship("Milestone")