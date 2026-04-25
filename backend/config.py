"""
Central configuration for the Antispoofing pipeline.
All thresholds and model paths live here for easy tuning.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Antispoofing Interview System"
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./antispoofing.db"

    # ── Liveness thresholds ───────────────────────────────────────────────
    EAR_THRESHOLD: float = 0.22          # below → eye closed (calibrated for webcam)
    EAR_CONSEC_FRAMES: int = 2           # frames for blink to register
    MIN_BLINKS_FOR_LIVENESS: int = 2     # needed to confirm liveness
    HEAD_POSE_YAW_LIMIT: float = 30.0    # degrees before alert
    HEAD_POSE_PITCH_LIMIT: float = 25.0
    LIVENESS_WINDOW_FRAMES: int = 90     # rolling window for blink rate (at 10fps = 9s)

    # ── Spoof thresholds ─────────────────────────────────────────────────
    # Recalibrated: real webcam faces score 0.40-0.65 with LBP heuristic
    SPOOF_CONFIDENCE_THRESHOLD: float = 0.38
    SPOOF_MODEL_PATH: str = "backend/models/spoof_model.h5"

    # ── Behavior thresholds ──────────────────────────────────────────────
    GAZE_OFF_SCREEN_SECONDS: float = 2.5     # alert if gaze away longer than this
    ATTENTION_LOW_THRESHOLD: float = 0.35    # below → low attention
    ATTENTION_LOW_SECONDS: float = 8.0       # alert if low attention persists
    LIP_MOVEMENT_THRESHOLD: float = 0.006    # normalized lip distance delta
    BODY_MOVEMENT_THRESHOLD: float = 12.0    # pixel movement delta for body alert
    EYE_CONTACT_YAW_LIMIT: float = 12.0      # degrees: within this = eye contact
    EYE_CONTACT_PITCH_LIMIT: float = 10.0

    # ── Alert weights (for final risk score) ─────────────────────────────
    ALERT_WEIGHTS: dict = {
        "FACE_ABSENT":        1.5,
        "MULTIPLE_FACES":     3.0,
        "BLINK_ABSENT":       0.5,
        "GAZE_AWAY":          1.0,
        "LOW_ATTENTION":      0.8,
        "SPOOF_DETECTED":     5.0,
        "HEAD_TURNED":        1.2,
        "LIP_MOVEMENT":       0.7,
        "EXCESSIVE_MOVEMENT": 0.6,
        "LOOKING_DOWN":       0.9,
    }

    class Config:
        env_file = ".env"


settings = Settings()
