from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from backend.database.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    client_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    other_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    conversation_type = Column(String, nullable=False)  # client_engineer / client_factory

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)