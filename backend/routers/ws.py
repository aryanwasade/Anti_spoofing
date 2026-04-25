"""
WebSocket router — real-time video frame analysis.

Flow:
  1. Browser connects → /ws/{session_id}
  2. Browser sends JSON: { "frame": "data:image/jpeg;base64,..." }
  3. Backend runs full pipeline
  4. Backend sends back JSON FrameResult
  5. Significant alerts are persisted to DB
"""
import json
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models.db_models import InterviewSession, AlertEvent
from backend.pipeline.runner import AnalysisPipeline
from backend.utils.image import b64_to_frame

router = APIRouter(tags=["websocket"])

# Throttle DB writes: only persist alert if same type not seen in last N frames
ALERT_PERSIST_COOLDOWN = 25   # frames (~2.5s at 10fps)
SESSION_UPDATE_EVERY   = 20   # update session stats every N frames


def _frame_result_to_dict(r) -> dict:
    return {
        "face_count":          r.face_count,
        "face_bbox":           r.face_bbox,
        # Liveness
        "ear":                 r.ear,
        "blink_detected":      r.blink_detected,
        "total_blinks":        r.total_blinks,
        "blink_rate_per_min":  r.blink_rate_per_min,
        "liveness_score":      r.liveness_score,
        "is_live":             r.is_live,
        "pitch":               r.pitch,
        "yaw":                 r.yaw,
        "roll":                r.roll,
        "head_turned":         r.head_turned,
        # Spoof
        "spoof_label":         r.spoof_label,
        "spoof_confidence":    r.spoof_confidence,
        "spoof_method":        r.spoof_method,
        "spoof_type":          r.spoof_type,
        # Behavior
        "gaze_direction":      r.gaze_direction,
        "attention_score":     r.attention_score,
        "is_attentive":        r.is_attentive,
        "eye_contact_score":   r.eye_contact_score,
        "lip_moving":          r.lip_moving,
        "lip_movement_score":  r.lip_movement_score,
        "body_movement":       r.body_movement,
        "excessive_movement":  r.excessive_movement,
        "movement_delta":      r.movement_delta,
        # Composite
        "trust_score":         r.trust_score,
        # Alerts
        "alerts":              r.alerts,
    }


@router.websocket("/ws/{session_id}")
async def video_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()

    pipeline = AnalysisPipeline()
    frame_count        = 0
    total_attention    = 0.0
    total_liveness     = 0.0
    total_trust        = 0.0
    total_eye_contact  = 0.0
    total_spoof_conf   = 0.0
    spoof_event_count  = 0
    lip_event_count    = 0
    body_event_count   = 0
    head_turn_count    = 0
    gaze_away_count    = 0
    alert_cooldown: dict[str, int] = {}

    try:
        async with AsyncSessionLocal() as db:
            session: InterviewSession | None = await db.get(InterviewSession, session_id)
            if not session:
                await websocket.send_json({"error": "Session not found"})
                await websocket.close()
                return

        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            b64 = payload.get("frame", "")

            frame = await asyncio.get_event_loop().run_in_executor(
                None, b64_to_frame, b64
            )
            if frame is None:
                continue

            result = await asyncio.get_event_loop().run_in_executor(
                None, pipeline.process, frame
            )

            frame_count        += 1
            total_attention    += result.attention_score
            total_liveness     += result.liveness_score
            total_trust        += result.trust_score
            total_eye_contact  += result.eye_contact_score
            total_spoof_conf   += result.spoof_confidence

            if result.spoof_label == "SPOOF":
                spoof_event_count += 1
            if result.lip_moving:
                lip_event_count += 1
            if result.excessive_movement:
                body_event_count += 1
            if result.head_turned:
                head_turn_count += 1
            if result.gaze_direction not in ("CENTER", "UNKNOWN"):
                gaze_away_count += 1

            # Persist alerts (with cooldown to avoid DB flooding)
            if result.alerts:
                async with AsyncSessionLocal() as db:
                    for alert in result.alerts:
                        atype = alert["type"]
                        if alert_cooldown.get(atype, 0) > 0:
                            alert_cooldown[atype] -= 1
                            continue
                        alert_cooldown[atype] = ALERT_PERSIST_COOLDOWN
                        db.add(AlertEvent(
                            session_id = session_id,
                            alert_type = atype,
                            severity   = alert["severity"],
                            confidence = alert["confidence"],
                            details    = alert.get("details"),
                            timestamp  = datetime.now(timezone.utc),
                        ))
                    await db.commit()

            # Update session stats periodically
            if frame_count % SESSION_UPDATE_EVERY == 0:
                gaze_dist = pipeline.get_gaze_distribution()
                async with AsyncSessionLocal() as db:
                    s = await db.get(InterviewSession, session_id)
                    if s:
                        s.total_frames         = frame_count
                        s.avg_attention        = round(total_attention   / frame_count, 3)
                        s.avg_liveness         = round(total_liveness    / frame_count, 3)
                        s.avg_trust_score      = round(total_trust       / frame_count, 3)
                        s.avg_eye_contact      = round(total_eye_contact / frame_count, 3)
                        s.avg_spoof_confidence = round(total_spoof_conf  / frame_count, 3)
                        s.spoof_events         = spoof_event_count
                        s.lip_movement_events  = lip_event_count
                        s.body_movement_events = body_event_count
                        s.head_turn_events     = head_turn_count
                        s.gaze_away_events     = gaze_away_count
                        s.gaze_center_pct  = gaze_dist["center"]
                        s.gaze_left_pct    = gaze_dist["left"]
                        s.gaze_right_pct   = gaze_dist["right"]
                        s.gaze_up_pct      = gaze_dist["up"]
                        s.gaze_down_pct    = gaze_dist["down"]
                        await db.commit()

            await websocket.send_json(_frame_result_to_dict(result))

    except WebSocketDisconnect:
        pass
    finally:
        gaze_dist = pipeline.get_gaze_distribution()
        pipeline.close()
        # Final session stats update
        if frame_count > 0:
            async with AsyncSessionLocal() as db:
                s = await db.get(InterviewSession, session_id)
                if s:
                    s.total_frames         = frame_count
                    s.avg_attention        = round(total_attention   / frame_count, 3)
                    s.avg_liveness         = round(total_liveness    / frame_count, 3)
                    s.avg_trust_score      = round(total_trust       / frame_count, 3)
                    s.avg_eye_contact      = round(total_eye_contact / frame_count, 3)
                    s.avg_spoof_confidence = round(total_spoof_conf  / frame_count, 3)
                    s.spoof_events         = spoof_event_count
                    s.lip_movement_events  = lip_event_count
                    s.body_movement_events = body_event_count
                    s.head_turn_events     = head_turn_count
                    s.gaze_away_events     = gaze_away_count
                    s.gaze_center_pct      = gaze_dist["center"]
                    s.gaze_left_pct        = gaze_dist["left"]
                    s.gaze_right_pct       = gaze_dist["right"]
                    s.gaze_up_pct          = gaze_dist["up"]
                    s.gaze_down_pct        = gaze_dist["down"]
                    s.status               = "closed"
                    s.ended_at             = datetime.now(timezone.utc)
                    await db.commit()
