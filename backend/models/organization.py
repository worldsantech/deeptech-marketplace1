from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), index=True)

    type: Mapped[str] = mapped_column(String(50))

    country: Mapped[str] = mapped_column(String(100))

    website: Mapped[str | None] = mapped_column(String(255), nullable=True)