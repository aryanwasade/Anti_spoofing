"""
Image utility helpers: base64 encode/decode, frame resize.
"""
import base64
import cv2
import numpy as np


def b64_to_frame(b64_string: str) -> np.ndarray | None:
    """Decode a base64 data-URI or raw base64 string to a BGR numpy array."""
    try:
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_string)
        nparr = np.frombuffer(img_bytes, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def frame_to_b64(frame: np.ndarray, quality: int = 70) -> str:
    """Encode a BGR numpy array as a JPEG base64 data-URI string."""
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


def resize_frame(frame: np.ndarray, width: int = 640) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= width:
        return frame
    ratio = width / w
    return cv2.resize(frame, (width, int(h * ratio)))


def crop_face(frame: np.ndarray, bbox: dict, padding: float = 0.2) -> np.ndarray | None:
    """Crop face ROI with optional padding from a {x,y,w,h} bounding box dict."""
    h, w = frame.shape[:2]
    x, y, bw, bh = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    pad_x = int(bw * padding)
    pad_y = int(bh * padding)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + bw + pad_x)
    y2 = min(h, y + bh + pad_y)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return roi
