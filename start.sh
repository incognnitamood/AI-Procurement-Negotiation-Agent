#!/bin/bash

echo "Procurement Negotiation OpenEnv - Starting"
echo "=========================================="
echo "API Server on port 7860"
echo ""

# Run FastAPI with uvicorn
python -m uvicorn main:app --host 0.0.0.0 --port 7860