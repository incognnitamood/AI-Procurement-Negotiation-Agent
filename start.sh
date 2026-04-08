#!/bin/bash

echo "Starting Procurement Negotiation Environment..."
echo "==============================================="

# Check if HF_TOKEN is set
if [ -z "$HF_TOKEN" ]; then
    echo "WARNING: HF_TOKEN not set. LLM-based inference will fail."
fi

# Create log directory
mkdir -p /tmp/logs

echo "Starting FastAPI server on port 8000..."
# Start server and keep logs
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/logs/fastapi.log &
SERVER_PID=$!

echo "Waiting for FastAPI server to be ready (PID: $SERVER_PID)..."
# Wait for health check
MAX_RETRIES=60
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ FastAPI server is ready"
        break
    fi
    
    # Check if process is still running
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "✗ FastAPI crashed. Recent logs:"
        tail -20 /tmp/logs/fastapi.log
        exit 1
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "✗ FastAPI timeout. Logs:"
    cat /tmp/logs/fastapi.log
    exit 1
fi

sleep 2

echo "Starting Gradio UI on port 7860..."
python gradio_ui.py 2>&1 | tee /tmp/logs/gradio.log &
GRADIO_PID=$!

sleep 2

# Verify both are running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "✗ FastAPI died after startup"
    exit 1
fi

if ! kill -0 $GRADIO_PID 2>/dev/null; then
    echo "✗ Gradio died after startup"
    exit 1
fi

echo ""
echo "==============================================="
echo "Services running successfully!"
echo "  - FastAPI: http://localhost:8000 (PID: $SERVER_PID)"
echo "  - Gradio:  http://0.0.0.0:7860 (PID: $GRADIO_PID)"
echo "==============================================="
echo ""

# Keep script running and monitor processes
while true; do
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "FastAPI died (PID $SERVER_PID). Restarting..."
        python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/logs/fastapi.log &
        SERVER_PID=$!
        sleep 2
    fi
    
    if ! kill -0 $GRADIO_PID 2>/dev/null; then
        echo "Gradio died (PID $GRADIO_PID). Exiting..."
        exit 1
    fi
    
    sleep 5
done