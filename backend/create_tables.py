from backend.database.base import Base, engine

from backend.models.application import Application
from backend.models.attachment import Attachment
from backend.models.conversation import Conversation
from backend.models.customer_profile import CustomerProfile
from backend.models.engineer_profile import EngineerProfile
from backend.models.factory_profile import FactoryProfile
from backend.models.message import Message
from backend.models.milestone import Milestone
from backend.models.notification import Notification
from backend.models.organization import Organization
from backend.models.project import Project
from backend.models.project_completion_request import ProjectCompletionRequest
from backend.models.project_event import ProjectEvent
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.user import User


def create_tables():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()