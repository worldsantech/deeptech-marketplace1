from sqlalchemy.orm import Session

from backend.core.roles import ROLE_CUSTOMER, ROLE_PROVIDER
from backend.core.security import hash_password
from backend.database.session import SessionLocal
from backend.models.application import Application
from backend.models.customer_profile import CustomerProfile
from backend.models.message import Message
from backend.models.notification import Notification
from backend.models.project import Project
from backend.models.project_completion_request import ProjectCompletionRequest
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.saved_project import SavedProject
from backend.models.user import User


def filtered_payload(model_cls, payload: dict) -> dict:
    allowed_fields = set(model_cls.__table__.columns.keys())
    return {key: value for key, value in payload.items() if key in allowed_fields}


def get_or_create(session: Session, model_cls, lookup: dict, defaults: dict | None = None):
    instance = session.query(model_cls).filter_by(**lookup).first()
    if instance:
        return instance, False

    payload = dict(lookup)
    if defaults:
        payload.update(defaults)

    instance = model_cls(**filtered_payload(model_cls, payload))
    session.add(instance)
    session.flush()
    return instance, True


def seed_users(session: Session):
    demo_password_hash = hash_password("DemoPass123!")

    customer = session.query(User).filter(User.email == "demo.customer@example.com").first()
    if customer is None:
        customer = User(
            email="demo.customer@example.com",
            full_name="Demo Customer",
            role=ROLE_CUSTOMER,
            hashed_password=demo_password_hash,
            is_active=True,
            is_verified=True,
        )
        session.add(customer)
        session.flush()
    else:
        customer.full_name = "Demo Customer"
        customer.role = ROLE_CUSTOMER
        customer.hashed_password = demo_password_hash
        customer.is_active = True
        customer.is_verified = True

    provider_1 = session.query(User).filter(User.email == "demo.provider1@example.com").first()
    if provider_1 is None:
        provider_1 = User(
            email="demo.provider1@example.com",
            full_name="Anna Service Tech",
            role=ROLE_PROVIDER,
            hashed_password=demo_password_hash,
            is_active=True,
            is_verified=True,
        )
        session.add(provider_1)
        session.flush()
    else:
        provider_1.full_name = "Anna Service Tech"
        provider_1.role = ROLE_PROVIDER
        provider_1.hashed_password = demo_password_hash
        provider_1.is_active = True
        provider_1.is_verified = True

    provider_2 = session.query(User).filter(User.email == "demo.provider2@example.com").first()
    if provider_2 is None:
        provider_2 = User(
            email="demo.provider2@example.com",
            full_name="Mark Field Engineer",
            role=ROLE_PROVIDER,
            hashed_password=demo_password_hash,
            is_active=True,
            is_verified=True,
        )
        session.add(provider_2)
        session.flush()
    else:
        provider_2.full_name = "Mark Field Engineer"
        provider_2.role = ROLE_PROVIDER
        provider_2.hashed_password = demo_password_hash
        provider_2.is_active = True
        provider_2.is_verified = True

    session.flush()
    return customer, provider_1, provider_2


def seed_profiles(session: Session, customer: User, provider_1: User, provider_2: User):
    get_or_create(
        session,
        CustomerProfile,
        {"user_id": customer.id},
        {
            "company_name": "Demo Manufacturing Buyer",
            "country": "Poland",
            "city": "Gdansk",
            "bio": "Industrial buyer looking for field service and maintenance providers.",
        },
    )

    get_or_create(
        session,
        ProviderProfile,
        {"user_id": provider_1.id},
        {
            "bio": "Automation and PLC specialist for factory commissioning and troubleshooting.",
            "skills": "PLC, Siemens, commissioning, diagnostics, automation",
            "country": "Poland",
            "availability": "available",
        },
    )

    get_or_create(
        session,
        ProviderProfile,
        {"user_id": provider_2.id},
        {
            "bio": "Mechanical and maintenance field engineer for installation and repairs.",
            "skills": "maintenance, mechanical, installation, service, field support",
            "country": "Germany",
            "availability": "busy_soon",
        },
    )

    session.flush()


