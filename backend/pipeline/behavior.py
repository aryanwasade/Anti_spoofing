"""
Behavior Analysis Module — Comprehensive real-time behavioral monitoring.

Tracks:
- Iris-based gaze direction (LEFT / CENTER / RIGHT / UP / DOWN)
- Eye contact score (camera-facing engagement)
- Lip movement detection (talking / silent)
- Body/shoulder movement via landmark delta
- Attention score: weighted composite of all above

Fixed: Added fallback gaze estimation from head pose when iris landmarks
       (indices 469-477) are unavailable (< 478 landmarks). Also added
       warm-up grace period for first 30 frames to prevent 0% attention.
"""
import numpy as np
from collections import deque, Counter
from dataclasses import dataclass, field
from backend.config import settings

# ── MediaPipe landmark indices ────────────────────────────────────────────────
# Iris (requires output_face_blendshapes=True in FaceLandmarker)
LEFT_IRIS    = [474, 475, 476, 477]
RIGHT_IRIS   = [469, 470, 471, 472]
LEFT_CORNERS  = [33, 133]
RIGHT_CORNERS = [362, 263]

# Lip landmarks (inner upper & lower lip)
UPPER_LIP = [13, 312, 311, 310, 415, 308]
LOWER_LIP = [14, 317, 402, 318, 324, 308]
LIP_TOP    = 13   # inner top
LIP_BOTTOM = 14   # inner bottom

# Shoulder approximation via cheek/jaw landmarks
LEFT_CHEEK  = 234
RIGHT_CHEEK = 454

# Nose tip for body position tracking
NOSE_TIP = 4


@dataclass
class BehaviorResult:
    gaze_direction: str = "UNKNOWN"     # CENTER | LEFT | RIGHT | UP | DOWN
    gaze_ratio: float = 0.5
    eye_contact_score: float = 0.0      # 0 when no face
    lip_moving: bool = False
    lip_movement_score: float = 0.0
    body_movement: float = 0.0
    excessive_movement: bool = False
    attention_score: float = 0.0        # 0 when no face
    is_attentive: bool = False
    movement_delta: float = 0.0


