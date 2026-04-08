#!/bin/bash

echo "Starting Procurement Negotiation Environment..."
echo "================================================"

# Start FastAPI server first (required for OpenEnv compliance)
echo "Starting FastAPI server on port 8000..."
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!
echo "FastAPI started (PID: $FASTAPI_PID)"

# Quick health check (max 15 seconds)
echo "Waiting for FastAPI to be ready..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ FastAPI ready"
        break
    fi
    echo "  Attempt $i/15..."
    sleep 1
done

# Start Gradio UI (optional, for user interaction)
echo "Starting Gradio UI on port 7860..."
python gradio_ui.py &
GRADIO_PID=$!
echo "Gradio started (PID: $GRADIO_PID)"

echo ""
echo "Services running:"
echo "  - FastAPI API: http://0.0.0.0:8000 (ports: /reset, /step, /state, /health)"
echo "  - Gradio UI:   http://0.0.0.0:7860"
echo ""

# Keep on running
wait