def seed_projects(session: Session, customer: User):
    open_project, _ = get_or_create(
        session,
        Project,
        {"owner_id": customer.id, "title": "PLC retrofit for packaging line"},
        {
            "description": "Need provider for PLC retrofit, startup, and diagnostics for packaging equipment.",
            "country": "Poland",
            "city": "Gdansk",
            "project_type": "plc",
            "budget_min": 2500,
            "budget_max": 5000,
            "currency": "EUR",
            "deadline_days": 21,
            "status": "open",
        },
    )

    in_progress_project, _ = get_or_create(
        session,
        Project,
        {"owner_id": customer.id, "title": "Preventive maintenance for conveyor system"},
        {
            "description": "Looking for provider to perform preventive maintenance and corrective actions on conveyor system.",
            "country": "Poland",
            "city": "Warsaw",
            "project_type": "maintenance",
            "budget_min": 1800,
            "budget_max": 3500,
            "currency": "EUR",
            "deadline_days": 14,
            "status": "in_progress",
        },
    )

    completed_project, _ = get_or_create(
        session,
        Project,
        {"owner_id": customer.id, "title": "Electrical commissioning for new assembly cell"},
        {
            "description": "Electrical commissioning, testing, and startup support for assembly cell deployment.",
            "country": "Germany",
            "city": "Berlin",
            "project_type": "electrical",
            "budget_min": 4000,
            "budget_max": 7000,
            "currency": "EUR",
            "deadline_days": 30,
            "status": "completed",
        },
    )

    session.flush()
    return open_project, in_progress_project, completed_project


def seed_applications(
    session: Session,
    open_project: Project,
    in_progress_project: Project,
    completed_project: Project,
    provider_1: User,
    provider_2: User,
):
    open_app_1, _ = get_or_create(
        session,
        Application,
        {"project_id": open_project.id, "applicant_user_id": provider_1.id},
        {
            "application_type": ROLE_PROVIDER,
            "cover_letter": "I can handle PLC retrofit, startup, and remote diagnostics support.",
            "proposed_budget": 4200,
            "estimated_timeline_days": 18,
            "status": "submitted",
        },
    )

    open_app_2, _ = get_or_create(
        session,
        Application,
        {"project_id": open_project.id, "applicant_user_id": provider_2.id},
        {
            "application_type": ROLE_PROVIDER,
            "cover_letter": "Experienced with industrial upgrade projects and maintenance execution.",
            "proposed_budget": 3900,
            "estimated_timeline_days": 20,
            "status": "shortlisted",
        },
    )

    active_app, _ = get_or_create(
        session,
        Application,
        {"project_id": in_progress_project.id, "applicant_user_id": provider_1.id},
        {
            "application_type": ROLE_PROVIDER,
            "cover_letter": "I can take over preventive maintenance and reporting.",
            "proposed_budget": 3000,
            "estimated_timeline_days": 10,
            "status": "accepted",
        },
    )

    rejected_active_app, _ = get_or_create(
        session,
        Application,
        {"project_id": in_progress_project.id, "applicant_user_id": provider_2.id},
        {
            "application_type": ROLE_PROVIDER,
            "cover_letter": "Available for conveyor maintenance support.",
            "proposed_budget": 3200,
            "estimated_timeline_days": 12,
            "status": "rejected",
        },
    )

    completed_app, _ = get_or_create(
        session,
        Application,
        {"project_id": completed_project.id, "applicant_user_id": provider_2.id},
        {
            "application_type": ROLE_PROVIDER,
            "cover_letter": "Can handle electrical commissioning and startup validation.",
            "proposed_budget": 6500,
            "estimated_timeline_days": 24,
            "status": "accepted",
        },
    )

    session.flush()

    if in_progress_project.selected_application_id != active_app.id:
        in_progress_project.selected_application_id = active_app.id
        in_progress_project.selected_applicant_user_id = provider_1.id
        in_progress_project.status = "in_progress"

    if completed_project.selected_application_id != completed_app.id:
        completed_project.selected_application_id = completed_app.id
        completed_project.selected_applicant_user_id = provider_2.id
        completed_project.status = "completed"

    session.flush()

    return {
        "open_app_1": open_app_1,
        "open_app_2": open_app_2,
        "active_app": active_app,
        "rejected_active_app": rejected_active_app,
        "completed_app": completed_app,
    }


