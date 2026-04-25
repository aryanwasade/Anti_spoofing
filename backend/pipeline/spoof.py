"""
Spoof Detection Module — Multi-layer heuristic for real webcam feeds.

Detection layers:
  1. Texture/LBP analysis (real vs printed photo)
  2. Moire pattern detection via FFT (screen replay)
  3. Skin-tone naturalness (AI/deepfake have unnaturally uniform skin)
  4. Face symmetry analysis (AI faces are more symmetric than real faces)
  5. Temporal jitter (AI video is too smooth; real webcam has micro-jitter)
  6. Optional: CNN model if spoof_model.h5 is present

Confidence: 1.0 = definitely REAL, 0.0 = definitely SPOOF
Threshold: score >= 0.38 → REAL, else SPOOF
"""
import os
import cv2
import numpy as np
from dataclasses import dataclass
from collections import deque
from backend.config import settings


@dataclass
class SpoofResult:
    label: str = "UNKNOWN"       # "REAL" | "SPOOF" | "UNKNOWN"
    confidence: float = 0.5      # 1.0 = very confident it's REAL
    method: str = "heuristic"    # "heuristic" | "cnn"
    spoof_type: str = ""         # "printed_photo" | "screen_replay" | "ai_face" | ""


# ── Texture analysis helpers ──────────────────────────────────────────────────

def _lbp_histogram(gray: np.ndarray) -> np.ndarray:
    """Compute uniform LBP histogram (8 neighbours, radius 1)."""
    h, w = gray.shape
    lbp = np.zeros_like(gray, dtype=np.uint8)
    offsets = [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]
    center = gray[1:-1, 1:-1].astype(np.int16)
    bits = []
    for dy, dx in offsets:
        nb = gray[1+dy:h-1+dy, 1+dx:w-1+dx].astype(np.int16)
        bits.append((nb >= center).astype(np.uint8))
    for i, b in enumerate(bits):
        lbp[1:-1, 1:-1] += (b << i)
    hist, _ = np.histogram(lbp, bins=256, range=(0, 256), density=True)
    return hist


def _color_diversity_score(face_roi: np.ndarray) -> float:
    """
    Real faces have diverse skin-tone color variation.
    Printed photos/screens have compressed, limited color palette.
    Returns 0..1 where 1 = diverse (real-like).
    """
    small = cv2.resize(face_roi, (32, 32))
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)
    a_var = float(np.var(lab[:, :, 1]))
    b_var = float(np.var(lab[:, :, 2]))
    color_score = min((a_var + b_var) / 80.0, 1.0)
    return color_score


def _texture_score(face_roi: np.ndarray) -> float:
    """
    Returns a score in [0..1] where higher = more likely REAL.
    """
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (64, 64))

    # 1. LBP entropy — real faces have higher entropy
    hist = _lbp_histogram(small)
    hist_nonzero = hist[hist > 0]
    entropy = -np.sum(hist_nonzero * np.log2(hist_nonzero + 1e-10))
    entropy_norm = float(np.clip(entropy / 7.5, 0.0, 1.0))

    # 2. Laplacian variance (sharpness / micro-texture)
    laplacian_var = cv2.Laplacian(small, cv2.CV_64F).var()
    grad_norm = float(np.clip(laplacian_var / 400.0, 0.0, 1.0))

    # 3. FFT high-frequency ratio — screens show moire; prints are blurry
    fft = np.fft.fft2(small)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    cy, cx = small.shape[0] // 2, small.shape[1] // 2
    r = 8
    low = magnitude[cy-r:cy+r, cx-r:cx+r].sum()
    total = magnitude.sum() + 1e-6
    high_ratio = 1.0 - low / total
    high_norm = float(np.clip(high_ratio * 3.5, 0.0, 1.0))

    # 4. Color diversity
    color_div = _color_diversity_score(face_roi)

    score = (
        0.35 * entropy_norm +
        0.30 * grad_norm    +
        0.20 * high_norm    +
        0.15 * color_div
    )
    return float(np.clip(score, 0.0, 1.0))


