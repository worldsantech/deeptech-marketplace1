from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.user import User
from backend.models.project import Project
from backend.models.application import Application
from backend.models.conversation import Conversation
from backend.schemas.conversation import ConversationCreate, ConversationResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client = db.query(User).filter(User.id == payload.client_user_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client user not found")

    other_user = db.query(User).filter(User.id == payload.other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="Other user not found")

    if client.role != "client":
        raise HTTPException(status_code=400, detail="client_user_id must belong to a client")

    if project.client_id != payload.client_user_id:
        raise HTTPException(status_code=400, detail="This project does not belong to the specified client")

    if other_user.role not in {"engineer", "factory"}:
        raise HTTPException(status_code=400, detail="Other user must be engineer or factory")

    application = db.query(Application).filter(
        Application.project_id == payload.project_id,
        Application.applicant_user_id == payload.other_user_id
    ).first()

    if not application:
        raise HTTPException(status_code=400, detail="Conversation can be created only after application")

    existing_conversation = db.query(Conversation).filter(
        Conversation.project_id == payload.project_id,
        Conversation.client_user_id == payload.client_user_id,
        Conversation.other_user_id == payload.other_user_id
    ).first()

    if existing_conversation:
        return existing_conversation

    conversation_type = "client_engineer" if other_user.role == "engineer" else "client_factory"

    conversation = Conversation(
        project_id=payload.project_id,
        client_user_id=payload.client_user_id,
        other_user_id=payload.other_user_id,
        conversation_type=conversation_type,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation