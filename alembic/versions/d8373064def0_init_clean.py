"""init_clean

Revision ID: d8373064def0
Revises: 
Create Date: 2026-03-25

"""

from typing import Sequence, Union

from backend.database.base import Base
from backend.database.database import engine

# revision identifiers, used by Alembic.
revision: str = "d8373064def0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    Base.metadata.drop_all(bind=engine)