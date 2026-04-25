"""
SQLAlchemy ORM models for sessions, alerts, and reports.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class InterviewSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    candidate_name: Mapped[str] = mapped_column(String, default="Candidate")
    role: Mapped[str] = mapped_column(String, default="candidate")  # candidate | interviewer
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")   # active | closed

    # Frame stats
    total_frames: Mapped[int] = mapped_column(Integer, default=0)

    # Core behavioral scores (0.0–1.0)
    avg_attention: Mapped[float] = mapped_column(Float, default=0.0)
    avg_liveness: Mapped[float] = mapped_column(Float, default=0.0)
    avg_trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_eye_contact: Mapped[float] = mapped_column(Float, default=0.0)
    avg_spoof_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Event counters
    spoof_events: Mapped[int] = mapped_column(Integer, default=0)
    lip_movement_events: Mapped[int] = mapped_column(Integer, default=0)
    body_movement_events: Mapped[int] = mapped_column(Integer, default=0)
    head_turn_events: Mapped[int] = mapped_column(Integer, default=0)
    gaze_away_events: Mapped[int] = mapped_column(Integer, default=0)

    # Gaze distribution (% time in each direction 0–100)
    gaze_center_pct: Mapped[float] = mapped_column(Float, default=0.0)
    gaze_left_pct: Mapped[float] = mapped_column(Float, default=0.0)
    gaze_right_pct: Mapped[float] = mapped_column(Float, default=0.0)
    gaze_up_pct: Mapped[float] = mapped_column(Float, default=0.0)
    gaze_down_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Computed risk
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    alerts: Mapped[list["AlertEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    alert_type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)   # LOW | MEDIUM | HIGH | CRITICAL
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["InterviewSession"] = relationship(back_populates="alerts")
