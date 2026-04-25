"""
Pipeline Runner — orchestrates all stages for a single frame.
Returns a unified FrameResult dataclass.
"""
import numpy as np
from dataclasses import dataclass, field
from backend.pipeline.detector  import FaceDetector,   DetectionResult
from backend.pipeline.landmarks import LandmarkDetector, LandmarkResult
from backend.pipeline.liveness  import LivenessDetector, LivenessResult
from backend.pipeline.spoof     import SpoofDetector,  SpoofResult
from backend.pipeline.behavior  import BehaviorAnalyzer, BehaviorResult
from backend.pipeline.alerts    import AlertEngine
from backend.utils.image        import crop_face


@dataclass
class FrameResult:
    # ── Detection ─────────────────────────────────────────────────────────
    face_count: int = 0
    face_bbox: dict | None = None

    # ── Liveness ──────────────────────────────────────────────────────────
    ear: float = 0.0
    blink_detected: bool = False
    total_blinks: int = 0
    blink_rate_per_min: float = 0.0
    liveness_score: float = 0.0
    is_live: bool = False
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    head_turned: bool = False

    # ── Spoof ─────────────────────────────────────────────────────────────
    spoof_label: str = "UNKNOWN"
    spoof_confidence: float = 0.5
    spoof_method: str = "heuristic"
    spoof_type: str = ""  # "printed_photo" | "screen_replay" | "ai_face" | ""

    # ── Behavior ─────────────────────────────────────────────────────────────
    gaze_direction: str = "UNKNOWN"
    attention_score: float = 0.0      # 0 = not attentive / no face
    is_attentive: bool = False
    eye_contact_score: float = 0.0    # 0 = no eye contact / no face
    lip_moving: bool = False
    lip_movement_score: float = 0.0
    body_movement: float = 0.0
    excessive_movement: bool = False
    movement_delta: float = 0.0   # legacy alias

    # ── Composite ─────────────────────────────────────────────────────────────
    trust_score: float = 0.0      # 0 = untrusted (default safe)

    # ── Alerts ────────────────────────────────────────────────────────────
    alerts: list[dict] = field(default_factory=list)


class AnalysisPipeline:
    """
    Stateful pipeline: maintains per-session state (blink counts, alert timers).
    Create one instance per WebSocket session.
    """

    def __init__(self):
        self._detector  = FaceDetector()
        self._landmarks = LandmarkDetector()
        self._liveness  = LivenessDetector()
        self._spoof     = SpoofDetector()
        self._behavior  = BehaviorAnalyzer()
        self._alerter   = AlertEngine()

    def process(self, frame: np.ndarray) -> FrameResult:
        result = FrameResult()

        # Stage 1: Face detection
        det = self._detector.detect(frame)
        result.face_count = det.face_count
        result.face_bbox  = det.primary_bbox

        if det.face_count == 0:
            # No face detected — all behavioral metrics drop to 0
            # Mark as SPOOF: candidate may have left, covered camera, or
            # is showing a static image/phone where face detection fails
            result.attention_score   = 0.0
            result.eye_contact_score = 0.0
            result.liveness_score    = 0.0
            result.is_attentive      = False
            result.trust_score       = 0.0
            result.spoof_label       = "SPOOF"
            result.spoof_confidence  = 0.0
            result.spoof_type        = "no_face"
            result.gaze_direction    = "UNKNOWN"
            result.alerts = self._alerter.evaluate(
                det,
                LivenessResult(),
                SpoofResult(label="SPOOF", confidence=0.0, spoof_type="no_face"),
                BehaviorResult(),
            )
            return result

        # Stage 2: Landmark extraction
        lm_res: LandmarkResult = self._landmarks.detect(frame)

        # Stage 3: Liveness
        if lm_res.found:
            liv: LivenessResult = self._liveness.update(
                lm_res.landmarks,
                frame.shape,
                blink_left=lm_res.blink_left,
                blink_right=lm_res.blink_right,
            )
            result.ear               = liv.ear
            result.blink_detected    = liv.blink_detected
            result.total_blinks      = liv.total_blinks
            result.blink_rate_per_min = liv.blink_rate_per_min
            result.liveness_score    = liv.liveness_score
            result.is_live           = liv.is_live
            result.pitch             = liv.pitch
            result.yaw               = liv.yaw
            result.roll              = liv.roll
            result.head_turned       = liv.head_turned
        else:
            liv = LivenessResult()

        # Stage 4: Spoof detection (on cropped face ROI)
        face_roi = crop_face(frame, det.primary_bbox) if det.primary_bbox else None
        spoof: SpoofResult = self._spoof.predict(face_roi)
        result.spoof_label       = spoof.label
        result.spoof_confidence  = spoof.confidence
        result.spoof_method      = spoof.method
        result.spoof_type        = getattr(spoof, 'spoof_type', '')

        # Stage 5: Behavior analysis
        if lm_res.found:
            beh: BehaviorResult = self._behavior.update(
                lm_res.landmarks, yaw=result.yaw, pitch=result.pitch
            )
            result.gaze_direction    = beh.gaze_direction
            result.attention_score   = beh.attention_score
            result.is_attentive      = beh.is_attentive
            result.eye_contact_score = beh.eye_contact_score
            result.lip_moving        = beh.lip_moving
            result.lip_movement_score = beh.lip_movement_score
            result.body_movement     = beh.body_movement
            result.excessive_movement = beh.excessive_movement
            result.movement_delta    = beh.movement_delta
        else:
            # Face detected but landmarks failed — set behavior to 0
            beh = BehaviorResult()
            result.attention_score   = 0.0
            result.eye_contact_score = 0.0
            result.is_attentive      = False

        # Stage 6: Trust score — composite metric (0..1)
        # Liveness 30% + Attention 40% + Anti-spoof 30%
        # SPOOF: score penalized heavily
        # UNKNOWN: use raw confidence (0.5 default = 15% contribution)
        # REAL: full 30% contribution
        if spoof.label == "REAL":
            spoof_ok = 1.0
        elif spoof.label == "SPOOF":
            spoof_ok = 0.0
        else:  # UNKNOWN — give partial credit
            spoof_ok = spoof.confidence  # 0.5 default

        result.trust_score = round(
            0.30 * result.liveness_score +
            0.40 * result.attention_score +
            0.30 * spoof_ok,
            3
        )

        # Stage 7: Alert engine
        result.alerts = self._alerter.evaluate(det, liv, spoof, beh)
        return result

    def get_gaze_distribution(self) -> dict:
        return self._behavior.get_gaze_distribution()

    def reset(self):
        self._liveness.reset()
        self._behavior.reset()
        self._alerter.reset()

    def close(self):
        self._detector.close()
        self._landmarks.close()