def seed_saved_projects(session: Session, provider_1: User, open_project: Project):
    get_or_create(
        session,
        SavedProject,
        {"provider_id": provider_1.id, "project_id": open_project.id},
        {},
    )
    session.flush()


def seed_messages(session: Session, in_progress_project: Project, customer: User, provider_1: User):
    get_or_create(
        session,
        Message,
        {
            "project_id": in_progress_project.id,
            "sender_user_id": customer.id,
            "recipient_user_id": provider_1.id,
            "body": "Hi, please confirm the maintenance checklist before arrival.",
        },
        {
            "is_read": True,
        },
    )

    get_or_create(
        session,
        Message,
        {
            "project_id": in_progress_project.id,
            "sender_user_id": provider_1.id,
            "recipient_user_id": customer.id,
            "body": "Confirmed. I will start with diagnostics and preventive checks.",
        },
        {
            "is_read": False,
        },
    )

    session.flush()


def seed_notifications(
    session: Session,
    customer: User,
    provider_1: User,
    open_project: Project,
    in_progress_project: Project,
    active_app: Application,
):
    get_or_create(
        session,
        Notification,
        {
            "user_id": customer.id,
            "title": "New application received",
            "type": "new_application",
            "related_project_id": open_project.id,
        },
        {
            "message": "A provider applied to your open project.",
            "related_application_id": active_app.id,
            "is_read": False,
        },
    )

    get_or_create(
        session,
        Notification,
        {
            "user_id": provider_1.id,
            "title": "Application status updated",
            "type": "application_status_updated",
            "related_project_id": in_progress_project.id,
        },
        {
            "message": "Your application was accepted and project moved to in progress.",
            "related_application_id": active_app.id,
            "is_read": False,
        },
    )

    session.flush()


def seed_completion_and_reviews(
    session: Session,
    completed_project: Project,
    customer: User,
    provider_2: User,
):
    completion_request, _ = get_or_create(
        session,
        ProjectCompletionRequest,
        {
            "project_id": completed_project.id,
            "provider_id": provider_2.id,
            "customer_id": customer.id,
        },
        {
            "status": "approved",
            "provider_message": "Commissioning completed, all checks passed.",
            "customer_message": "Approved. Equipment is accepted.",
        },
    )

    get_or_create(
        session,
        Review,
        {
            "project_id": completed_project.id,
            "reviewer_user_id": customer.id,
            "reviewed_user_id": provider_2.id,
        },
        {
            "rating": 5,
            "comment": "Excellent commissioning support, clear communication, and on-time delivery.",
        },
    )

    get_or_create(
        session,
        Review,
        {
            "project_id": completed_project.id,
            "reviewer_user_id": provider_2.id,
            "reviewed_user_id": customer.id,
        },
        {
            "rating": 5,
            "comment": "Well-prepared customer, fast decisions, and smooth project coordination.",
        },
    )

    session.flush()
    return completion_request


def main():
    session = SessionLocal()
    try:
        customer, provider_1, provider_2 = seed_users(session)
        seed_profiles(session, customer, provider_1, provider_2)

        open_project, in_progress_project, completed_project = seed_projects(session, customer)

        applications = seed_applications(
            session=session,
            open_project=open_project,
            in_progress_project=in_progress_project,
            completed_project=completed_project,
            provider_1=provider_1,
            provider_2=provider_2,
        )

        seed_saved_projects(session, provider_1, open_project)
        seed_messages(session, in_progress_project, customer, provider_1)
        seed_notifications(
            session,
            customer,
            provider_1,
            open_project,
            in_progress_project,
            applications["active_app"],
        )
        seed_completion_and_reviews(session, completed_project, customer, provider_2)

        session.commit()

        print("Demo seed completed successfully.")
        print("")
        print("Demo users:")
        print("Customer  -> demo.customer@example.com / DemoPass123!")
        print("Provider1 -> demo.provider1@example.com / DemoPass123!")
        print("Provider2 -> demo.provider2@example.com / DemoPass123!")
        print("")
        print("Created demo data:")
        print("- 1 customer")
        print("- 2 providers")
        print("- provider profiles")
        print("- 3 projects (open / in_progress / completed)")
        print("- applications")
        print("- messages")
        print("- notifications")
        print("- completion request")
        print("- reviews")
        print("- saved project")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()