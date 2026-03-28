from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.exceptions import register_exception_handlers
from backend.core.logging import RequestLoggingMiddleware, configure_logging, logger
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

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "B2B marketplace backend for customers and providers. "
        "Core domains: auth, profiles, projects, applications, messaging, "
        "notifications, reviews, dashboards, milestones, completion flow, and search."
    ),
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS if settings.CORS_ALLOW_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(auth_router)

app.include_router(profiles_router)
app.include_router(engineers_router)
app.include_router(profile_stats_router)

app.include_router(projects_router)
app.include_router(project_detail_router)
app.include_router(applications_router)
app.include_router(milestones_router)
app.include_router(project_progress_router)
app.include_router(project_activity_router)
app.include_router(project_completion_router)
app.include_router(reviews_router)

app.include_router(messages_router)
app.include_router(notifications_router)
app.include_router(attachments_router)

app.include_router(search_projects_router)
app.include_router(search_providers_router)
app.include_router(homepage_router)
app.include_router(favorites_router)

app.include_router(provider_dashboard_router)
app.include_router(customer_dashboard_router)


@app.on_event("startup")
def on_startup():
    logger.info(
        "app_startup app_name=%s version=%s env=%s debug=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENV,
        settings.DEBUG,
    )


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "DeepTech Marketplace API is running",
        "status": "ok",
        "environment": settings.ENV,
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "environment": settings.ENV,
    }