from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so Alembic can detect them
from backend.models.user import User  # noqa: F401
from backend.models.application import Application  # noqa: F401
from backend.models.attachment import Attachment  # noqa: F401
from backend.models.conversation import Conversation  # noqa: F401
from backend.models.customer_profile import CustomerProfile  # noqa: F401
from backend.models.engineer_profile import EngineerProfile  # noqa: F401
from backend.models.factory_profile import FactoryProfile  # noqa: F401
from backend.models.message import Message  # noqa: F401
from backend.models.milestone import Milestone  # noqa: F401
from backend.models.notification import Notification  # noqa: F401
from backend.models.organization import Organization  # noqa: F401
from backend.models.project import Project  # noqa: F401
from backend.models.project_completion_request import ProjectCompletionRequest  # noqa: F401
from backend.models.project_event import ProjectEvent  # noqa: F401
from backend.models.provider_profile import ProviderProfile  # noqa: F401
from backend.models.review import Review  # noqa: F401
from backend.models.saved_project import SavedProject  # noqa: F401