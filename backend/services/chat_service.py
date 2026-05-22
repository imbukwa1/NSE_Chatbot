import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from models.chat import ChatMessage, ChatSession
from models.user import User


def api_success(message: str, data: dict | None = None) -> dict:
    return {"success": True, "message": message, "data": data or {}}


def make_session_title(message_text: str) -> str:
    title = " ".join(message_text.strip().split())
    return title[:57] + "..." if len(title) > 60 else title or "New NSE chat"


def create_chat_session(
    db: Session,
    user: User,
    title: str | None = None,
) -> ChatSession:
    session = ChatSession(user_id=user.id, title=title or "New NSE chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(db: Session, user: User) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


def get_owned_session(db: Session, user: User, session_id: int) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session was not found.",
        )
    return session


def add_message(
    db: Session,
    session: ChatSession,
    sender_type: str,
    message_text: str,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session.id,
        sender_type=sender_type,
        message_text=message_text,
    )
    session.updated_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(session)
    return message


def delete_session(db: Session, session: ChatSession) -> None:
    db.delete(session)
    db.commit()


async def generate_chatbot_response(query: str) -> dict[str, Any]:
    """Reuse the existing chatbot endpoint without rewriting the AI engine."""
    from main import ChatRequest, chat

    response = await chat(ChatRequest(query=query))

    if isinstance(response, JSONResponse):
        return json.loads(response.body.decode("utf-8"))

    if isinstance(response, StreamingResponse):
        message_parts: list[str] = []
        metadata: dict[str, Any] = {
            "type": "ai_response",
            "data": {},
            "disclaimer": "This is not financial advice.",
        }
        async for chunk in response.body_iterator:
            text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            for block in text.split("\n\n"):
                if not block.strip():
                    continue
                event = "message"
                data_lines: list[str] = []
                for line in block.splitlines():
                    if line.startswith("event:"):
                        event = line.split(":", 1)[1].strip()
                    if line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].strip())
                data = "\n".join(data_lines)
                if event == "metadata" and data:
                    metadata = json.loads(data)
                elif event == "token":
                    message_parts.append(data)
        message = "".join(message_parts).strip()
        return {
            **metadata,
            "message": message or metadata.get("message", ""),
        }

    if isinstance(response, dict):
        return response

    return {
        "type": "ai_response",
        "data": {},
        "message": str(response),
        "disclaimer": "This is not financial advice.",
    }


async def add_user_message_and_ai_response(
    db: Session,
    user: User,
    session_id: int,
    message_text: str,
) -> tuple[ChatSession, ChatMessage, ChatMessage, dict[str, Any]]:
    session = get_owned_session(db, user, session_id)

    if session.title == "New NSE chat":
        session.title = make_session_title(message_text)
        db.commit()
        db.refresh(session)

    user_message = add_message(db, session, "user", message_text)
    chatbot_response = await generate_chatbot_response(message_text)
    ai_text = chatbot_response.get("message") or chatbot_response.get("data", {}).get("analysis")
    if not ai_text:
        ai_text = "I could not prepare a response for that query. Please try again."
    ai_message = add_message(db, session, "ai", ai_text)
    return session, user_message, ai_message, chatbot_response

