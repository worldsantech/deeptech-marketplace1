from fastapi import FastAPI

from backend.database.base import Base
from backend.database.database import engine

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

from backend.routers.applications import router as applications_router
from backend.routers.attachments import router as attachments_router
from backend.routers.auth import router as auth_router
from backend.routers.customer_dashboard import router as customer_dashboard_router
from backend.routers.engineers import router as engineers_router
from backend.routers.favorites import router as favorites_router
from backend.routers.homepage import router as homepage_router
from backend.routers.messages import router as messages_router
from backend.routers.milestones import router as milestones_router
from backend.routers.notifications import router as notifications_router
from backend.routers.profile_stats import router as profile_stats_router
from backend.routers.project_activity import router as project_activity_router
from backend.routers.project_detail import router as project_detail_router
from backend.routers.project_progress import router as project_progress_router
from backend.routers.profiles import router as profiles_router
from backend.routers.projects import router as projects_router
from backend.routers.projects_completion import router as project_completion_router
from backend.routers.provider_dashboard import router as provider_dashboard_router
from backend.routers.reviews import router as reviews_router
from backend.routers.search_projects import router as search_projects_router
from backend.routers.search_providers import router as search_providers_router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(project_detail_router)
app.include_router(applications_router)
app.include_router(profiles_router)
app.include_router(engineers_router)
app.include_router(search_projects_router)
app.include_router(search_providers_router)
app.include_router(messages_router)
app.include_router(homepage_router)
app.include_router(favorites_router)
app.include_router(provider_dashboard_router)
app.include_router(customer_dashboard_router)
app.include_router(notifications_router)
app.include_router(project_completion_router)
app.include_router(reviews_router)
app.include_router(attachments_router)
app.include_router(profile_stats_router)
app.include_router(milestones_router)
app.include_router(project_progress_router)
app.include_router(project_activity_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}