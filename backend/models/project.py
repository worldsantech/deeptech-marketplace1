from sqlalchemy import Column, Integer, String, Text, ForeignKey

from backend.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String, default="open")

    selected_application_id = Column(Integer, nullable=True)
    selected_applicant_user_id = Column(Integer, nullable=True)

    # marketplace search fields
    country = Column(String, nullable=True)
    project_type = Column(String, nullable=True)
    budget_min = Column(Integer, nullable=True)
    budget_max = Column(Integer, nullable=True)