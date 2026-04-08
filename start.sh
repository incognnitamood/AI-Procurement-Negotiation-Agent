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
# Start server with output captured for debugging
uvicorn server.app:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &
SERVER_PID=$!

echo "Waiting for FastAPI server to respond..."
# Wait for server to be ready with health check
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ FastAPI server is ready"
        break
    fi
    
    # Check if process is still running
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "✗ FastAPI server process died. Check logs:"
        cat /tmp/fastapi.log
        exit 1
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 10)) -eq 0 ]; then
        echo "  Still waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    fi
    sleep 0.5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "✗ FastAPI server did not respond within timeout. Logs:"
    cat /tmp/fastapi.log
    exit 1
fi

echo "Starting Gradio UI on port 7860..."
python gradio_ui.py > /tmp/gradio.log 2>&1 &
GRADIO_PID=$!

sleep 2

# Check if Gradio started
if ! kill -0 $GRADIO_PID 2>/dev/null; then
    echo "✗ Gradio process died. Check logs:"
    cat /tmp/gradio.log
    exit 1
fi

echo ""
echo "==============================================="
echo "Services running successfully:"
echo "  - FastAPI Server: http://localhost:8000/health"
echo "  - Gradio UI:      http://0.0.0.0:7860"
echo "==============================================="
echo "Logs:"
echo "  - FastAPI: /tmp/fastapi.log"
echo "  - Gradio:  /tmp/gradio.log"
echo "==============================================="
echo ""

# Trap errors and show logs
trap 'echo "Shutting down..."; kill $SERVER_PID $GRADIO_PID 2>/dev/null || true' EXIT

wait $SERVER_PID $GRADIO_PID