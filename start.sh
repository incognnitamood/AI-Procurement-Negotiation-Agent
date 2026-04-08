#!/bin/bash

echo "Starting Procurement Negotiation Environment..."
echo "================================================"

# Determine if running on HF Spaces
if [ -n "${SPACE_ID:-}" ]; then
    echo "Running on HF Spaces (SPACE_ID=$SPACE_ID)"
    echo "FastAPI will listen on port 7860 (exposed to public)"
    echo ""
    echo "Starting FastAPI server on port 7860..."
    python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
else
    echo "Running locally"
    echo ""
    echo "Starting FastAPI server on port 8000..."
    python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 &
    FASTAPI_PID=$!
    echo "FastAPI started (PID: $FASTAPI_PID)"
    
    # Quick health check (max 15 seconds)
    echo "Waiting for FastAPI to be ready..."
    for i in {1..15}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✓ FastAPI ready on port 8000"
            break
        fi
        echo "  Attempt $i/15..."
        sleep 1
    done
    
    echo "Starting Gradio UI on port 7860 (for local development)..."
    export GRADIO_SERVER_PORT=7860
    python gradio_ui.py &
    GRADIO_PID=$!
    echo "Gradio started (PID: $GRADIO_PID)"
    
    echo ""
    echo "Services running:"
    echo "  - FastAPI API: http://localhost:8000 (/reset, /step, /state, /health)"
    echo "  - Gradio UI:   http://localhost:7860"
    echo ""
    
    # Keep services running
    wait
fi