# 🛡️ Antispoofing in Real-Time Interview and Analysis System

A full-stack, AI-powered interview monitoring platform that performs real-time:
- **Face detection** (MediaPipe)
- **Liveness detection** (EAR blink + head pose)
- **Spoof detection** (LBP/FFT heuristic + optional CNN)
- **Behavior analysis** (gaze, attention score)
- **Alert generation** and **session reports**

---

## 🚀 Quick Start (Windows)

```
Double-click start.bat
```

Or manually:

### Backend
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

- **Frontend**: http://localhost:5173  
- **Backend API**: http://localhost:8000  
- **API Docs (Swagger)**: http://localhost:8000/docs  

---

## 📁 Project Structure

```
antispoofing11/
├── backend/
│   ├── main.py              ← FastAPI app entry
│   ├── config.py            ← All thresholds & settings
│   ├── database.py          ← SQLite + SQLAlchemy
│   ├── models/db_models.py  ← ORM: Session, AlertEvent
│   ├── pipeline/
│   │   ├── detector.py      ← Face detection (MediaPipe)
│   │   ├── landmarks.py     ← Face mesh (468 landmarks)
│   │   ├── liveness.py      ← EAR blinks + head pose
│   │   ├── spoof.py         ← Texture + CNN spoof detect
│   │   ├── behavior.py      ← Gaze + attention scoring
│   │   ├── alerts.py        ← Alert rule engine
│   │   └── runner.py        ← Pipeline orchestrator
│   ├── routers/
│   │   ├── session.py       ← Session REST endpoints
│   │   ├── report.py        ← Report generation endpoint
│   │   └── ws.py            ← WebSocket video stream
│   └── utils/
│       ├── image.py         ← Base64 encode/decode helpers
│       └── report_gen.py    ← JSON report builder
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── HomePage.jsx       ← Landing + session start
│       │   ├── CandidatePage.jsx  ← Live webcam view
│       │   └── InterviewerPage.jsx← Dashboard + reports
│       ├── components/
│       │   ├── AlertPanel.jsx     ← Real-time alert feed
│       │   ├── AttentionChart.jsx ← Line chart
│       │   └── ScoreBadge.jsx     ← Score display
│       └── hooks/
│           ├── useWebcam.js       ← getUserMedia + capture
│           └── useWebSocket.js    ← WS lifecycle
├── training/
│   ├── train_spoof.py       ← MobileNetV2 fine-tuning
│   └── preprocess.py        ← Face crop + resize dataset
├── docker-compose.yml
├── requirements.txt
└── start.bat                ← Windows one-click start
```

---

## 🧠 Training the Spoof CNN (Optional)

1. Download a dataset (e.g., NUAA, Replay-Attack, CelebA-Spoof)
2. Preprocess:
   ```
   python training/preprocess.py --src /path/to/raw_real  --dst training/data --label real
   python training/preprocess.py --src /path/to/raw_spoof --dst training/data --label spoof
   ```
3. Train:
   ```
   python training/train_spoof.py --data training/data --epochs 20
   ```
4. Model saves to `backend/models/spoof_model.h5` — auto-loaded on next backend start.

---

## ⚙️ Configuration

Edit `backend/config.py` to tune thresholds:
- `EAR_THRESHOLD` — blink sensitivity
- `HEAD_POSE_YAW_LIMIT` — head turn alert angle
- `SPOOF_CONFIDENCE_THRESHOLD` — real/spoof decision boundary
- `GAZE_OFF_SCREEN_SECONDS` — gaze alert window

---

## 🏗️ Tech Stack

| Layer     | Technology                    |
|-----------|-------------------------------|
| Backend   | Python 3.11, FastAPI, Uvicorn |
| CV/AI     | OpenCV, MediaPipe, TensorFlow |
| Database  | SQLite (SQLAlchemy async)     |
| Frontend  | React 18, Vite, Chart.js      |
| Streaming | WebSocket (native browser)    |
| Deploy    | Docker, NGINX                 |
