"""
FastAPI Procurement Negotiation OpenEnv
Streamlined API server for OpenEnv validation
"""

import traceback
from typing import Dict, Any, Optional
import uuid

from fastapi import FastAPI, HTTPException, Request
from environment import NegotiationEnvironment
from models import NegotiationAction

print("[INFO] Starting OpenEnv API Server", flush=True)

# Session storage
SESSIONS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Procurement Negotiation OpenEnv")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "api": "procurement-negotiation-openenv"}

@app.post("/reset")
async def reset(request: Request):
    """Reset negotiation environment."""
    try:
        try:
            body = await request.json()
        except:
            body = {}
        
        task = body.get("task") or body.get("task_name", "saas_renewal")
        
        # Check if session already exists
        if "session_id" in body and body["session_id"] in SESSIONS:
            session_id = body["session_id"]
            obs = SESSIONS[session_id]["obs"]
            return {
                "observation": obs.model_dump(),
                "info": {"task": task, "session_id": session_id}
            }
        
        # Create new session
        session_id = str(uuid.uuid4())
        env = NegotiationEnvironment()
        obs = env.reset(task)
        SESSIONS[session_id] = {"env": env, "obs": obs, "task": task}
        
        return {
            "observation": obs.model_dump(),
            "info": {"task": task, "session_id": session_id}
        }
    except Exception as e:
        print(f"[ERROR] /reset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
async def step(request: Request):
    """Execute negotiation step."""
    try:
        try:
            body = await request.json()
        except:
            body = {}
        
        session_id = body.get("session_id")
        action_data = body.get("action")
        
        if not session_id or not action_data:
            raise ValueError("Missing session_id or action")
        
        if session_id not in SESSIONS:
            raise ValueError(f"Session not found: {session_id}")
        
        env = SESSIONS[session_id]["env"]
        action = NegotiationAction(**action_data)
        obs, reward, done, info = env.step(action)
        
        SESSIONS[session_id]["obs"] = obs
        
        return {
            "observation": obs.model_dump(),
            "reward": float(reward),
            "done": bool(done),
            "info": info
        }
    except Exception as e:
        print(f"[ERROR] /step: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state")
async def get_state(session_id: str):
    """Get negotiation state."""
    try:
        if session_id not in SESSIONS:
            raise ValueError(f"Session not found: {session_id}")
        
        env = SESSIONS[session_id]["env"]
        state = env.state()
        return {"state": state.model_dump()}
    except Exception as e:
        print(f"[ERROR] /state: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("[INFO] OpenEnv API Server starting on 0.0.0.0:7860")
    print("[INFO] Endpoints: /reset (POST), /step (POST), /state (GET), /health (GET)")
    uvicorn.run(app, host="0.0.0.0", port=7860)
