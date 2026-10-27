from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import ChatSession
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionDetail, ChatSessionOut
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["assistant"])


@router.post("/message", response_model=ChatResponse,
             summary="Ask the Real Estate GPT assistant (rule-based parsing + real database search)")
def message(req: ChatRequest, db: DbSession, user: CurrentUser):
    """Anonymous callers get a stateless answer; authenticated callers also get their history persisted."""
    try:
        return chat_service.handle_message(db, user, req)
    except chat_service.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")


@router.get("/sessions", response_model=list[ChatSessionOut])
def sessions(user: CurrentUser, db: DbSession):
    return db.scalars(select(ChatSession).where(ChatSession.user_id == user.id)
                      .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc()).limit(50)).all()


def _own_session(db, user, session_id: int) -> ChatSession:
    sess = db.scalars(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
                      .options(selectinload(ChatSession.messages))).first()
    if sess is None:  # same response for "missing" and "someone else's": no information leak
        raise HTTPException(404, "Chat session not found")
    return sess


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def session_detail(session_id: int, user: CurrentUser, db: DbSession):
    return _own_session(db, user, session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, user: CurrentUser, db: DbSession) -> Response:
    db.delete(_own_session(db, user, session_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
