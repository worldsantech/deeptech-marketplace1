from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.review import Review
from backend.models.user import User
from backend.services.project_event_logger import log_project_event

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("")
def create_review(
    project_id: int,
    rating: int,
    comment: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5",
        )

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can review only completed projects",
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

    review = Review(
        project_id=project.id,
        reviewer_user_id=reviewer_id,
        reviewed_user_id=reviewed_user_id,
        rating=rating,
        comment=comment,
    )

    db.add(review)
    db.flush()

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="review_created",
        title="Review created",
        description=comment if comment else f"Rating: {rating}/5",
        actor_user_id=current_user.id,
        entity_type="review",
        entity_id=review.id,
        metadata={
            "rating": rating,
            "reviewer_user_id": reviewer_id,
            "reviewed_user_id": reviewed_user_id,
            "has_comment": bool(comment.strip()) if comment else False,
        },
    )

    db.commit()
    db.refresh(review)

    return review


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