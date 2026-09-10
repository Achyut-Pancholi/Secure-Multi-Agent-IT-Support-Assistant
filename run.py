import sys
import os
import subprocess
import time
import signal

# Ensure current directory is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

processes = []

def clean_exit(signum=None, frame=None):
    print("\n[Shutting down all services...]")
    for p in processes:
        try:
            p.terminate()
            p.kill()
        except Exception:
            pass
    sys.exit(0)

# Register signals for clean Ctrl+C shutdown
signal.signal(signal.SIGINT, clean_exit)
signal.signal(signal.SIGTERM, clean_exit)

def main():
    print("=" * 60)
    print("🚀 STARTING SECURE MULTI-AGENT IT SUPPORT ASSISTANT (ALL-IN-ONE)")
    print("=" * 60)

    # 1. Start Mock IT Services (Port 8001)
    print("1️⃣ Starting Mock IT Services API on http://127.0.0.1:8001 ...")
    p_mock = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mock_services.main:app", "--port", "8001"],
        cwd=root_dir
    )
    processes.append(p_mock)
    time.sleep(1.5)

    # 2. Start Main FastAPI Backend (Port 8000)
    print("2️⃣ Starting Main Multi-Agent Backend on http://127.0.0.1:8000 ...")
    p_api = subprocess.Popen(
        [sys.executable, "app/main.py"],
        cwd=root_dir
    )
    processes.append(p_api)
    time.sleep(2.0)

    # 3. Start Streamlit UI (Port 8501)
    print("3️⃣ Starting Streamlit Chat UI on http://localhost:8501 ...")
    print("=" * 60)
    print("👉 Browser UI: http://localhost:8501")
    print("👉 Langfuse Cloud: https://cloud.langfuse.com")
    print("Press Ctrl+C anytime to stop all 3 services.")
    print("=" * 60)

    p_ui = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "ui/app.py"],
        cwd=root_dir
    )
    processes.append(p_ui)

    # Keep master script running until user interrupts
    try:
        p_ui.wait()
    except KeyboardInterrupt:
        clean_exit()

if __name__ == "__main__":
    main()