class BehaviorAnalyzer:
    def __init__(self, history_len: int = 60):
        self._prev_landmarks: list | None = None
        self._prev_nose_pos: tuple | None = None
        self._gaze_history: deque = deque(maxlen=history_len)
        self._attention_history: deque = deque(maxlen=history_len)
        self._lip_history: deque = deque(maxlen=20)
        self._prev_lip_dist: float = 0.0
        self._gaze_counter: Counter = Counter()
        self._total_gaze_frames: int = 0
        self._frames_processed: int = 0

    def reset(self):
        self._prev_landmarks = None
        self._prev_nose_pos = None
        self._gaze_history.clear()
        self._attention_history.clear()
        self._lip_history.clear()
        self._prev_lip_dist = 0.0
        self._gaze_counter.clear()
        self._total_gaze_frames = 0
        self._frames_processed = 0

    def get_gaze_distribution(self) -> dict:
        """Returns % time in each gaze direction (0–100)."""
        total = max(self._total_gaze_frames, 1)
        return {
            "center": round(self._gaze_counter["CENTER"] / total * 100, 1),
            "left":   round(self._gaze_counter["LEFT"]   / total * 100, 1),
            "right":  round(self._gaze_counter["RIGHT"]  / total * 100, 1),
            "up":     round(self._gaze_counter["UP"]     / total * 100, 1),
            "down":   round(self._gaze_counter["DOWN"]   / total * 100, 1),
        }

    def update(
        self,
        landmarks: list[tuple],
        yaw: float = 0.0,
        pitch: float = 0.0,
    ) -> BehaviorResult:
        result = BehaviorResult()
        self._frames_processed += 1

        has_iris = len(landmarks) >= 478

        if len(landmarks) < 468:
            # Too few landmarks — give warm-up score
            warmup = min(self._frames_processed / 30.0, 0.5)
            result.attention_score = warmup
            result.eye_contact_score = warmup
            self._attention_history.append(warmup)
            return result

        # ── 1. Gaze direction ─────────────────────────────────────────────
        if has_iris:
            # Full iris-based gaze (most accurate)
            def iris_ratio(iris_ids, corner_ids):
                cx = np.mean([landmarks[i][0] for i in iris_ids])
                lx = landmarks[corner_ids[0]][0]
                rx = landmarks[corner_ids[1]][0]
                width = rx - lx
                if width < 2:
                    return 0.5
                return float(np.clip((cx - lx) / width, 0.0, 1.0))

            l_r = iris_ratio(LEFT_IRIS,  LEFT_CORNERS)
            r_r = iris_ratio(RIGHT_IRIS, RIGHT_CORNERS)
            avg = (l_r + r_r) / 2.0
            result.gaze_ratio = round(avg, 4)

            if avg < 0.30:
                gaze = "LEFT"
            elif avg > 0.70:
                gaze = "RIGHT"
            elif pitch > 18:
                gaze = "DOWN"
            elif pitch < -18:
                gaze = "UP"
            else:
                gaze = "CENTER"
        else:
            # Fallback: use head pose to estimate gaze direction
            # (less accurate but better than UNKNOWN)
            result.gaze_ratio = 0.5
            if abs(yaw) < 12 and abs(pitch) < 12:
                gaze = "CENTER"
            elif yaw > 15:
                gaze = "RIGHT"
            elif yaw < -15:
                gaze = "LEFT"
            elif pitch > 18:
                gaze = "DOWN"
            elif pitch < -18:
                gaze = "UP"
            else:
                gaze = "CENTER"

        result.gaze_direction = gaze
        self._gaze_history.append(1.0 if gaze == "CENTER" else 0.0)
        self._gaze_counter[gaze] += 1
        self._total_gaze_frames += 1

        # ── 2. Eye contact score ───────────────────────────────────────────
        yaw_ok   = abs(yaw)   < settings.EYE_CONTACT_YAW_LIMIT
        pitch_ok = abs(pitch) < settings.EYE_CONTACT_PITCH_LIMIT
        gaze_ok  = gaze == "CENTER"

        if has_iris:
            avg_val = result.gaze_ratio
            iris_center_score = 1.0 - abs(avg_val - 0.5) * 3.0
            iris_center_score = float(np.clip(iris_center_score, 0.0, 1.0))
            eye_contact = iris_center_score * 0.5 + (0.25 if yaw_ok else 0.0) + (0.25 if pitch_ok else 0.0)
        else:
            # Fallback eye contact from head pose only
            eye_contact = (0.5 if gaze_ok else 0.1) + (0.25 if yaw_ok else 0.0) + (0.25 if pitch_ok else 0.0)

        result.eye_contact_score = round(float(np.clip(eye_contact, 0.0, 1.0)), 3)

        # ── 3. Lip movement (talking detection) ───────────────────────────
        lip_top_y    = landmarks[LIP_TOP][1]
        lip_bottom_y = landmarks[LIP_BOTTOM][1]
        l_eye_x = landmarks[LEFT_CORNERS[0]][0]
        r_eye_x = landmarks[RIGHT_CORNERS[1]][0]
        face_width = max(abs(r_eye_x - l_eye_x), 1)
        lip_dist_norm = abs(lip_bottom_y - lip_top_y) / face_width

        lip_delta = abs(lip_dist_norm - self._prev_lip_dist) if self._prev_lip_dist > 0 else 0.0
        self._prev_lip_dist = lip_dist_norm
        self._lip_history.append(lip_delta)

        avg_lip_delta = float(np.mean(self._lip_history)) if self._lip_history else 0.0
        result.lip_moving = avg_lip_delta > settings.LIP_MOVEMENT_THRESHOLD
        result.lip_movement_score = round(float(np.clip(avg_lip_delta / 0.02, 0.0, 1.0)), 3)

        # ── 4. Body / head movement via nose tip position ─────────────────
        nose_x, nose_y = landmarks[NOSE_TIP][0], landmarks[NOSE_TIP][1]
        if self._prev_nose_pos is not None:
            dx = nose_x - self._prev_nose_pos[0]
            dy = nose_y - self._prev_nose_pos[1]
            movement = float(np.sqrt(dx*dx + dy*dy))
        else:
            movement = 0.0
        self._prev_nose_pos = (nose_x, nose_y)

        result.body_movement  = round(movement, 2)
        result.movement_delta = result.body_movement
        result.excessive_movement = movement > settings.BODY_MOVEMENT_THRESHOLD

        # ── 5. Attention score — weighted composite ────────────────────────
        on_screen_score = float(np.mean(self._gaze_history)) if self._gaze_history else 0.8

        # Grace period: first 30 frames get boosted on-screen score
        if self._frames_processed <= 30:
            on_screen_score = max(on_screen_score, 0.6)

        head_fwd_score = 1.0 if (abs(yaw) < 20 and abs(pitch) < 15) else max(0.0, 1.0 - abs(yaw)/50.0)
        ec_score = result.eye_contact_score
        still_score = 0.0 if result.excessive_movement else 1.0

        attention = (
            0.40 * on_screen_score +
            0.25 * head_fwd_score  +
            0.25 * ec_score        +
            0.10 * still_score
        )
        result.attention_score = round(float(np.clip(attention, 0.0, 1.0)), 3)
        result.is_attentive = result.attention_score >= settings.ATTENTION_LOW_THRESHOLD

        self._attention_history.append(result.attention_score)
        self._prev_landmarks = landmarks

        return result
