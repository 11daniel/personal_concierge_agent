@echo off
echo 🚀 Starting Personal Concierge Agent on Windows...

:: Set ABI compatibility environment variable for Python 3.14 PyO3 compiler issues
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

:: Check if virtual environment exists
if not exist venv (
    echo 🌐 No virtual environment found. Creating one...
    :: Attempt to use python3.12 if installed, otherwise fallback to system python
    py -3.12 -m venv venv 2>nul
    if errorlevel 1 (
        echo 🐍 Falling back to default python...
        python -m venv venv
    )
)

:: Upgrade pip inside venv
call venv\Scripts\python.exe -m pip install --upgrade pip

:: Install dependencies
echo 📦 Installing required dependencies...
call venv\Scripts\pip.exe install -r requirements.txt

:: Start uvicorn backend server in a separate background window
echo 🟢 Launching uvicorn backend server on port 8000...
start "Personal Concierge Backend" cmd /k "set PYTHONPATH=backend&& venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000"

:: Wait for uvicorn to bind to port
timeout /t 3 /nobreak >nul

:: Start Streamlit dashboard in the active window
echo 🟢 Launching Streamlit dashboard frontend on http://localhost:8501...
call venv\Scripts\streamlit.exe run frontend/app.py --server.port 8501

pause
