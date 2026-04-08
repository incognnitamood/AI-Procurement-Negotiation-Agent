import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Body
from environment import NegotiationEnvironment
from models import NegotiationAction
from typing import Optional, Dict, Any

app = FastAPI()

SESSIONS = {}

@app.post("/reset")
async def reset(request: Dict[str, Any] = Body(...)):
    try:
        # Support both "task" and "task_name" keys for compatibility
        task = request.get("task") or request.get("task_name", "saas_renewal")
        session_id = request.get("session_id") or f"session_{hash(str(request))}"
        
        env = NegotiationEnvironment()
        obs = env.reset(task)
        SESSIONS[session_id] = env
        
        return {
            "observation": obs.model_dump(),
            "info": {"task": task, "session_id": session_id}
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
async def step(request: Dict[str, Any] = Body(...)):
    try:
        session_id = request.get("session_id")
        action_data = request.get("action")
        if not session_id or not action_data:
            raise HTTPException(status_code=400, detail="Missing session_id or action")
        
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        
        env = SESSIONS[session_id]
        action = NegotiationAction(**action_data)
        obs, reward, done, info = env.step(action)
        
        return {
            "observation": obs.model_dump(),
            "reward": float(reward),
            "done": bool(done),
            "info": info
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state")
async def get_state(session_id: str):
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        
        env = SESSIONS[session_id]
        state = env.state()
        return {"state": state.model_dump()}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}