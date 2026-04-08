#!/usr/bin/env python3
"""
Launch both FastAPI server and Gradio UI for the negotiation environment.
Works on Windows, Mac, and Linux.
"""

import subprocess
import time
import os
import sys

def main():
    print("=" * 60)
    print("Starting Procurement Negotiation Environment...")
    print("=" * 60)
    
    # Check if HF_TOKEN is set
    if not os.getenv("HF_TOKEN"):
        print("WARNING: HF_TOKEN not set. LLM-based inference will fail.")
        print("Set it with: set HF_TOKEN=your_token_here (Windows)")
    
    print("\nStarting FastAPI server on port 8000...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("Waiting for server to start...")
    time.sleep(3)
    
    print("Starting Gradio UI on port 7860...")
    ui_process = subprocess.Popen(
        [sys.executable, "gradio_ui.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("\n" + "=" * 60)
    print("✅ Services running:")
    print("   - FastAPI Server: http://localhost:8000")
    print("   - Gradio UI:      http://localhost:7860")
    print("=" * 60)
    print("Press Ctrl+C to stop all services.\n")
    
    try:
        server_process.wait()
        ui_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down services...")
        server_process.terminate()
        ui_process.terminate()
        time.sleep(1)
        server_process.kill()
        ui_process.kill()
        print("Services stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
