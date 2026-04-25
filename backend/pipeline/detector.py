"""
Face Detection Module — MediaPipe Tasks API (0.10.30+).
Returns face count and pixel-coordinate bounding boxes.
"""
import cv2
import numpy as np
from dataclasses import dataclass, field
import pathlib

import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

_MODEL_PATH = str(pathlib.Path(__file__).parent.parent.parent /
                  "backend" / "models" / "blaze_face_short_range.tflite")


@dataclass
class DetectionResult:
    face_count: int = 0
    bboxes: list[dict] = field(default_factory=list)   # [{x,y,w,h,score}]
    primary_bbox: dict | None = None


class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.5):
        opts = vision.FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=_MODEL_PATH),
            min_detection_confidence=min_detection_confidence,
        )
        self._detector = vision.FaceDetector.create_from_options(opts)

    def detect(self, frame: np.ndarray) -> DetectionResult:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self._detector.detect(mp_image)

        bboxes = []
        if results.detections:
            for det in results.detections:
                bb    = det.bounding_box
                score = det.categories[0].score if det.categories else 0.0
                # Tasks API bbox is already in pixel coords
                x  = max(0, bb.origin_x)
                y  = max(0, bb.origin_y)
                bw = min(bb.width,  w - x)
                bh = min(bb.height, h - y)
                bboxes.append({"x": x, "y": y, "w": bw, "h": bh, "score": float(score)})

        bboxes.sort(key=lambda b: b["score"], reverse=True)
        return DetectionResult(
            face_count=len(bboxes),
            bboxes=bboxes,
            primary_bbox=bboxes[0] if bboxes else None,
        )

    def close(self):
        self._detector.close()
