"""
ZeRoN IA — AI Chat API Endpoints
POST /ai/chat        — Send a message to the AI assistant
GET  /ai/history     — Get chat history for a session
GET  /ai/sessions    — List user's chat sessions
DELETE /ai/sessions  — Clear all sessions for the current user
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.models.chat_history import ChatMessage
from app.schemas.ai_chat import ChatRequest, ChatResponse, ChatMessageOut, ChatSessionOut
from app.api.endpoints.auth import get_current_user
from app.services.ai_assistant import chat as ai_chat

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def send_chat_message(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Send a message to ZeRoN IA and get a response."""
    session_id = body.session_id or str(uuid.uuid4())

    # Load conversation history for this session
    history_records = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history = [{"role": msg.role, "content": msg.content} for msg in history_records]

    # Call AI service
    ai_response = ai_chat(
        message=body.message,
        history=history,
        db=db,
    )

    # Persist user message and assistant response
    now = datetime.now(timezone.utc)
    user_msg = ChatMessage(
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=body.message,
        created_at=now,
    )
    assistant_msg = ChatMessage(
        session_id=session_id,
        user_id=current_user.id,
        role="assistant",
        content=ai_response,
        created_at=now,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(response=ai_response, session_id=session_id)


@router.get("/history/{session_id}", response_model=List[ChatMessageOut])
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve chat history for a specific session."""
    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return messages


@router.get("/sessions", response_model=List[ChatSessionOut])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all chat sessions for the current user."""
    sessions = (
        db.query(
            ChatMessage.session_id,
            func.count(ChatMessage.id).label("message_count"),
            func.min(ChatMessage.created_at).label("created_at"),
            func.max(ChatMessage.created_at).label("updated_at"),
        )
        .filter(ChatMessage.user_id == current_user.id)
        .group_by(ChatMessage.session_id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .all()
    )

    result = []
    for s in sessions:
        # Get last message content for preview
        last_msg = (
            db.query(ChatMessage.content)
            .filter(
                ChatMessage.session_id == s.session_id,
                ChatMessage.user_id == current_user.id,
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        result.append(ChatSessionOut(
            session_id=s.session_id,
            last_message=(last_msg.content[:100] + "...") if last_msg and len(last_msg.content) > 100 else (last_msg.content if last_msg else ""),
            message_count=s.message_count,
            created_at=s.created_at,
            updated_at=s.updated_at,
        ))
    return result


@router.delete("/sessions")
def clear_chat_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Clear all chat sessions for the current user."""
    db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).delete()
    db.commit()
    return {"ok": True, "message": "Historial de chat eliminado"}
