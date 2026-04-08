#!/bin/bash
set -e

echo "Starting Procurement Negotiation Environment..."
echo "==============================================="

# Check if HF_TOKEN is set
if [ -z "$HF_TOKEN" ]; then
    echo "WARNING: HF_TOKEN not set. LLM-based inference will fail."
    echo "Set it with: export HF_TOKEN=your_token_here"
fi

echo "Starting FastAPI server on port 8000..."
uvicorn server.app:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

echo "Waiting for server to start..."
sleep 3

echo "Starting Gradio UI on port 7860..."
python gradio_ui.py &
GRADIO_PID=$!

echo ""
echo "==============================================="
echo "Services running:"
echo "  - FastAPI Server: http://localhost:8000"
echo "  - Gradio UI:      http://localhost:7860"
echo "==============================================="
echo "Press Ctrl+C to stop all services."
echo ""

wait $SERVER_PID $GRADIO_PID