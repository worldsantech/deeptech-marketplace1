import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.project_completion_request import ProjectCompletionRequest
from backend.models.review import Review
from backend.models.user import User
from backend.services.project_event_logger import log_project_event

logger = logging.getLogger("app")

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_latest_approved_completion_request(
    project_id: int,
    db: Session,
) -> ProjectCompletionRequest | None:
    return (
        db.query(ProjectCompletionRequest)
        .filter(
            ProjectCompletionRequest.project_id == project_id,
            ProjectCompletionRequest.status == "approved",
        )
        .order_by(ProjectCompletionRequest.created_at.desc(), ProjectCompletionRequest.id.desc())
        .first()
    )


def ensure_project_reviewable(project: Project) -> None:
    if project.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can review only completed projects",
        )

    if not project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have a selected provider",
        )


def clean_comment(value: str) -> str:
    cleaned = (value or "").strip()
    return cleaned


@router.post("")
def create_review(
    project_id: int,
    rating: int,
    comment: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if rating < 1 or rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5",
            )

        project = get_project_or_404(project_id, db)
        ensure_project_reviewable(project)

        approved_completion_request = get_latest_approved_completion_request(project.id, db)
        if not approved_completion_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Review is allowed only after an approved completion request",
            )

        reviewer_id = current_user.id

        if reviewer_id == project.owner_id:
            reviewed_user_id = project.selected_applicant_user_id
        elif reviewer_id == project.selected_applicant_user_id:
            reviewed_user_id = project.owner_id
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not part of this project",
            )

        if reviewer_id == reviewed_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot review yourself",
            )

        existing_review = (
            db.query(Review)
            .filter(
                Review.project_id == project.id,
                Review.reviewer_user_id == reviewer_id,
            )
            .first()
        )

        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already reviewed this project",
            )

        clean_review_comment = clean_comment(comment)

        review = Review(
            project_id=project.id,
            reviewer_user_id=reviewer_id,
            reviewed_user_id=reviewed_user_id,
            rating=rating,
            comment=clean_review_comment,
        )

        db.add(review)
        db.flush()

        log_project_event(
            db=db,
            project_id=project.id,
            event_type="review_created",
            title="Review created",
            description=clean_review_comment if clean_review_comment else f"Rating: {rating}/5",
            actor_user_id=current_user.id,
            entity_type="review",
            entity_id=review.id,
            metadata={
                "rating": rating,
                "reviewer_user_id": reviewer_id,
                "reviewed_user_id": reviewed_user_id,
                "has_comment": bool(clean_review_comment),
            },
        )

        db.commit()
        db.refresh(review)

        return review

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while creating review. project_id=%s user_id=%s",
            project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review",
        )


@router.get("/user/{user_id}")
def get_user_reviews(
    user_id: int,
    db: Session = Depends(get_db),
):
    reviews = (
        db.query(Review)
        .filter(Review.reviewed_user_id == user_id)
        .order_by(Review.id.desc())
        .all()
    )

    return {
        "user_id": user_id,
        "total": len(reviews),
        "items": reviews,
    }