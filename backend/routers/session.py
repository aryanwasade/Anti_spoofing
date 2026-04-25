"""
Session management router.
POST /session/start    → create new session, return session_id
GET  /session/{id}     → get session info
GET  /sessions         → list all sessions (with full metrics)
POST /session/{id}/end → close session
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.database import get_db
from backend.models.db_models import InterviewSession

router = APIRouter(prefix="/session", tags=["session"])


class StartSessionRequest(BaseModel):
    candidate_name: str = "Candidate"
    role: str = "candidate"  # "candidate" | "interviewer"


@router.post("/start")
async def start_session(body: StartSessionRequest, db: AsyncSession = Depends(get_db)):
    session = InterviewSession(
        id=str(uuid.uuid4()),
        candidate_name=body.candidate_name,
        role=body.role,
        started_at=datetime.now(timezone.utc),
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "session_id":     session.id,
        "candidate_name": session.candidate_name,
        "role":           session.role,
    }


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(InterviewSession, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return _session_dict(s)


@router.get("s")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InterviewSession)
        .order_by(InterviewSession.started_at.desc())
        .limit(100)
    )
    sessions = result.scalars().all()
    return [_session_dict(s) for s in sessions]


@router.post("/{session_id}/end")
async def end_session(session_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(InterviewSession, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    s.status   = "closed"
    s.ended_at = datetime.now(timezone.utc)
    await db.commit()
    return {"session_id": session_id, "status": "closed"}


def _session_dict(s: InterviewSession) -> dict:
    return {
        "session_id":          s.id,
        "candidate_name":      s.candidate_name,
        "role":                s.role,
        "status":              s.status,
        "started_at":          s.started_at.isoformat() if s.started_at else None,
        "ended_at":            s.ended_at.isoformat()   if s.ended_at   else None,
        "total_frames":        s.total_frames,
        # Scores (0.0–1.0)
        "avg_attention":       s.avg_attention,
        "avg_liveness":        s.avg_liveness,
        "avg_trust_score":     s.avg_trust_score,
        "avg_eye_contact":     s.avg_eye_contact,
        "avg_spoof_confidence":s.avg_spoof_confidence,
        # Events
        "spoof_events":        s.spoof_events,
        "lip_movement_events": s.lip_movement_events,
        "body_movement_events":s.body_movement_events,
        "head_turn_events":    s.head_turn_events,
        "gaze_away_events":    s.gaze_away_events,
        # Gaze distribution
        "gaze_center_pct":     s.gaze_center_pct,
        "gaze_left_pct":       s.gaze_left_pct,
        "gaze_right_pct":      s.gaze_right_pct,
        "gaze_up_pct":         s.gaze_up_pct,
        "gaze_down_pct":       s.gaze_down_pct,
        # Risk
        "risk_score":          s.risk_score,
    }
