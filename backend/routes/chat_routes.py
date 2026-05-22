from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionResponse,
)
from services.chat_service import (
    add_user_message_and_ai_response,
    api_success,
    create_chat_session,
    delete_session,
    get_owned_session,
    get_user_sessions,
)

router = APIRouter(prefix="/chat/sessions", tags=["Chat History"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = create_chat_session(db, current_user, payload.title)
    return api_success(
        "Chat session created successfully",
        {"session": ChatSessionResponse.model_validate(session).model_dump(mode="json")},
    )


@router.get("")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = get_user_sessions(db, current_user)
    return api_success(
        "Chat sessions retrieved successfully",
        {
            "sessions": [
                ChatSessionResponse.model_validate(session).model_dump(mode="json")
                for session in sessions
            ]
        },
    )


@router.get("/{session_id}")
def retrieve_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_owned_session(db, current_user, session_id)
    return api_success(
        "Chat session retrieved successfully",
        {"session": ChatSessionDetail.model_validate(session).model_dump(mode="json")},
    )


@router.delete("/{session_id}")
def remove_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_owned_session(db, current_user, session_id)
    delete_session(db, session)
    return api_success("Chat session deleted successfully", {"session_id": session_id})


@router.post("/{session_id}/messages")
async def add_session_message(
    session_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session, user_message, ai_message, chatbot_response = (
        await add_user_message_and_ai_response(
            db,
            current_user,
            session_id,
            payload.message_text,
        )
    )
    return api_success(
        "Chat message saved successfully",
        {
            "session": ChatSessionResponse.model_validate(session).model_dump(mode="json"),
            "user_message": ChatMessageResponse.model_validate(user_message).model_dump(mode="json"),
            "ai_message": ChatMessageResponse.model_validate(ai_message).model_dump(mode="json"),
            "chatbot_response": chatbot_response,
        },
    )

