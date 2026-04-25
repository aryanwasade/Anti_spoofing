"""
Landmark Detection Module — MediaPipe Tasks API (0.10.30+).
Uses FaceLandmarker to extract 478 3D facial landmarks + iris + blendshapes.

IMPORTANT: output_face_blendshapes=True serves TWO purposes:
  1. Gets the full 478-point output including iris landmarks (469-477)
     needed for gaze detection in behavior.py
  2. Gets blendshape scores including eyeBlinkLeft / eyeBlinkRight
     which are used for highly-accurate blink detection in liveness.py
     (much more reliable than manual EAR computation)
"""
import cv2
import numpy as np
import pathlib
from dataclasses import dataclass, field

import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

_MODEL_PATH = str(pathlib.Path(__file__).parent.parent.parent /
                  "backend" / "models" / "face_landmarker.task")


@dataclass
class LandmarkResult:
    found: bool = False
    landmarks: list[tuple[int, int, float]] = field(default_factory=list)
    # Each entry: (pixel_x, pixel_y, z_normalized)

    # Blendshape-based blink scores (0.0=open, 1.0=fully closed)
    # These are much more accurate than manual EAR computation
    blink_left: float = 0.0
    blink_right: float = 0.0


class LandmarkDetector:
    def __init__(
        self,
        max_num_faces: int = 1,
        min_detection_confidence: float = 0.4,
        min_tracking_confidence: float = 0.4,
    ):
        opts = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_MODEL_PATH),
            # CRITICAL: True → 478 landmarks (iris) + blendshape blink scores
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=False,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(opts)

        # Blendshape name → index cache (populated on first detect)
        self._blink_left_idx: int | None = None
        self._blink_right_idx: int | None = None

    def _find_blendshape_indices(self, blendshapes) -> None:
        """Cache the indices of eyeBlinkLeft and eyeBlinkRight blendshapes."""
        for i, bs in enumerate(blendshapes):
            if bs.category_name == "eyeBlinkLeft":
                self._blink_left_idx = i
            elif bs.category_name == "eyeBlinkRight":
                self._blink_right_idx = i
            if self._blink_left_idx is not None and self._blink_right_idx is not None:
                break

    def detect(self, frame: np.ndarray) -> LandmarkResult:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self._landmarker.detect(mp_image)

        if not results.face_landmarks:
            return LandmarkResult(found=False)

        face = results.face_landmarks[0]
        pts = [
            (int(lm.x * w), int(lm.y * h), float(lm.z))
            for lm in face
        ]

        result = LandmarkResult(found=True, landmarks=pts)

        # Extract blink scores from blendshapes
        if results.face_blendshapes:
            bshapes = results.face_blendshapes[0]
            # Cache indices on first call
            if self._blink_left_idx is None:
                self._find_blendshape_indices(bshapes)

            if self._blink_left_idx is not None:
                result.blink_left = float(bshapes[self._blink_left_idx].score)
            if self._blink_right_idx is not None:
                result.blink_right = float(bshapes[self._blink_right_idx].score)

        return result

    def close(self):
        self._landmarker.close()
