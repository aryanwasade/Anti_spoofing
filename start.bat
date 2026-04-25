@echo off
echo ============================================================
echo   Antispoofing Interview System — Quick Start (Windows)
echo ============================================================
echo.

REM ── Check Python virtual environment ──────────────────────────
if not exist ".venv" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
) else (
    echo [1/4] Virtual environment found.
)

echo [2/4] Installing Python dependencies...
call .venv\Scripts\activate.bat && pip install -r requirements.txt --quiet

echo [3/4] Installing frontend dependencies...
cd frontend && npm install --silent && cd ..

echo [4/4] Starting servers...
echo.
echo  Backend  → http://localhost:8000
echo  Frontend → http://localhost:5173
echo  API Docs → http://localhost:8000/docs
echo.
echo Press Ctrl+C in each window to stop.
echo.

REM Start backend in new window
start "AntiSpoof Backend" cmd /k ".venv\Scripts\activate.bat && uvicorn backend.main:app --reload --port 8000"

REM Wait 3 seconds then start frontend
timeout /t 3 /nobreak > nul
start "AntiSpoof Frontend" cmd /k "cd frontend && npm run dev"

echo Both servers are starting...
echo Open http://localhost:5173 in your browser.
pause