def _screen_replay_score(face_roi: np.ndarray) -> float:
    """
    Detect screen replay attacks (phone held to camera, monitor replay).
    Returns 0..1 where LOW score = suspicious (screen replay detected).

    Screens exhibit:
    - Moire interference patterns (regular pixel grid beating with camera sensor)
    - Strong spectral peaks in mid-frequency FFT bands
    - Reduced color gamut (sRGB vs full camera gamut)
    """
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128)).astype(np.float32)

    # FFT analysis for moire patterns
    fft = np.fft.fft2(resized)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.log1p(np.abs(fft_shift))

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2

    # Band analysis: inner (DC), mid (moire zone), outer (noise)
    inner_mask = np.zeros_like(magnitude)
    mid_mask   = np.zeros_like(magnitude)

    for y in range(h):
        for x in range(w):
            d = np.sqrt((y - cy)**2 + (x - cx)**2)
            if d < 8:
                inner_mask[y, x] = 1
            elif 15 < d < 45:
                mid_mask[y, x] = 1

    inner_energy = float(np.sum(magnitude * inner_mask))
    mid_energy   = float(np.sum(magnitude * mid_mask))
    total_energy = float(np.sum(magnitude)) + 1e-6

    # High mid-band energy relative to total → moire → screen
    mid_ratio = mid_energy / total_energy

    # Moire indicator: ratio above 0.35 is suspicious
    moire_penalty = float(np.clip((mid_ratio - 0.25) / 0.20, 0.0, 1.0))

    # Check for uniform brightness bands (scan lines on some monitors)
    row_var = float(np.var(np.mean(resized, axis=1)))
    scanline_penalty = float(np.clip(1.0 - row_var / 100.0, 0.0, 0.5))

    # Score: 1.0 = real, lower = more screen-like
    screen_score = 1.0 - (0.7 * moire_penalty + 0.3 * scanline_penalty)
    return float(np.clip(screen_score, 0.0, 1.0))


