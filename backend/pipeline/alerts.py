"""
Alert Engine — rule-based alert generation with persistent timers.
Applies threshold rules to pipeline results and emits structured alert dicts.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from backend.pipeline.liveness  import LivenessResult
from backend.pipeline.spoof     import SpoofResult
from backend.pipeline.behavior  import BehaviorResult
from backend.pipeline.detector  import DetectionResult
from backend.config import settings


SEVERITY_MAP = {
    "FACE_ABSENT":        "HIGH",
    "MULTIPLE_FACES":     "HIGH",
    "BLINK_ABSENT":       "LOW",
    "GAZE_AWAY":          "MEDIUM",
    "LOW_ATTENTION":      "MEDIUM",
    "SPOOF_DETECTED":     "CRITICAL",
    "HEAD_TURNED":        "MEDIUM",
    "LIP_MOVEMENT":       "LOW",
    "EXCESSIVE_MOVEMENT": "MEDIUM",
    "LOOKING_DOWN":       "MEDIUM",
}


def _alert(alert_type: str, confidence: float = 1.0, details: dict | None = None) -> dict:
    return {
        "id":         str(uuid.uuid4()),
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "type":       alert_type,
        "severity":   SEVERITY_MAP.get(alert_type, "MEDIUM"),
        "confidence": round(confidence, 4),
        "details":    details or {},
    }


class AlertEngine:
    def __init__(self):
        # Frame counters for persistent conditions
        self._gaze_away_frames    = 0
        self._low_attention_frames = 0
        self._no_blink_frames      = 0
        self._lip_movement_frames  = 0
        self._body_movement_frames = 0
        self._fps_estimate         = 10.0  # assumed 10fps

        # Cooldown: prevent re-firing same alert every frame
        self._alert_cooldown: dict[str, int] = {}
        self._COOLDOWN_FRAMES = 40  # ~4s at 10fps

    def _can_fire(self, alert_type: str) -> bool:
        remaining = self._alert_cooldown.get(alert_type, 0)
        if remaining > 0:
            self._alert_cooldown[alert_type] = remaining - 1
            return False
        return True

    def _fire(self, alert_type: str, *args, **kwargs) -> dict | None:
        if self._can_fire(alert_type):
            self._alert_cooldown[alert_type] = self._COOLDOWN_FRAMES
            return _alert(alert_type, *args, **kwargs)
        return None

    def evaluate(
        self,
        detection: DetectionResult,
        liveness: LivenessResult,
        spoof: SpoofResult,
        behavior: BehaviorResult,
    ) -> list[dict]:
        alerts = []

        # ── Face count ────────────────────────────────────────────────────
        if detection.face_count == 0:
            a = self._fire("FACE_ABSENT", 1.0)
            if a: alerts.append(a)
            return alerts   # no point analysing further

        if detection.face_count > 1:
            a = self._fire("MULTIPLE_FACES", 1.0, {"count": detection.face_count})
            if a: alerts.append(a)

        # ── Spoof ─────────────────────────────────────────────────────────
        if spoof.label == "SPOOF":
            spoof_type = getattr(spoof, 'spoof_type', '')
            type_labels = {
                'ai_face': 'AI-generated face detected',
                'screen_replay': 'Screen/phone replay detected',
                'printed_photo': 'Printed photo attack detected',
            }
            a = self._fire("SPOOF_DETECTED", 1.0 - spoof.confidence, {
                "spoof_confidence": spoof.confidence,
                "method": spoof.method,
                "spoof_type": spoof_type,
                "description": type_labels.get(spoof_type, "Spoofing attempt detected"),
            })
            if a: alerts.append(a)

        # ── Head turned ───────────────────────────────────────────────────
        if liveness.head_turned:
            a = self._fire("HEAD_TURNED", 0.9, {
                "yaw": liveness.yaw,
                "pitch": liveness.pitch,
            })
            if a: alerts.append(a)

        # ── Gaze away (persistent: only alert after N seconds) ────────────
        if behavior.gaze_direction != "CENTER" and behavior.gaze_direction != "UNKNOWN":
            self._gaze_away_frames += 1
        else:
            self._gaze_away_frames = max(0, self._gaze_away_frames - 2)  # decay

        away_seconds = self._gaze_away_frames / self._fps_estimate
        if away_seconds >= settings.GAZE_OFF_SCREEN_SECONDS:
            a = self._fire("GAZE_AWAY", 0.85, {
                "direction":  behavior.gaze_direction,
                "duration_s": round(away_seconds, 1),
            })
            if a: alerts.append(a)

        # ── Looking down ──────────────────────────────────────────────────
        if behavior.gaze_direction == "DOWN":
            a = self._fire("LOOKING_DOWN", 0.8, {"duration_s": round(away_seconds, 1)})
            if a: alerts.append(a)

        # ── Low attention (persistent) ────────────────────────────────────
        if behavior.attention_score < settings.ATTENTION_LOW_THRESHOLD:
            self._low_attention_frames += 1
        else:
            self._low_attention_frames = max(0, self._low_attention_frames - 3)

        low_seconds = self._low_attention_frames / self._fps_estimate
        if low_seconds >= settings.ATTENTION_LOW_SECONDS:
            a = self._fire("LOW_ATTENTION", 0.8, {
                "score":      behavior.attention_score,
                "duration_s": round(low_seconds, 1),
            })
            if a: alerts.append(a)

        # ── Lip movement (talking) ────────────────────────────────────────
        if behavior.lip_moving:
            self._lip_movement_frames += 1
        else:
            self._lip_movement_frames = max(0, self._lip_movement_frames - 2)

        if self._lip_movement_frames > 15:  # >1.5s of talking
            a = self._fire("LIP_MOVEMENT", behavior.lip_movement_score, {
                "lip_score": behavior.lip_movement_score,
            })
            if a: alerts.append(a)

        # ── Excessive body movement ───────────────────────────────────────
        if behavior.excessive_movement:
            self._body_movement_frames += 1
        else:
            self._body_movement_frames = max(0, self._body_movement_frames - 3)

        if self._body_movement_frames > 8:
            a = self._fire("EXCESSIVE_MOVEMENT", 0.75, {
                "movement_delta": behavior.body_movement,
            })
            if a: alerts.append(a)

        # ── Blink absent (check every ~5s with no blink at all) ───────────
        if liveness.total_blinks == 0:
            self._no_blink_frames += 1
        else:
            self._no_blink_frames = 0

        if self._no_blink_frames > self._fps_estimate * 5:
            a = self._fire("BLINK_ABSENT", 0.6)
            if a: alerts.append(a)

        return alerts

    def reset(self):
        self._gaze_away_frames     = 0
        self._low_attention_frames = 0
        self._no_blink_frames      = 0
        self._lip_movement_frames  = 0
        self._body_movement_frames = 0
        self._alert_cooldown.clear()
