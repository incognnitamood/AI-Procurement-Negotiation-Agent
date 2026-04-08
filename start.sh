#!/bin/bash

echo "Starting Procurement Negotiation Environment..."
echo "================================================"

# FastAPI listens on port 7860 (HF Spaces default exposed port)
# This ensures validation scripts can reach /reset at the public URL
echo "Starting FastAPI on port 7860 (OpenEnv API)..."
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --log-level info