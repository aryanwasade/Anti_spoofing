"""
Report generator — builds a rich structured report from session + alert data.
All metrics expressed as percentages (0–100) and raw scores (0.0–1.0).
"""
from datetime import datetime, timezone
from backend.models.db_models import InterviewSession, AlertEvent
from backend.config import settings


def build_report(session: InterviewSession, alerts: list[AlertEvent]) -> dict:
    # Duration
    duration_s = 0.0
    if session.ended_at and session.started_at:
        duration_s = (session.ended_at - session.started_at).total_seconds()
    duration_min = max(duration_s / 60.0, 1.0 / 60.0)

    # Alert summary counts
    alert_counts: dict[str, int] = {}
    for a in alerts:
        alert_counts[a.alert_type] = alert_counts.get(a.alert_type, 0) + 1

    # Risk score (weighted alerts per minute, capped at 100)
    risk = 0.0
    for atype, count in alert_counts.items():
        weight = settings.ALERT_WEIGHTS.get(atype, 1.0)
        risk += weight * count / duration_min
    risk = min(round(risk, 2), 100.0)

    # Persist risk_score back (we just compute it, not save here)
    # (ws.py saves it on close; report just computes for display)

    # Recommendation
    if risk < 5:
        recommendation = "PASS"
    elif risk < 20:
        recommendation = "REVIEW"
    else:
        recommendation = "FAIL"

    # Convert 0..1 scores to percentages
    def pct(v: float) -> float:
        return round(float(v) * 100, 1)

    # Spoof-clean percentage = avg spoof confidence (higher = more real)
    spoof_clean_pct = pct(session.avg_spoof_confidence)

    # Alert rate per minute
    total_alerts = sum(alert_counts.values())
    alert_rate_per_min = round(total_alerts / duration_min, 2)

    # Per-alert-type rate
    alert_rates = {
        atype: round(count / duration_min, 3)
        for atype, count in alert_counts.items()
    }

    # Behavioral percentages
    attention_pct   = pct(session.avg_attention)
    liveness_pct    = pct(session.avg_liveness)
    trust_pct       = pct(session.avg_trust_score)
    eye_contact_pct = pct(session.avg_eye_contact)

    # Integrity score: composite of key clean metrics
    integrity_score = round(
        0.30 * session.avg_liveness     +
        0.25 * session.avg_attention    +
        0.25 * session.avg_spoof_confidence +
        0.20 * session.avg_eye_contact,
        3
    )

    return {
        "session_id":     session.id,
        "candidate_name": session.candidate_name,
        "role":           session.role,
        "started_at":     session.started_at.isoformat() if session.started_at else None,
        "ended_at":       session.ended_at.isoformat()   if session.ended_at   else None,
        "duration_seconds":          round(duration_s, 1),
        "total_frames_processed":    session.total_frames,

        # ── Behavioral scores (0–100 %) ────────────────────────────────
        "percentages": {
            "attention":    attention_pct,
            "liveness":     liveness_pct,
            "trust":        trust_pct,
            "eye_contact":  eye_contact_pct,
            "spoof_clean":  spoof_clean_pct,
            "integrity":    pct(integrity_score),
        },

        # ── Raw scores (0.0–1.0) ───────────────────────────────────────
        "metrics": {
            "avg_attention_score":    session.avg_attention,
            "avg_liveness_score":     session.avg_liveness,
            "avg_trust_score":        session.avg_trust_score,
            "avg_eye_contact":        session.avg_eye_contact,
            "avg_spoof_confidence":   session.avg_spoof_confidence,
            "spoof_events":           session.spoof_events,
            "lip_movement_events":    session.lip_movement_events,
            "body_movement_events":   session.body_movement_events,
            "head_turn_events":       session.head_turn_events,
            "gaze_away_events":       session.gaze_away_events,
        },

        # ── Gaze distribution ─────────────────────────────────────────
        "gaze_distribution": {
            "center": session.gaze_center_pct,
            "left":   session.gaze_left_pct,
            "right":  session.gaze_right_pct,
            "up":     session.gaze_up_pct,
            "down":   session.gaze_down_pct,
        },

        # ── Alert analytics ───────────────────────────────────────────
        "risk_score":          risk,
        "recommendation":      recommendation,
        "alert_summary":       alert_counts,
        "alert_rate_per_min":  alert_rate_per_min,
        "alert_rates":         alert_rates,
        "total_alerts":        total_alerts,

        # ── Full alert timeline ───────────────────────────────────────
        "alerts": [
            {
                "id":         a.id,
                "timestamp":  a.timestamp.isoformat(),
                "type":       a.alert_type,
                "severity":   a.severity,
                "confidence": a.confidence,
                "details":    a.details,
            }
            for a in sorted(alerts, key=lambda x: x.timestamp)
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
