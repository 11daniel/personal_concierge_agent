#!/bin/bash
# Startup script for Personal Concierge Agent (FastAPI Backend + Streamlit Frontend)

# Ensure script halts on errors
set -e

# Export ABI compatibility environment variable for Python 3.14 PyO3 compiler issues
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

echo "🚀 Starting Personal Concierge Agent..."

# Set up and activate virtual environment to manage dependencies locally
if [ ! -d "venv" ]; then
    echo "🌐 No virtual environment found. Creating one..."
    # Attempt to use python3.12 (highly stable) if available, otherwise fallback to system python3
    if command -v python3.12 &>/dev/null; then
        echo "🐍 Using Python 3.12..."
        python3.12 -m venv venv
    else
        echo "🐍 Using default python3..."
        python3 -m venv venv
    fi
fi

# Upgrade pip inside virtual environment
./venv/bin/pip install --upgrade pip

# Install dependencies inside the virtual environment
echo "📦 Installing required dependencies..."
./venv/bin/pip install -r requirements.txt

# Check if port 8000 is occupied
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Warning: Port 8000 is already in use. Uvicorn backend might fail to start if it is another process."
fi

# Check if port 8501 is occupied
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Warning: Port 8501 is already in use. Streamlit will select a different port."
fi

# Start FastAPI backend server using the virtual environment uvicorn
echo "🟢 Launching uvicorn backend server on port 8000..."
PYTHONPATH=backend ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Let uvicorn boot up
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Trap exit signals to terminate the backend uvicorn automatically
cleanup() {
    echo "🛑 Shutting down backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start Streamlit application using the virtual environment streamlit
echo "🟢 Launching Streamlit dashboard frontend on http://localhost:8501..."
./venv/bin/streamlit run frontend/app.py --server.port 8501

# Keep script alive to hold the trap active
wait
