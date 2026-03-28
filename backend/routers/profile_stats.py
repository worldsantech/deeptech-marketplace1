from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.application import Application
from backend.models.customer_profile import CustomerProfile
from backend.models.project import Project
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.user import User

router = APIRouter(prefix="/profiles", tags=["Profile Stats"])


def get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def build_recent_reviews(review_rows):
    recent_reviews = []
    for review, reviewer in review_rows:
        recent_reviews.append(
            {
                "review_id": review.id,
                "project_id": review.project_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at,
                "reviewer": {
                    "id": reviewer.id,
                    "full_name": reviewer.full_name,
                    "role": reviewer.role,
                },
            }
        )
    return recent_reviews


@router.get("/{user_id}/stats")
def get_profile_stats(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = get_user_or_404(user_id, db)

    average_rating = (
        db.query(func.avg(Review.rating))
        .filter(Review.reviewed_user_id == user.id)
        .scalar()
    )

    reviews_count = (
        db.query(Review)
        .filter(Review.reviewed_user_id == user.id)
        .count()
    )

    recent_reviews_rows = (
        db.query(Review, User)
        .join(User, User.id == Review.reviewer_user_id)
        .filter(Review.reviewed_user_id == user.id)
        .order_by(Review.id.desc())
        .limit(5)
        .all()
    )

    recent_reviews = build_recent_reviews(recent_reviews_rows)

    if user.role == "Provider":
        profile = (
            db.query(ProviderProfile)
            .filter(ProviderProfile.user_id == user.id)
            .first()
        )

        completed_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == user.id,
                Project.status == "completed",
            )
            .count()
        )

        active_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == user.id,
                Project.status == "in_progress",
            )
            .count()
        )

        is_owner = current_user.id == user.id

        applications_total = None
        applications_submitted = None
        applications_shortlisted = None
        applications_accepted = None
        applications_rejected = None

        if is_owner:
            applications_total = (
                db.query(Application)
                .filter(Application.applicant_user_id == user.id)
                .count()
            )

            applications_submitted = (
                db.query(Application)
                .filter(
                    Application.applicant_user_id == user.id,
                    Application.status == "submitted",
                )
                .count()
            )

            applications_shortlisted = (
                db.query(Application)
                .filter(
                    Application.applicant_user_id == user.id,
                    Application.status == "shortlisted",
                )
                .count()
            )

            applications_accepted = (
                db.query(Application)
                .filter(
                    Application.applicant_user_id == user.id,
                    Application.status == "accepted",
                )
                .count()
            )

            applications_rejected = (
                db.query(Application)
                .filter(
                    Application.applicant_user_id == user.id,
                    Application.status == "rejected",
                )
                .count()
            )

        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "role": user.role,
                "is_owner_view": is_owner,
            },
            "profile": {
                "bio": profile.bio if profile else None,
                "skills": profile.skills if profile else None,
                "country": profile.country if profile else None,
                "availability": profile.availability if profile else None,
            },
            "stats": {
                "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                "reviews_count": reviews_count,
                "completed_projects_count": completed_projects_count,
                "active_projects_count": active_projects_count,
                "applications_total": applications_total,
                "applications_submitted": applications_submitted,
                "applications_shortlisted": applications_shortlisted,
                "applications_accepted": applications_accepted,
                "applications_rejected": applications_rejected,
            },
            "recent_reviews": recent_reviews,
        }

    if user.role == "Customer":
        profile = (
            db.query(CustomerProfile)
            .filter(CustomerProfile.user_id == user.id)
            .first()
        )

        projects_total = (
            db.query(Project)
            .filter(Project.owner_id == user.id)
            .count()
        )

        projects_open = (
            db.query(Project)
            .filter(
                Project.owner_id == user.id,
                Project.status == "open",
            )
            .count()
        )

        projects_in_progress = (
            db.query(Project)
            .filter(
                Project.owner_id == user.id,
                Project.status == "in_progress",
            )
            .count()
        )

        projects_completed = (
            db.query(Project)
            .filter(
                Project.owner_id == user.id,
                Project.status == "completed",
            )
            .count()
        )

        is_owner = current_user.id == user.id
        applications_received_total = None

        if is_owner:
            applications_received_total = (
                db.query(Application)
                .join(Project, Project.id == Application.project_id)
                .filter(Project.owner_id == user.id)
                .count()
            )

        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "role": user.role,
                "is_owner_view": is_owner,
            },
            "profile": {
                "bio": profile.bio if profile else None,
                "country": getattr(profile, "country", None) if profile else None,
            },
            "stats": {
                "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                "reviews_count": reviews_count,
                "projects_total": projects_total,
                "projects_open": projects_open,
                "projects_in_progress": projects_in_progress,
                "projects_completed": projects_completed,
                "applications_received_total": applications_received_total,
            },
            "recent_reviews": recent_reviews,
        }

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role,
            "is_owner_view": current_user.id == user.id,
        },
        "stats": {
            "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
            "reviews_count": reviews_count,
        },
        "recent_reviews": recent_reviews,
    }


@router.get("/{user_id}/public")
def get_public_profile_with_stats(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(user_id, db)

    average_rating = (
        db.query(func.avg(Review.rating))
        .filter(Review.reviewed_user_id == user.id)
        .scalar()
    )

    reviews_count = (
        db.query(Review)
        .filter(Review.reviewed_user_id == user.id)
        .count()
    )

    if user.role == "Provider":
        profile = (
            db.query(ProviderProfile)
            .filter(ProviderProfile.user_id == user.id)
            .first()
        )

        completed_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == user.id,
                Project.status == "completed",
            )
            .count()
        )

        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "role": user.role,
            },
            "profile": {
                "bio": profile.bio if profile else None,
                "skills": profile.skills if profile else None,
                "country": profile.country if profile else None,
                "availability": profile.availability if profile else None,
            },
            "stats": {
                "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                "reviews_count": reviews_count,
                "completed_projects_count": completed_projects_count,
            },
        }

    if user.role == "Customer":
        profile = (
            db.query(CustomerProfile)
            .filter(CustomerProfile.user_id == user.id)
            .first()
        )

        projects_completed = (
            db.query(Project)
            .filter(
                Project.owner_id == user.id,
                Project.status == "completed",
            )
            .count()
        )

        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "role": user.role,
            },
            "profile": {
                "bio": profile.bio if profile else None,
                "country": getattr(profile, "country", None) if profile else None,
            },
            "stats": {
                "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                "reviews_count": reviews_count,
                "projects_completed": projects_completed,
            },
        }

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role,
        },
        "stats": {
            "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
            "reviews_count": reviews_count,
        },
    }