def _ai_face_score(face_roi: np.ndarray) -> float:
    """
    Detect AI-generated / deepfake faces.
    Returns 0..1 where LOW score = suspicious (AI face detected).

    AI/GAN faces exhibit:
    - Near-perfect bilateral symmetry (real faces have slight asymmetry)
    - Unnaturally smooth skin texture with low high-frequency noise
    - Blending artifacts at hair/background boundaries (GAN boundary)
    - Overly uniform skin tone distribution in HSV space
    """
    if face_roi is None or face_roi.size == 0:
        return 1.0

    roi = cv2.resize(face_roi, (128, 128))
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape

    # ── 1. Symmetry analysis ──────────────────────────────────────────────
    # Real faces have slight left-right asymmetry
    left_half  = gray[:, :w//2]
    right_half = np.fliplr(gray[:, w//2:])
    # Pad to same width
    min_w = min(left_half.shape[1], right_half.shape[1])
    left_half  = left_half[:, :min_w]
    right_half = right_half[:, :min_w]

    symmetry_diff = float(np.mean(np.abs(left_half - right_half)))
    # Real faces: diff ~15-40; AI faces: diff ~2-12
    # Normalize: very low diff = suspicious
    symmetry_score = float(np.clip((symmetry_diff - 5.0) / 30.0, 0.0, 1.0))

    # ── 2. Skin smoothness (AI = too smooth) ─────────────────────────────
    # Real skin has micro-texture. AI skin is too smooth at high frequencies.
    # Measure: local standard deviation in small patches
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    noise = gray - blurred
    noise_std = float(np.std(noise))
    # Real face: std ~8-20; AI face: std ~1-5 (unnaturally smooth)
    smoothness_score = float(np.clip((noise_std - 2.0) / 15.0, 0.0, 1.0))

    # ── 3. Boundary / edge artifacts (GAN blending) ───────────────────────
    # GAN faces often have artifacts at boundaries — unnatural edge sharpness
    edges = cv2.Canny(cv2.convertScaleAbs(gray), 50, 150)
    # Check edge distribution: GAN artifacts cluster at specific locations
    top_edge_density    = float(np.mean(edges[:8, :]))    # very top (hair/forehead)
    bottom_edge_density = float(np.mean(edges[-8:, :]))   # very bottom (chin/neck)
    center_edge_density = float(np.mean(edges[h//4:3*h//4, w//4:3*w//4]))

    # Boundary anomaly: edges at periphery much stronger than center → GAN artifact
    if center_edge_density > 1.0:
        boundary_ratio = (top_edge_density + bottom_edge_density) / (2 * center_edge_density + 1e-6)
    else:
        boundary_ratio = 1.0
    boundary_score = float(np.clip(1.0 - (boundary_ratio - 1.2) / 2.0, 0.0, 1.0))

    # ── 4. Skin tone uniformity (AI has unnaturally uniform skin) ─────────
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).astype(np.float32)
    # Focus on saturation channel — skin area
    sat = hsv[:, :, 1]
    sat_std = float(np.std(sat))
    # Real skin: saturation varies naturally. AI skin: very uniform.
    skin_score = float(np.clip(sat_std / 30.0, 0.0, 1.0))

    # ── Combine ────────────────────────────────────────────────────────────
    ai_score = (
        0.30 * symmetry_score   +
        0.35 * smoothness_score +
        0.20 * boundary_score   +
        0.15 * skin_score
    )
    return float(np.clip(ai_score, 0.0, 1.0))


def _temporal_jitter_score(curr_frame: np.ndarray, prev_frame: np.ndarray) -> float:
    """
    Real webcam feeds have natural micro-jitter and compression noise.
    AI video / pre-recorded replays are unnaturally smooth between frames.
    Returns 0..1 where LOW = suspiciously smooth (possible AI/replay).
    """
    if prev_frame is None or curr_frame.shape != prev_frame.shape:
        return 1.0  # neutral when no previous frame

    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    diff = np.abs(curr_gray - prev_gray)
    mean_diff = float(np.mean(diff))

    # Real webcam: mean diff ~2-15 per frame
    # AI video or still image: mean diff ~0-1 (nearly identical frames)
    jitter_score = float(np.clip(mean_diff / 8.0, 0.0, 1.0))
    return jitter_score


# ── Main detector class ───────────────────────────────────────────────────────

class SpoofDetector:
    def __init__(self):
        self._model = None
        self._method = "heuristic"
        self._score_history: deque = deque(maxlen=10)  # smooth over 10 frames
        self._prev_face_roi: np.ndarray | None = None
        self._try_load_model()

    def _try_load_model(self):
        path = settings.SPOOF_MODEL_PATH
        if os.path.exists(path):
            try:
                import tensorflow as tf
                self._model = tf.keras.models.load_model(path)
                self._method = "cnn"
                print(f"[SpoofDetector] Loaded CNN model from {path}")
            except Exception as e:
                print(f"[SpoofDetector] Could not load model ({e}). Using heuristic.")

    def predict(self, face_roi: np.ndarray) -> SpoofResult:
        if face_roi is None or face_roi.size == 0:
            return SpoofResult()

        if self._method == "cnn" and self._model is not None:
            return self._predict_cnn(face_roi)
        return self._predict_heuristic(face_roi)

    def _predict_heuristic(self, face_roi: np.ndarray) -> SpoofResult:
        # ── Run all detection layers ───────────────────────────────────────
        texture  = _texture_score(face_roi)           # real texture vs flat
        screen   = _screen_replay_score(face_roi)     # moire / screen replay
        ai_face  = _ai_face_score(face_roi)           # AI / deepfake face
        temporal = _temporal_jitter_score(face_roi, self._prev_face_roi)

        self._prev_face_roi = face_roi.copy()

        # ── Weighted combination ───────────────────────────────────────────
        # Texture is most reliable; temporal helps catch AI video
        raw_score = (
            0.35 * texture  +
            0.25 * screen   +
            0.25 * ai_face  +
            0.15 * temporal
        )

        # ── Temporal smoothing over recent frames ──────────────────────────
        self._score_history.append(raw_score)
        score = float(np.mean(self._score_history))

        # ── Determine label and spoof type ────────────────────────────────
        label = "REAL" if score >= settings.SPOOF_CONFIDENCE_THRESHOLD else "SPOOF"

        # Identify the dominant spoof signal for detailed reporting
        spoof_type = ""
        if label == "SPOOF":
            scores = {"printed_photo": texture, "screen_replay": screen, "ai_face": ai_face}
            spoof_type = min(scores, key=scores.get)

        return SpoofResult(
            label=label,
            confidence=round(score, 4),
            method="heuristic",
            spoof_type=spoof_type,
        )

    def _predict_cnn(self, face_roi: np.ndarray) -> SpoofResult:
        import tensorflow as tf
        img = cv2.resize(face_roi, (224, 224)).astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)
        prob = float(self._model.predict(img, verbose=0)[0][0])
        label = "REAL" if prob >= settings.SPOOF_CONFIDENCE_THRESHOLD else "SPOOF"
        return SpoofResult(label=label, confidence=round(prob, 4), method="cnn")
