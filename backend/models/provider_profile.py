from sqlalchemy import Column, Integer, String, ForeignKey

from backend.database.base import Base


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    bio = Column(String, nullable=True)

    # marketplace search fields
    skills = Column(String, nullable=True)
    country = Column(String, nullable=True)
    availability = Column(String, nullable=True)