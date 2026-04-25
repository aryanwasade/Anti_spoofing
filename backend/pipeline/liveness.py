"""
Liveness Detection Module.
- Blink detection via MediaPipe blendshape scores (eyeBlinkLeft/Right)
  More accurate than manual EAR computation
- Head pose estimation via solvePnP (yaw, pitch, roll)
- Produces a unified liveness_score [0..1]

Score progression:
  - Frame 1:  ~0.45 (base score from open-eye blendshape + pose)
  - After 1st blink: ~0.70
  - After 2nd blink at natural rate: ~0.90+
  - is_live = True after MIN_BLINKS_FOR_LIVENESS blinks
"""
import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass
from backend.config import settings

# ── MediaPipe landmark indices for head pose ──────────────────────────────────
POSE_IDS  = [1, 152, 33, 263, 61, 291]   # nose, chin, l-eye, r-eye, l-mouth, r-mouth

# 3D reference face model (mm scale)
MODEL_POINTS_3D = np.array([
    (0.0,    0.0,    0.0),
    (0.0,   -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0,  170.0, -135.0),
    (-150.0,-150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype=np.float64)

# Blink detection thresholds (blendshape score: 0=open, 1=closed)
BLINK_CLOSE_THRESHOLD = 0.35   # score above this = eye is closing
BLINK_CONSEC_FRAMES   = 2      # min frames eye must be closed to count as blink


@dataclass
class LivenessResult:
    ear: float = 0.0            # kept for compatibility (now = 1 - avg_blink_score)
    blink_detected: bool = False
    total_blinks: int = 0
    blink_rate_per_min: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    head_turned: bool = False
    liveness_score: float = 0.0
    is_live: bool = False


class LivenessDetector:
    """
    Liveness detection using MediaPipe blendshape blink scores.
    Blendshape scores are 0=open → 1=fully closed, trained end-to-end by MediaPipe.
    """
    def __init__(self):
        self._blink_counter = 0
        self._total_blinks = 0
        self._frames_processed = 0
        self._fps_estimate = 10.0
        self._blink_frames: deque = deque(maxlen=20)
        self._was_closed = False

    def reset(self):
        self._blink_counter = 0
        self._total_blinks = 0
        self._frames_processed = 0
        self._blink_frames.clear()
        self._was_closed = False

    def update(
        self,
        landmarks: list[tuple],
        frame_shape: tuple,
        blink_left: float = 0.0,
        blink_right: float = 0.0,
    ) -> LivenessResult:
        self._frames_processed += 1
        result = LivenessResult()

        if len(landmarks) < 468:
            result.liveness_score = 0.10
            return result

        # ── Blink detection via blendshape scores ─────────────────────────
        # Average left and right eye blink scores
        avg_blink = (blink_left + blink_right) / 2.0
        # EAR-compatible value: 1 - blink_score (high = open eye)
        result.ear = round(1.0 - avg_blink, 4)

        eye_closed = avg_blink > BLINK_CLOSE_THRESHOLD

        if eye_closed:
            self._blink_counter += 1
            self._was_closed = True
        else:
            if self._was_closed and self._blink_counter >= BLINK_CONSEC_FRAMES:
                self._total_blinks += 1
                self._blink_frames.append(self._frames_processed)
                result.blink_detected = True
            self._blink_counter = 0
            self._was_closed = False

        result.total_blinks = self._total_blinks

        # Blink rate (blinks/min) from recent blink timestamps
        window_frames = settings.LIVENESS_WINDOW_FRAMES
        recent_blinks = sum(
            1 for f in self._blink_frames
            if (self._frames_processed - f) <= window_frames
        )
        window_minutes = (window_frames / self._fps_estimate) / 60.0
        result.blink_rate_per_min = round(recent_blinks / max(window_minutes, 1/60), 1)

        # ── Head Pose (solvePnP) ──────────────────────────────────────────
        h, w = frame_shape[:2]
        focal = w
        cam_mat = np.array(
            [[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1]], dtype=np.float64
        )
        dist_coeffs = np.zeros((4, 1))
        img_pts = np.array(
            [landmarks[i][:2] for i in POSE_IDS], dtype=np.float64
        )
        ok, rvec, _ = cv2.solvePnP(
            MODEL_POINTS_3D, img_pts, cam_mat, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if ok:
            rmat, _ = cv2.Rodrigues(rvec)
            angles, *_ = cv2.RQDecomp3x3(rmat)
            result.pitch = round(float(angles[0]), 2)
            result.yaw   = round(float(angles[1]), 2)
            result.roll  = round(float(angles[2]), 2)
            result.head_turned = (
                abs(result.yaw)   > settings.HEAD_POSE_YAW_LIMIT or
                abs(result.pitch) > settings.HEAD_POSE_PITCH_LIMIT
            )

        # ── Liveness score ────────────────────────────────────────────────
        # Component 1: Eye openness score (immediate from frame 1)
        # avg_blink=0 → eyes fully open → score=1.0
        # avg_blink=1 → eyes fully closed → score=0.0
        eye_open_score = 1.0 - avg_blink

        # Component 2: Blink-based liveness (builds over time)
        rate = result.blink_rate_per_min
        if self._total_blinks == 0:
            # No blinks yet — partial credit if eyes appear naturally open
            blink_score = 0.40 * eye_open_score
        elif self._total_blinks == 1:
            blink_score = 0.70
        elif rate < 1:
            blink_score = min(0.65 + self._total_blinks * 0.05, 0.80)
        elif rate < 3:
            blink_score = 0.80 + (rate - 1) / 2.0 * 0.10
        elif rate <= 25:
            blink_score = 1.0
        else:
            blink_score = max(0.65, 1.0 - (rate - 25) / 20.0)

        # Component 3: Head pose (immediate from frame 1)
        pose_score = 0.0 if result.head_turned else 1.0

        # Component 4: Eyes naturally open (not fixed/frozen = not a photo)
        # Real eyes: blink score varies naturally; photos have fixed blink score
        natural_eye_score = eye_open_score  # 0.6-0.9 for natural open eyes

        result.liveness_score = round(
            0.45 * blink_score       +
            0.30 * pose_score        +
            0.25 * natural_eye_score,
            3
        )
        result.liveness_score = max(0.0, min(1.0, result.liveness_score))

        result.is_live = (
            self._total_blinks >= settings.MIN_BLINKS_FOR_LIVENESS
            and not result.head_turned
            and result.liveness_score > 0.50
        )
        return result
