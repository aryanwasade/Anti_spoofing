"""
Report router.
GET /report/{session_id} → returns full JSON session report
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.db_models import InterviewSession, AlertEvent
from backend.utils.report_gen import build_report

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{session_id}")
async def get_report(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    result = await db.execute(
        select(AlertEvent)
        .where(AlertEvent.session_id == session_id)
        .order_by(AlertEvent.timestamp)
    )
    alerts = result.scalars().all()

    return build_report(session, alerts)
